import colorama, subprocess, sys, tempfile
from termcolor import colored


# The Windows releases we build images for
RELEASES = ['1809', '1903', '1909']

# The alias tags we create for convenience purposes
ALIASES = {'ltsc2019': '1809'}

# Prints and runs a command
def run(command, **kwargs):
	print(colored(command, color='yellow'))
	result = subprocess.run(command, check=True, **kwargs)
	print('', flush=True)
	return result


# Initialise colour output
colorama.init()

# Build the default image for each supported Windows release
for release in RELEASES:
	
	# Create a temporary directory to hold the Dockerfile
	with tempfile.TemporaryDirectory() as tempDir:
		
		# Generate the Dockerfile and build the image
		run(['dlldiag', 'docker', 'Dockerfile', 'mcr.microsoft.com/windows/servercore:{}'.format(release)], cwd=tempDir)
		run(['docker', 'build', '-t', 'adamrehn/dll-diagnostics:{}'.format(release), tempDir])

# Create our alias tags
for alias, target in ALIASES.items():
	run(['docker', 'tag', 'adamrehn/dll-diagnostics:{}'.format(target), 'adamrehn/dll-diagnostics:{}'.format(alias)])

# Push the images to Docker Hub if requested
if len(sys.argv) > 1 and sys.argv[1] == '--push':
	for tag in RELEASES + list(ALIASES.keys()):
		run(['docker', 'push', 'adamrehn/dll-diagnostics:{}'.format(tag)])
