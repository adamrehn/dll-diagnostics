from ..common import CommonErrors, HelperProcess, ModuleHeader, OutputFormatting, StringUtils, WindowsDebugger
from termcolor import colored
from ctypes import *
import argparse, os, sys


class CallTrace(object):
	'''
	Represents an individual function call in a `LoadLibrary()` trace
	'''
	
	def __init__(self, prefix, function, dll, result):
		self.prefix = prefix
		self.function = function
		self.dll = dll
		self.result = result
	
	def __str__(self):
		return '{} - {} - {}{}'.format(
			self.prefix,
			self.function,
			self.dll,
			': {}'.format(self.result) if self.result is not None else ''
		)


class TraceHelpers(object):
	'''
	Helper functionality for tracing `LoadLibrary()` calls
	'''
	
	@staticmethod
	def getFunctionWhitelist():
		'''
		Returns the list of function names that we care about when tracing `LoadLibrary()` calls
		'''
		return [
			'LdrLoadDll',
			'LdrpLoadDllInternal',
			'LdrpMinimalMapModule',
			'LdrpResolveDllName'
		]
	
	@staticmethod
	def getSuccessMessage(function):
		'''
		Returns the appropriate message for indicating a successful outcome for the specified function
		'''
		return {
			'LdrLoadDll': 'Loaded successfully',
			'LdrpLoadDllInternal': 'Loaded successfully',
			'LdrpMinimalMapModule': 'Mapped successfully'
		}[function]
	
	@staticmethod
	def parseLine(prefix, function, details):
		'''
		Parses a single output line from a loader snaps trace.
		Output lines follow this format:
		
		"ab12:cd34 @ 123456789 - Function - [ENTER|RETURN]: [DLL|Status]: PAYLOAD"
		'''
		components = details.split(':', 2)
		return {
			'prefix': prefix.split(' @ ', 2)[0],
			'function': function,
			'operation': components[0],
			'dll': components[2].strip() if components[0] == 'ENTER' else None,
			'result': components[2].strip() if components[0] == 'RETURN' else None
		}
	
	@staticmethod
	def aggregateCalls(calls):
		'''
		Aggregates a set of CallTrace objects, returning the first successful call
		if at least one call was successful or else simply returning the first call
		'''
		succeeded = list([c for c in calls if c.result == 0])
		return succeeded[0] if len(succeeded) > 0 else calls[0]
	
	@staticmethod
	def getResolvedDll(call):
		'''
		Given a CallTrace object for a `LdrpResolveDllName` call, returns a coloured
		string containing either the resolved DLL path or a formatted error string if
		the call was unsuccessful
		'''
		return colored(call.dll, color='green') if call.result == 0 else OutputFormatting.formatColouredResult(call.result, [call.dll])
	
	@staticmethod
	def performTrace(debugger, helper, module, architecture, cwd, args=[]):
		'''
		Performs a `LoadLibrary()` trace with loader snaps enabled
		'''
		
		# Load NTDLL.DLL so we can use the RtlNtStatusToDosError() function to map NTSTATUS codes to Windows API error codes
		ntdll = cdll.LoadLibrary('ntdll')
		
		# Run our library loader helper through the debugger with loader snaps enabled
		result = debugger.debugWithLoaderSnaps(architecture, helper.executable, [module], cwd=cwd)
		
		# Locate the start and end markers in the debugger stdout so we avoid parts of the trace that relate
		# purely to loading the helper executable rather than loading the module we are interested in
		startMarker = '[LOADLIBRARY][START]'
		endMarker = '[LOADLIBRARY][END]'
		start = result.stdout.index(startMarker) + len(startMarker)
		end = result.stdout.index(endMarker)
		subset = result.stdout[start:end]
		
		# Split each line into prefix, function name, and details
		lines = [line.split(' - ', 2) for line in subset.replace('\r\n', '\n').split('\n')]
		
		# Isolate the lines related to the functions we are interested in
		lines = [line for line in lines if len(line) == 3 and line[1] in TraceHelpers.getFunctionWhitelist()]
		
		# Parse the details of each line
		parsedLines = [TraceHelpers.parseLine(line[0], line[1], line[2]) for line in lines]
		
		# Pair the ENTER and RETURN lines to determine the return values for each function call
		calls = []
		pending = []
		while len(parsedLines) > 0:
			
			# Determine if this is an ENTER line or a RETURN line
			parsed = parsedLines.pop(0)
			if parsed['operation'] == 'ENTER':
				
				# Create a CallTrace object for the function call
				trace = CallTrace(parsed['prefix'], parsed['function'], parsed['dll'], parsed['result'])
				calls.append(trace)
				pending.append(trace)
				
			else:
				
				# Attempt to match the RETURN line to its corresponding ENTER line
				matches = [c for c in reversed(pending) if parsed['prefix'] == c.prefix and parsed['function'] == c.function]
				if len(matches) > 0:
					
					# Match found, update the result value
					match = matches[0]
					match.result = ntdll.RtlNtStatusToDosError(int(parsed['result'], 16))
					pending.remove(match)
					
				elif len(parsedLines) > 1:
					
					# Match not found but there are other lines remaining, so push this one back in the queue
					OutputFormatting.printWarning('encountered a RETURN trace line before its corresponding ENTER line')
					parsedLines.insert(2, parsed)
					
				else:
					
					# Match not found and no other lines left, so we have no choice but to simply drop the line
					OutputFormatting.printWarning('dropped a RETURN trace line because no corresponding ENTER line could be found')
		
		# Report any function calls for which we did not find a return value
		unresolved = [c for c in calls if c.result is None]
		calls = [c for c in calls if c.result is not None]
		if len(unresolved) > 0:
			OutputFormatting.printWarning('return values could not be found for the following function calls:')
			print(colored('- ' + '\n- '.join([str(c) for c in unresolved]) + '\n', color='yellow'), flush=True)
		
		# Return the raw trace output and the list of calls for which a return value was found
		return (subset + result.stderr, calls)


