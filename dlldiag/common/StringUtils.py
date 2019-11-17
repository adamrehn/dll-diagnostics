class StringUtils(object):
	'''
	Provides utility functionality related to working with strings and lists of strings
	'''
	
	@staticmethod
	def sortCaseInsensitive(strings):
		'''
		Performs a case-insensitive sort of a list of strings
		'''
		return sorted(strings, key=str.casefold)
	
	@staticmethod
	def uniqueCaseInsensitive(strings, sort=False):
		'''
		Returns the unique set of strings from a list, performing case-insensitive comparisons
		whilst also preserving the original casing of the returned results
		'''
		unique = list({s.casefold(): s for s in strings}.values())
		return StringUtils.sortCaseInsensitive(unique) if sort == True else unique
