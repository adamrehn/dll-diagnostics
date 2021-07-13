from .FileIO import FileIO
import json, os, subprocess, tempfile, threading, time
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
	
	def run(self, executable, args, timeout=None, capture=True, merge=False, **kwargs):
		'''
		Runs the specified executable with our instrumentation DLL injected.
		This is a wrapper for `subprocess.run()`.
		
		`timeout` specifies a timeout in seconds after which the process should be stopped.
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
			
			# Start a child process to run the executable with our DLL injected
			command = [self.withDLL, '/d:{}'.format(self.detourDLL), executable] + args
			process = subprocess.Popen(
				command,
				stdout=stdout,
				stderr=stderr,
				universal_newlines=True,
				env=env,
				**kwargs
			)
			
			# If a timeout was specified then spin off a separate thread to terminate the child process after the timeout elapses
			if timeout is not None:
				threading.Thread(
					target=DetourLibrary._terminateAfterTimeout,
					args=(process, timeout),
					daemon=True
				).start()
			
			# Wait for the child process to complete and retrieve its stdout, stderr and exit code
			stdout, stderr = process.communicate(None)
			exitCode = process.poll()
			result = subprocess.CompletedProcess(command, exitCode, stdout, stderr)
			
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
	
	@staticmethod
	def _terminateAfterTimeout(process, timeout):
		'''
		Forcibly terminates a process and its child processes after the specified timeout elapses.
		
		`process` is a `subprocess.Popen` object representing the target process.
		`timeout` specifies the timeout in seconds.
		'''
		
		# Wait for the timeout to elapse
		time.sleep(timeout)
		
		# If the child process is still running then use `taskkill` to terminate it
		if process.returncode is None:
			subprocess.run(
				['taskkill', '/F', '/T', '/PID', str(process.pid)],
				stdout=subprocess.DEVNULL,
				stderr=subprocess.DEVNULL,
				check=False
			)