def trace():
	
	# Our supported command-line arguments
	parser = argparse.ArgumentParser(prog='{} trace'.format(sys.argv[0]), prefix_chars='-/')
	parser.add_argument('module', help='DLL or EXE file for which LoadLibrary() call should be traced')
	parser.add_argument('--raw', '/RAW', action='store_true', help='Print raw trace output in addition to summary info')
	parser.add_argument('--no-delay-load', '/NODELAY', action='store_true', help='Don\'t perform traces for the module\'s delay-loaded dependencies')
	
	# If no command-line arguments were supplied, display the help message and exit
	if len(sys.argv) < 2:
		parser.print_help()
		sys.exit(0)
	
	# Parse the supplied command-line arguments
	args = parser.parse_args()
	
	try:
		
		# Ensure the module path is an absolute path
		args.module = os.path.abspath(args.module)
		
		# Determine the architecture of the module
		print('Parsing module header and detecting architecture... ', end='')
		header = ModuleHeader(args.module)
		architecture = header.getArchitecture()
		print('done.\n')
		
		# Retrieve the list of delay-loaded dependencies, unless requested otherwise
		dependencies = []
		if args.no_delay_load == False:
			print('Identifying the module\'s delay-loaded dependencies... ', end='')
			dependencies = StringUtils.sortCaseInsensitive(header.listDelayLoadedImports())
			print('done.\n')
		
		# Display the module details
		print('Parsed module details:')
		OutputFormatting.printModuleDetails(header)
		print()
		
		# Display the list of delay-loaded dependencies
		if args.no_delay_load == False:
			print('The module imports {} delay-loaded dependencies:'.format(len(dependencies)))
			print('\n'.join(dependencies))
			print()
		
		# Verify that the debugger for the module's architecture is installed
		debugger = WindowsDebugger()
		if debugger.haveDebugger(architecture) == False:
			CommonErrors.debuggerNotInstalled(architecture)
		
		# Determine if our library loader helper for the module's architecture can be run
		helper = HelperProcess(architecture, 'loadlibrary')
		if helper.canRun() == False:
			CommonErrors.cannotRunHelper(architecture)
		
		# Perform the LoadLibrary() trace for the module and each of its delay-loaded dependencies
		cwd = os.path.dirname(args.module)
		rawOutput = ''
		calls = []
		for module in [args.module] + dependencies:
			print('Performing LoadLibrary() trace for {}...'.format(module))
			result = TraceHelpers.performTrace(debugger, helper, module, architecture, cwd)
			rawOutput += result[0]
			calls = calls + result[1]
		print('Done.\n', flush=True)
		
		# Generate and print summaries each function except for `LdrpResolveDllName`, which requires special treatment
		for function in [c for c in TraceHelpers.getFunctionWhitelist() if c != 'LdrpResolveDllName']:
			
			# Retrieve the list of calls to the current function and the set of unique DLL names used as arguments
			instances = [c for c in calls if c.function == function]
			dlls = StringUtils.uniqueCaseInsensitive([c.dll for c in instances], sort=True)
			
			# For cases where there are multiple calls for a single DLL, treat the result as success if at least one call succeeded
			results = {
				dll: TraceHelpers.aggregateCalls([c for c in instances if c.dll.lower() == dll.lower()]).result
				for dll in dlls
			}
			
			# Print the summary
			print('Summary of {} calls:'.format(colored(function, color='yellow')))
			summary = [(dll, OutputFormatting.formatColouredResult(result, [dll], TraceHelpers.getSuccessMessage(function))) for dll, result in results.items()]
			OutputFormatting.printRows(summary, spacing=4)
			print()
		
		# Retrieve the list of calls to `LdrpResolveDllName` and the filenames of the DLLs that were being resolved
		instances = [c for c in calls if c.function == 'LdrpResolveDllName']
		dlls = StringUtils.uniqueCaseInsensitive([os.path.basename(c.dll) for c in instances], sort=True)
		
		# Determine which path (if any) each DLL was resolved to
		resolved = {
			dll: TraceHelpers.getResolvedDll(TraceHelpers.aggregateCalls([c for c in instances if os.path.basename(c.dll.lower()) == dll.lower()]))
			for dll in dlls
		}
		
		# Print the summary
		print('Summary of {} calls:'.format(colored('LdrpResolveDllName', color='yellow')))
		OutputFormatting.printRows(resolved.items(), spacing=4)
		print()
		
		# Print the raw trace output if the user requested it
		if args.raw == True:
			print('Raw trace output:')
			print(rawOutput, end='', flush=True)
		
	except RuntimeError as e:
		print('Error: {}'.format(e))
		sys.exit(1)


DESCRIPTOR = {
	'function': trace,
	'description': 'Traces a LoadLibrary() call for a module and reports detailed results'
}
