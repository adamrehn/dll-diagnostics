from ..common import DetourLibrary, FileIO, ModuleHeader, OutputFormatting
import argparse, hashlib, json, os, re, sys
from collections import OrderedDict
from termcolor import colored
import networkx as nx


class GraphHelpers(object):
	'''
	Helper functionality for reconstructing `LoadLibrary()` call hierarchies
	'''
	
	@staticmethod
	def entryHash(entry):
		'''
		Computes a hash of the fields common to both "enter" and "return" log entries
		'''
		
		# Extract the common fields and copy them into a new dictionary
		subset = {}
		for field in ['random', 'timestamp_start', 'module', 'thread', 'function', 'arguments']:
			subset[field] = entry[field]
		
		# Dump the dictionary to a JSON string and hash it
		return hashlib.sha256(json.dumps(subset, sort_keys=True).encode('utf-8')).hexdigest()
	
	@staticmethod
	def entriesMatch(lhs, rhs):
		'''
		Determines whether the supplied log entries are for the same function call
		'''
		return GraphHelpers.entryHash(lhs) == GraphHelpers.entryHash(rhs)
	
	@staticmethod
	def findMatch(candidates, entry):
		'''
		Attempts to find the last entry in the supplied list that matches the hash of the specified entry
		'''
		for index in range(len(candidates) - 1, -1, -1):
			candidate = candidates[index]
			if GraphHelpers.entriesMatch(candidate, entry):
				return candidates.pop(index)
		
		# No match found
		return None
	
	@staticmethod
	def formatFunctionName(entry):
		'''
		Formats a function name for pretty-printing
		'''
		return colored(entry['function'], color='yellow')
	
	@staticmethod
	def formatReturnValue(entry, successCondition=None):
		'''
		Formats a function call's return value for pretty-printing
		'''
		
		# Evaluate the success condition (if supplied) and retrieve the appropriate error field for the function
		success = successCondition(entry) if successCondition is not None else False
		error = entry['status'] if entry['function'] == 'LdrLoadDll' else entry['error']
		
		# Pretty-print the result upon success or the error upon failure
		if success == True or error['code'] == 0:
			return colored(entry['result'], color='green')
		else:
			return colored(error['message'].strip(), color='red')
	
	@staticmethod
	def formatFlags(flags):
		'''
		Formats a set of flags for pretty-printing
		'''
		return ' | '.join([colored(f, color='yellow') for f in flags])
	
	@staticmethod
	def formatAnnotations(annotations):
		'''
		Formats a set of annotations for pretty-printing
		'''
		return ' '.join([colored('[{}]'.format(a), color='magenta', attrs=['bold']) for a in annotations])
	
	@staticmethod
	def constructGraph(logEntries):
		'''
		Constructs a directed graph from the supplied list of log entries
		'''
		
		# Create a new directed graph with support for parallel edges
		graph = nx.OrderedMultiDiGraph()
		
		# Maintain a list of function calls for which we've not yet seen a return value
		pending = []
		
		# Gather all LdrLoadDll() calls and process them last
		loadDllEntries = list([e for e in logEntries if e['function'] == 'LdrLoadDll'])
		logEntries = list([e for e in logEntries if e['function'] != 'LdrLoadDll']) + loadDllEntries
		
		# Process each log entry in turn
		for entry in logEntries:
			
			# Determine if the log entry is for the start of a function call or its return value
			if entry['type'] == 'enter':
				
				# Add the entry to our stack of pending function calls
				pending.append(entry)
				
			elif entry['type'] == 'return':
				
				# Identify which pending function call this entry represents the return value for
				match = GraphHelpers.findMatch(pending, entry)
				if match is None:
					OutputFormatting.printWarning('encountered a return value before the function call!')
					continue
				
				# If this is a LdrLoadDll() call then examine the stack trace to determine the appropriate module to treat as the caller
				# (Note that we filter out the resolved module in addition to KERNELBASE.DLL and NTDLL.DLL, to help prevent self-loops that provide little valuable information)
				if entry['function'] == 'LdrLoadDll':
					candidates = [m for m in entry['stack'] if m != entry['result'] and m.upper() not in ['C:\\WINDOWS\\SYSTEM32\\KERNELBASE.DLL', 'C:\\WINDOWS\\SYSTEM32\\NTDLL.DLL']]
					if len(candidates) > 0:
						entry['module'] = candidates[0]
				
				# Create a vertex for the calling module if we don't already have one
				if entry['module'] not in graph:
					graph.add_node(entry['module'], non_loadlibrary_calls=[])
				
				# Determine if this is a LoadLibrary function call
				if entry['function'].startswith('LoadLibrary') or entry['function'] == 'LdrLoadDll':
					
					# Create a vertex for the module resolved by the LoadLibrary() call if we don't already have one
					# (Note that this will create a vertex called "NULL" that all failed calls will have outbound edges pointing to)
					if entry['result'] not in graph:
						graph.add_node(entry['result'], non_loadlibrary_calls=[])
					
					# Create an edge between the calling module vertex and the resolved module vertex, annotated with the call details
					graph.add_edge(entry['module'], entry['result'], details=entry)
					
				else:
					
					# For all other function calls, just add an entry to the list in the metadata for the vertex
					nx.get_node_attributes(graph, 'non_loadlibrary_calls')[entry['module']].append(entry)
				
			else:
				raise RuntimeError('unsupported log entry type "{}"!'.format(entry['type']))
		
		# Print a warning if there were any function calls for which we did not encounter a return value
		if len(pending) > 0:
			for entry in pending:
				OutputFormatting.printWarning('return value not found for function call: {}'.format(entry))
		
		return graph
	
	@staticmethod
	def printSummary(graph, extendedDetails):
		'''
		Prints a summary of the supplied call hierarchy graph
		'''
		
		# Iterate over each module
		for vertex in graph:
			
			# Ignore the "NULL" vertex that is used to represent failed LoadLibrary() calls
			if vertex == 'NULL':
				continue
			
			# Print the module name
			print('{}:'.format(colored(vertex, color='cyan', attrs=['bold'])))
			
			# Gather the list of pretty-printed function calls so we can filter out duplicates
			printed = []
			
			# If we are displaying extended details then print the details of the module's calls that are not LoadLibrary() calls
			if extendedDetails == True:
				
				# Keep track of the cookie values used by AddDllDirectory() and RemoveDllDirectory()
				cookies = {}
				
				# Iterate over the non-LoadLibrary calls
				calls = nx.get_node_attributes(graph, 'non_loadlibrary_calls')[vertex]
				for call in calls:
					
					# Determine which function we are dealing with, since we pretty print them with different formats
					if call['function'] == 'SetDefaultDllDirectories':
						printed.append('    {} [{}] -> {}'.format(
							GraphHelpers.formatFunctionName(call),
							GraphHelpers.formatFlags(call['arguments'][0]),
							GraphHelpers.formatReturnValue(call)
						))
					
					elif call['function'] in ['SetDllDirectoryA', 'SetDllDirectoryW']:
						printed.append('    {} "{}" -> {}'.format(
							GraphHelpers.formatFunctionName(call),
							call['arguments'][0],
							GraphHelpers.formatReturnValue(call)
						))
						
					elif call['function'] == 'AddDllDirectory':
						
						# Add the returned cookie to our list
						cookies[call['result']] = call['arguments'][0]
						
						printed.append('    {} "{}" -> {}'.format(
							GraphHelpers.formatFunctionName(call),
							call['arguments'][0],
							GraphHelpers.formatReturnValue(call)
						))
					
					elif call['function'] == 'RemoveDllDirectory':
						
						# Retrieve the passed cookie from our list
						cookie = cookies.get(call['arguments'][0], '<UNKNOWN>')
						
						printed.append('    {} {} ("{}") -> {}'.format(
							GraphHelpers.formatFunctionName(call),
							call['arguments'][0],
							cookie,
							GraphHelpers.formatReturnValue(call)
						))
			
			# Iterate over the edges for the module's LoadLibrary() and LdrLoadDll() calls
			neighbours = graph[vertex]
			if len(neighbours) == 0:
				printed.append('    This module did not load any libraries.')
			else:
				for _, edges in neighbours.items():
					for _, edge in edges.items():
						
						# Determine if we are annotating the call with any special information
						details = edge['details']
						annotations = []
						if extendedDetails == True:
							if details['function'] == 'LdrLoadDll' and details['module'].upper() in ['C:\WINDOWS\SYSTEM32\DXGI.DLL', 'C:\WINDOWS\SYSTEM32\D3D12CORE.DLL'] and 'DriverStore' in details['result']:
								annotations.append('DirectX UMD')
						
						# Determine if we are printing the search flags for the call
						flags = ''
						if extendedDetails == True and (details['function'].startswith('LoadLibraryEx') or details['function'] == 'LdrLoadDll'):
							flags = ' [{}]'.format(GraphHelpers.formatFlags(
								details['arguments'][1] if details['function'] == 'LdrLoadDll' else details['arguments'][2]
							))
						
						# Print the call details with pretty formatting
						printed.append('    {}{} "{}"{} -> {}'.format(
							(GraphHelpers.formatAnnotations(annotations) + ' ') if len(annotations) > 0 else '',
							GraphHelpers.formatFunctionName(details),
							details['arguments'][0],
							flags,
							GraphHelpers.formatReturnValue(details, successCondition = lambda e: e['result'] != 'NULL')
						))
			
			# Print all unique output lines, preserving their ordering
			print('\n'.join(list(OrderedDict.fromkeys(printed))))
			
			# Print a blank line after each module's call list
			print()
	
	@staticmethod
	def writeToFile(graph, outfile):
		'''
		Writes the supplied graph to file in GraphViz DOT format
		'''
		
		# Use pydot to convert the graph to DOT format
		dot = nx.drawing.nx_pydot.to_pydot(graph).to_string()
		
		# Clean up extraneous vertices
		# (These are presumably caused by using Windows file paths as vertex names)
		dot = re.sub('^C;$', '', dot, flags = re.MULTILINE)
		while '\n\n' in dot:
			dot = dot.replace('\n\n', '\n')
		
		# Convert backslashes to forward slashes to avoid confusing GraphViz
		dot = dot.replace('\\\\', '/').replace('\\', '/')
		
		# Write the DOT to the specified output file
		FileIO.writeFile(outfile, dot)


