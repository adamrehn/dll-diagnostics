from pathlib import Path

class FileIO(object):
	'''
	Provides functionality for performing file I/O
	'''
	
	@staticmethod
	def readFile(filename, encoding='utf-8'):
		'''
		Reads data from a file
		'''
		return Path(filename).read_bytes().decode(encoding)
	
	@staticmethod
	def writeFile(filename, data, encoding='utf-8'):
		'''
		Writes data to a file
		'''
		Path(filename).write_bytes(data.encode(encoding))
