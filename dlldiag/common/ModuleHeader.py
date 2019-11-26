from .HelperProcess import HelperProcess
import os, pefile, platform, win32api

class ModuleHeader(object):
	'''
	Provides functionality for retrieving information about PE modules
	'''
	
	def __init__(self, module):
		'''
		Parses the header for the specified module
		'''
		self._filename = module
		self._pe = pefile.PE(module, fast_load=True)
		self._parsedImports = False
	
	def getArchitecture(self):
		'''
		Returns the architecture of the module ("x86" or "x64")
		'''
		machine = pefile.MACHINE_TYPE[self._pe.FILE_HEADER.Machine]
		return {
			'IMAGE_FILE_MACHINE_AMD64': 'x64',
			'IMAGE_FILE_MACHINE_I386': 'x86',
		}[machine]
	
	def getFilename(self):
		'''
		Returns the module's filename
		'''
		return self._filename
	
	def getType(self):
		'''
		Returns the module type ("Dynamic-Link Library", "Driver", or "Executable")
		'''
		if self._pe.is_dll():
			return 'Dynamic-Link Library'
		elif self._pe.is_driver():
			return 'Driver'
		elif self._pe.is_exe():
			return 'Executable'
		else:
			raise RuntimeError('unrecognised PE module type')
	
	def listAllImports(self):
		'''
		Returns an aggregated list of all dependencies that the module imports
		'''
		return self.listImports() + self.listDelayLoadedImports() + self.listBoundImports()
	
	def listImports(self):
		'''
		Returns a list of the standard imports for the module
		'''
		return self._getImportsForDirectory('DIRECTORY_ENTRY_IMPORT')
	
	def listDelayLoadedImports(self):
		'''
		Returns a list of the delay-loaded imports for the module
		'''
		return self._getImportsForDirectory('DIRECTORY_ENTRY_DELAY_IMPORT')
	
	def listBoundImports(self):
		'''
		Returns a list of the bound imports for the module
		'''
		return self._getImportsForDirectory('DIRECTORY_ENTRY_BOUND_IMPORT', attribute='name')
	
	def _getImportsForDirectory(self, directory, attribute='dll'):
		'''
		Retrieves the list of imports for a specific directory entry
		'''
		
		# If we haven't already parsed the imports, do so now
		if self._parsedImports == False:
			self._pe.parse_data_directories(import_dllnames_only=True)
			self._parsedImports = True
		
		# Retrieve the imports for the specified directory entry
		return [getattr(imported, attribute).decode('utf-8') for imported in getattr(self._pe, directory, [])]