def graph():
	
	# Our supported command-line arguments
	parser = argparse.ArgumentParser(prog='{} trace'.format(sys.argv[0]), prefix_chars='-/')
	parser.add_argument('module', help='EXE file for which the LoadLibrary() call hierarchy should be inspected')
	parser.add_argument('-outfile', default=None, help='Generate a GraphViz DOT file representing the call graph')
	parser.add_argument('-timeout', default=None, type=int, help='Forcibly terminate the inspected process after the specified number of seconds')
	parser.add_argument('--output', '/OUTPUT', action='store_true', help='Print the stdout and stderr output generated by running the EXE file')
	parser.add_argument('--extended', '/EXTENDED', action='store_true', help='Display extended information about DLL search parameters')
	
	# If no command-line arguments were supplied, display the help message and exit
	if len(sys.argv) < 2:
		parser.print_help()
		sys.exit(0)
	
	# Parse the supplied command-line arguments
	args, run_args = parser.parse_known_args()
	
	try:
		
		# Ensure the module path is an absolute path
		args.module = os.path.abspath(args.module)
		
		# Determine the architecture of the module
		print('Parsing module header and detecting architecture... ', end='')
		header = ModuleHeader(args.module)
		architecture = header.getArchitecture()
		print('done.\n')
		
		# Display the module details
		print('Parsed module details:')
		OutputFormatting.printModuleDetails(header)
		print()
		
		# Verify that the module is an executable
		if header.getType() != 'Executable':
			raise RuntimeError('the module file "{}" is not an executable!'.format(args.module))
		
		# Attempt to run the executable with our instrumentation DLL injected to log LoadLibrary() calls
		logEntries = []
		try:
			print('Running executable {} with arguments {}{} and instrumenting all LoadLibrary() calls...\n'.format(
				args.module,
				run_args,
				', {} second timeout'.format(args.timeout) if args.timeout is not None else ''
			), flush=True)
			detour = DetourLibrary(architecture, 'loadlibrary')
			result = detour.run(args.module, run_args, timeout=args.timeout)
			logEntries = result.log
		except:
			raise RuntimeError('failed to run instrumented executable!')
		
		# Construct the call hierarchy graph from the instrumentation log entries
		graph = GraphHelpers.constructGraph(logEntries)
		
		# Print a pretty summary
		GraphHelpers.printSummary(graph, args.extended)
		
		# Dump the graph to a GraphViz DOT file if an output filename was specified
		if args.outfile is not None:
			print('Writing GraphViz DOT representation to "{}"...'.format(args.outfile), flush=True)
			GraphHelpers.writeToFile(graph, args.outfile)
		
		# Print the stdout and stderr from the executable if requested
		if args.output == True:
			print(colored('\nApplication stdout:', color='cyan'))
			print(result.stdout)
			print(colored('\nApplication stderr:', color='cyan'))
			print(result.stderr)
		
	except RuntimeError as e:
		print('Error: {}'.format(e))
		sys.exit(1)


DESCRIPTOR = {
	'function': graph,
	'description': 'Executes a module with instrumentation to log LoadLibrary() calls and reconstructs the call hierarchy'
}
