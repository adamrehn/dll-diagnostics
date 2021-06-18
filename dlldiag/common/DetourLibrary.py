from .FileIO import FileIO
import json, os, subprocess, tempfile
from os.path import abspath, dirname, join

class DetourLibrary(object):
	'''
	Provides access to our Detours-based instrumentation DLLs
	'''
	
	def __init__(self, architecture, dll):
		'''
		Creates a new instrumentation DLL wrapper.
		
		`architecture` specifies the executable architecture ("x86" or "x64").
		`dll` specifies the name of the instrumentation DLL.
		'''
		self.withDLL = DetourLibrary._resolveWithDLL(architecture)
		self.detourDLL = DetourLibrary._resolveDetourDLL(architecture, dll)
		self.envVar = 'DLLDIAG_DETOUR_{}_LOGFILE'.format(dll.upper())
	
	def run(self, executable, args, capture=True, merge=False, **kwargs):
		'''
		Runs the specified executable with our instrumentation DLL injected.
		This is a wrapper for `subprocess.run()`.
		
		`capture` specifies whether stdout and stderr should be captured.
		`merge` specifies whether stderr should be redirected to stdout.
		'''
		
		# Configure stdout and stderr as requested
		stdout = subprocess.PIPE if capture == True else None
		stderr = subprocess.STDOUT if merge == True else stdout
		
		# Create a temporary directory to hold the log output from the instrumentation DLL
		with tempfile.TemporaryDirectory() as tempDir:
			
			# Retrieve the existing environment variables that will be passed to the executable
			env = os.environ.copy()
			if 'env' in kwargs:
				env = kwargs['env']
				del kwargs['env']
			
			# Set the environment variable to direct log output to the temporary directory
			logFile = join(tempDir, 'log.txt')
			env[self.envVar] = logFile
			
			# Run the executable with our DLL injected
			result = subprocess.run(
				[self.withDLL, '/d:{}'.format(self.detourDLL), executable] + args,
				stdout=stdout,
				stderr=stderr,
				universal_newlines=True,
				env=env,
				**kwargs
			)
			
			# Parse the log file and include it in the returned result
			logEntries = [json.loads(line) for line in FileIO.readFile(logFile).splitlines()]
			setattr(result, 'log', logEntries)
			return result
	
	@staticmethod
	def _resolveWithDLL(architecture):
		'''
		Resolves the absolute path to `withdll.exe` for the specified architecture
		'''
		return join(
			dirname(dirname(abspath(__file__))),
			'bin',
			architecture,
			'withdll.exe'
		)
	
	@staticmethod
	def _resolveDetourDLL(architecture, dll):
		'''
		Resolves the absolute path to a specific instrumentation DLL
		
		`architecture` specifies the executable architecture ("x86" or "x64").
		`dll` specifies the name of the instrumentation DLL.
		'''
		return join(
			dirname(dirname(abspath(__file__))),
			'bin',
			architecture,
			'dlldiag-detour-{}.dll'.format(dll)
		)
