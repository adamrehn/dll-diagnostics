from .CommonErrors import CommonErrors
from .HelperProcess import HelperProcess
from .ModuleHeader import ModuleHeader
import os, platform, win32api

class WindowsApi(object):
	'''
	Convenience functionality for interacting with the Windows API
	'''
	
	@staticmethod
	def formatError(error, inserts=[]):
		'''
		Formats a Windows API error code with the specified values for placeholder tokens
		'''
		message = win32api.FormatMessage(error).strip()
		for index, value in enumerate(inserts):
			message = message.replace('%{}'.format(index+1), value)
		return message
	
	@staticmethod
	def loadModule(module, cwd, architecture=None, force_external=False):
		'''
		Attempts to load the specified PE module using `LoadLibrary()` and returns the result.
		
		`architecture` specifies the architecture of the module (will be auto-detected if `None`.)
		
		Setting `force_external` to True will use a helper executable even if the architecture
		of the module matches the architecture of the Python interpreter. (Useful for testing.)
		'''
		
		# If no architecture was specified, auto-detect the module architecture
		moduleArch = architecture if architecture is not None else ModuleHeader(module).getArchitecture()
		
		# Determine if the Python interpreter architecture matches the module architecture
		pythonArch = 'x64' if platform.architecture()[0] == '64bit' else 'x86'
		if moduleArch == pythonArch and force_external == False:
			
			# Call `LoadLibrary()` directly in Python for maximum speed
			return WindowsApi._loadModuleInternal(module, cwd)
			
		else:
			
			# Use our helper executable to perform the load with the correct architecture
			return WindowsApi._loadModuleExternal(moduleArch, module, cwd)
	
	@staticmethod
	def _loadModuleInternal(module, cwd):
		'''
		Loads a module by calling `LoadLibrary()` directly inside the Python interpreter
		'''
		origCwd = os.getcwd()
		os.chdir(cwd)
		try:
			handle = win32api.LoadLibrary(module)
			win32api.FreeLibrary(handle)
			return 0
		except Exception as e:
			return e.winerror
		finally:
			os.chdir(origCwd)
	
	@staticmethod
	def _loadModuleExternal(architecture, module, cwd):
		'''
		Loads a module using our helper executable for the specified architecture
		'''
		
		# Verify that the helper executable can actually be run without any arguments to ensure we
		# don't inadvertently report execution failures as though they were `LoadLibrary()` failures
		helper = HelperProcess(architecture, 'loadlibrary')
		if helper.canRun() == False:
			CommonErrors.cannotRunHelper(architecture)
		
		# Run the helper and propagate the exit code
		return helper.run([module], cwd=cwd).returncode
