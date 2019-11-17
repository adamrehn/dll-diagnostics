from .common import OutputFormatting
from .subcommands import subcommands
from .version import __version__
import colorama, os, sys

def main():
	
	# Print the version number and copyright notice
	print('DLL Diagnostic Tools version {}'.format(__version__))
	print('Copyright (c) 2019 Adam Rehn\n', flush=True)
	
	# Initialise colour output
	colorama.init()
	
	# Truncate argv[0] to just the command name without the full path
	sys.argv[0] = os.path.basename(sys.argv[0])
	
	# Determine if a subcommand has been specified
	if len(sys.argv) > 1:
		
		# Verify that the specified subcommand is valid
		subcommand = sys.argv[1].lower()
		if subcommand not in subcommands.keys():
			print('Error: unrecognised subcommand "{}".'.format(subcommand), file=sys.stderr)
			sys.exit(1)
		
		# Invoke the subcommand
		sys.argv = [sys.argv[0]] + sys.argv[2:]
		subcommands[subcommand]['function']()
		
	else:
		
		# Print usage syntax
		print('Usage: {} SUBCOMMAND [OPTIONS]\n'.format(sys.argv[0]))
		print('Available subcommands:')
		OutputFormatting.printRows([(subcommand, subcommands[subcommand]['description']) for subcommand in subcommands], spacing=4, indent=2)
		print('\nRun `{} SUBCOMMAND --help` for more information on a subcommand.'.format(sys.argv[0]))
