import os, subprocess
from os.path import basename, exists, join

class WindowsDebugger(object):
	'''
	Provides functionality for locating and running components of the Debugging Tools for Windows 10 (WinDbg)
	'''
	
	def __init__(self):
		'''
		Performs debugger detection for our supported architectures and stores the results
		'''
		
		# Locate the root directory for the Debugging Tools for Windows 10
		programFiles = os.environ.get('ProgramFiles(x86)', os.environ['ProgramFiles'])
		debuggerRoot = join(programFiles, 'Windows Kits', '10', 'Debuggers')
		
		# Locate the subdirectories for our supported architectures
		architectureDirs = {
			'x86': join(debuggerRoot, 'x86'),
			'x64': join(debuggerRoot, 'x64')
		}
		
		# Determine if the debuggers are installed
		self._debuggers = {
			architecture: directory if exists(directory) else None
			for architecture, directory in architectureDirs.items()
		}
	
	def haveDebugger(self, architecture):
		'''
		Reports whether the debugger for the specified architecture is installed
		'''
		return self._debuggers.get(architecture, None) is not None
	
	def debugWithLoaderSnaps(self, architecture, executable, args=[], cwd=None):
		'''
		Enables loader snaps for the specified executable and runs it through the debugger
		'''
		
		# Attempt to enable loader snaps for the specified executable
		try:
			subprocess.run(
				[join(self._debuggers[architecture], 'gflags.exe'), '-i', basename(executable), '+sls'],
				stdout = subprocess.DEVNULL,
				stderr = subprocess.DEVNULL,
				check = True
			)
		except:
			raise RuntimeError('could not enable loader snaps. Please ensure you have sufficient privileges to perform this operation.')
		
		# Run the executable through the debugger and capture the output
		try:
			return subprocess.run(
				[join(self._debuggers[architecture], 'cdb.exe'), executable] + args,
				stdout = subprocess.PIPE,
				stderr = subprocess.PIPE,
				input = 'g\nq\n',
				universal_newlines = True,
				cwd = cwd
			)
		except:
			raise RuntimeError('could not run the debugger. Please ensure you have sufficient privileges to perform this operation.')
