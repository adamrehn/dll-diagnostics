import os, subprocess
from os.path import abspath, dirname, join

class HelperProcess(object):
	'''
	Provides access to our helper executables
	'''
	
	def __init__(self, architecture, helper):
		'''
		Creates a new helper executable wrapper.
		
		`architecture` specifies the executable architecture ("x86" or "x64").
		`helper` specifies the name of the helper tool.
		'''
		self.executable = HelperProcess._resolveHelper(architecture, helper)
	
	def canRun(self):
		'''
		Determines if the helper executable can be run successfully
		'''
		try:
			subprocess.run([self.executable], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
			return True
		except:
			return False
	
	def run(self, args, capture=True, merge=False, **kwargs):
		'''
		Runs the helper executable. This is a thin wrapper for `subprocess.run()`.
		
		`capture` specifies whether stdout and stderr should be captured.
		`merge` specifies whether stderr should be redirected to stdout.
		'''
		
		# Configure stdout and stderr as requested
		stdout = subprocess.PIPE if capture == True else None
		stderr = subprocess.STDOUT if merge == True else stdout
		
		# Run the helper executable as a child process
		return subprocess.run(
			[self.executable] + args,
			stdout=stdout,
			stderr=stderr,
			universal_newlines=True,
			**kwargs
		)
	
	@staticmethod
	def _resolveHelper(architecture, helper):
		'''
		Resolves the absolute path to a specific helper executable
		
		`architecture` specifies the executable architecture ("x86" or "x64").
		`helper` specifies the name of the helper tool.
		'''
		return join(
			dirname(dirname(abspath(__file__))),
			'bin',
			architecture,
			'dlldiag-helper-{}.exe'.format(helper)
		)
