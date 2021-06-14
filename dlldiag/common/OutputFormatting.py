from .WindowsApi import WindowsApi
from termcolor import colored

class OutputFormatting(object):
	'''
	Provides functionality related to formatting output
	'''
	
	@staticmethod
	def formatColouredResult(result, inserts, success='Succeeded'):
		'''
		Formats a Windows API return value, colouring the output green for success and red for failure
		'''
		message = success if result == 0 else 'Error {}: {}'.format(result, WindowsApi.formatError(result, inserts))
		return colored(message, color = 'green' if result == 0 else 'red')
	
	@staticmethod
	def printModuleDetails(module, spacing=4):
		'''
		Prints key details about the PE module wrapped in the supplied ModuleHeader object
		'''
		OutputFormatting.printRows([
			('Module:', module.getFilename()),
			('Type:', module.getType()),
			('Architecture:', module.getArchitecture())
		], spacing=spacing)
	
	@staticmethod
	def printWarning(message):
		'''
		Prints a warning message in yellow text
		'''
		print(colored('Warning: {}'.format(message), color='yellow'), flush=True)
	
	@staticmethod
	def printRow(lhs, rhs, width, indent=0):
		'''
		Prints a single row of output in two columns.
		
		`lhs` specifies the contents of the left-hand column.
		`rhs` specifies the contents of the right-hand column.
		`width` specifies the minimum width of the left-hand column.
		`indent` specifies the number of characters to indent the line by.
		'''
		formatString = '{}{:' + str(width) + '}{}'
		print(formatString.format(' ' * indent, lhs, rhs))
	
	@staticmethod
	def printRows(rows, spacing=1, indent=0):
		'''
		Prints a series of rows of output in two columns.
		
		`rows` specifies a list of tuples containing the values for each row.
		`spacing` indicates the minimum number of spaces between the columns.
		`indent` specifies the number of characters to indent each line by.
		'''
		
		# If we received zero rows then don't print anything
		if len(rows) == 0:
			return
		
		# Calculate the width of the left-hand column based on the longest value
		width = max([len(row[0]) for row in rows]) + spacing
		
		# Print the rows
		for row in rows:
			OutputFormatting.printRow(row[0], row[1], width, indent)
