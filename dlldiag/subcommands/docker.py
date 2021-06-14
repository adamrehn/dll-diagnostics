from ..version import __version__
from ..common import FileIO
import argparse, os, sys


# Our template Dockerfile code
DOCKERFILE_TEMPLATE = '''# escape=`
FROM {}
SHELL ["cmd", "/S", "/C"]

# We need administrative privileges for installing software and for running `dlldiag trace`
USER ContainerAdministrator

# Install the Chocolatey package manage
RUN powershell -NoProfile -ExecutionPolicy Bypass -Command "[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))"

# Install Python 3.x, the Microsoft Visual C++ Redistributable for Visual Studio 2015-2019, and the Debugging Tools for Windows 10 (WinDbg)
RUN choco install -y python vcredist140 windows-sdk-10-version-2004-windbg

# Label the image with the dll-diagnostics version number that it contains
LABEL DLLDIAG_VERSION={}

# Install dlldiag
RUN pip install dll-diagnostics=={}
'''


def docker():
	
	# Our supported command-line arguments
	parser = argparse.ArgumentParser(prog='{} docker'.format(sys.argv[0]))
	parser.add_argument('dockerfile', help='Output filename for the generated Dockerfile')
	parser.add_argument(
		'base',
		nargs='?',
		default='mcr.microsoft.com/windows/servercore:1809',
		help='Base image tag to use in the Dockerfile\'s FROM clause (default is Windows Server Core 2019)'
	)
	
	# If no command-line arguments were supplied, display the help message and exit
	if len(sys.argv) < 2:
		parser.print_help()
		sys.exit(0)
	
	# Parse the supplied command-line arguments
	args = parser.parse_args()
	
	# Fill in the template Dockerfile code and write it to the specified output file
	outfile = os.path.abspath(args.dockerfile)
	FileIO.writeFile(outfile, DOCKERFILE_TEMPLATE.format(args.base, __version__, __version__))
	
	# Print the absolute path to the output file
	print('Wrote generated Dockerfile to {}'.format(outfile), flush=True)


DESCRIPTOR = {
	'function': docker,
	'description': 'Generates a Dockerfile suitable for using dlldiag inside a Windows container'
}
