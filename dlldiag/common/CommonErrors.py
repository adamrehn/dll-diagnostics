class CommonErrors(object):
	'''
	Encapsulates common errors that may occur in multiple subcommands
	'''
	
	@staticmethod
	def cannotRunHelper(architecture):
		raise RuntimeError('cannot run the helper executable for architecture {}. Please ensure the Microsoft Visual C++ Redistributable for Visual Studio 2015-2019 is installed correctly.'.format(architecture))
	
	@staticmethod
	def debuggerNotInstalled(architecture):
		raise RuntimeError('no debugger found for architecture {}. Please ensure the Debugging Tools for Windows 10 (WinDbg) are installed correctly.'.format(architecture))
