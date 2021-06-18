from ..common import DetourLibrary, ModuleHeader, OutputFormatting
import argparse, hashlib, json, os, sys
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
		for field in ['timestamp_start', 'module', 'thread', 'function', 'arguments']:
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
		for candidate in reversed(candidates):
			if GraphHelpers.entriesMatch(candidate, entry):
				candidates.remove(candidate)
				return candidate
		
		# No match found
		return None
	
	@staticmethod
	def constructGraph(logEntries):
		'''
		Constructs a directed graph from the supplied list of log entries
		'''
		
		# Create a new directed graph
		graph = nx.OrderedDiGraph()
		
		# Maintain a list of function calls for which we've not yet seen a return value
		pending = []
		
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
				
				# Create a vertex for the calling module if we don't already have one
				if entry['module'] not in graph:
					graph.add_node(entry['module'])
				
				# Create a vertex for the module resolved by the LoadLibrary() call if we don't already have one
				# (Note that this will create a vertex called "NULL" that all failed calls will have outbound edges pointing to)
				if entry['result'] not in graph:
					graph.add_node(entry['result'])
				
				# Create an edge between the calling module vertex and the resolved module vertex, annotated with the call details
				graph.add_edge(entry['module'], entry['result'], details=entry)
				
			else:
				raise RuntimeError('unsupported log entry type "{}"!'.format(entry['type']))
		
		return graph
	
	@staticmethod
	def printSummary(graph):
		'''
		Prints a summary of the supplied call hierarchy graph
		'''
		
		# Iterate over each module
		for vertex in graph:
			print('{}:'.format(colored(vertex, color='cyan')))
			
			# Iterate over the edges for the module's LoadLibrary() calls
			edges = graph[vertex].items()
			if len(edges) == 0:
				print('    This module did not load any libraries.')
			else:
				for edge, attributes in edges:
					
					# Determine whether the call succeeded
					details = attributes['details']
					if details['error']['code'] == 0 and details['result'] != 'NULL':
						result = colored(details['result'], color='green')
					else:
						result = colored(details['error']['message'], color='red')
					
					# Print the call details with pretty formatting
					print('    {} "{}" -> {}'.format(
						colored(details['function'], color='yellow'),
						details['arguments'][0],
						result
					))
			
			# Print a blank line after each module's call list
			print()


def graph():
	
	# Our supported command-line arguments
	parser = argparse.ArgumentParser(prog='{} trace'.format(sys.argv[0]), prefix_chars='-/')
	parser.add_argument('module', help='EXE file for which the LoadLibrary() call hierarchy should be inspected')
	
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
			print('Running executable {} with arguments {} and instrumenting all LoadLibrary() calls...\n'.format(args.module, run_args), flush=True)
			detour = DetourLibrary(architecture, 'loadlibrary')
			logEntries = detour.run(args.module, run_args).log
		except:
			raise RuntimeError('failed to run instrumented executable!')
		
		# Construct the call hierarchy graph from the instrumentation log entries
		graph = GraphHelpers.constructGraph(logEntries)
		
		# Print a pretty summary
		GraphHelpers.printSummary(graph)
		
		# TODO: dump to GraphViz dot format?
		
	except RuntimeError as e:
		print('Error: {}'.format(e))
		sys.exit(1)


DESCRIPTOR = {
	'function': graph,
	'description': 'Executes a module with instrumentation to log LoadLibrary() calls and reconstructs the call hierarchy'
}
