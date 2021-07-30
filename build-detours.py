import glob, json, shutil, subprocess, sys, tempfile, urllib.request
from os.path import abspath, basename, dirname, isdir, join


# Copies a file to a new location, logging the details
def copy(source, dest):
	print('[BUILD-DETOURS.PY] Copy {} => {}'.format(source, dest), file=sys.stderr, flush=True)
	if isdir(source):
		shutil.copytree(source, dest)
	else:
		shutil.copy2(source, dest)

# Executes a command, logging the details
def run(command, **kwargs):
	print('[BUILD-DETOURS.PY] {}'.format(command), file=sys.stderr, flush=True)
	return subprocess.run(command, **kwargs)


# Retrieve the absolute paths to the source and destination directories
rootDir = dirname(abspath(__file__))
sourceDir = join(rootDir, 'detours')
binDir = join(rootDir, 'dlldiag', 'bin')

# Export the Conan recipe for Detours
with tempfile.TemporaryDirectory() as recipeDir:
	urllib.request.urlretrieve('https://raw.githubusercontent.com/adamrehn/conan-recipes/main/detours/fe7216c/conanfile.py', join(recipeDir, 'conanfile.py'))
	run(['conan', 'export', '.', 'adamrehn/stable'], cwd=recipeDir)

# Build Detours and our instrumentation DLLs for each supported architecture
for architecture in ['x86', 'x64']:
	
	# Create a Conan profile for the architecture
	conanArch = 'x86_64' if architecture == 'x64' else architecture
	profile = 'dlldiag_detours_{}'.format(conanArch)
	run(['conan', 'profile', 'new', profile, '--detect', '--force'])
	run(['conan', 'profile', 'update', 'settings.arch={}'.format(conanArch), profile])
	run(['conan', 'profile', 'update', 'settings.arch_build={}'.format(conanArch), profile])
	
	# Create a temporary directory to hold the build
	with tempfile.TemporaryDirectory() as tempDir:
		
		# Build Detours if it hasn't already been built for this architecture
		run(['conan', 'install', join(sourceDir, 'conanfile.txt'), '--profile={}'.format(profile), '--build=outdated'], cwd=tempDir)
		
		# Retrieve the details of the binary package for Detours
		with open(join(tempDir, 'conanbuildinfo.json'), 'rb') as f:
			detours = json.load(f)['dependencies'][0]
		
		# Build our instrumentation DLLs
		cmakeArchitecture = 'Win32' if architecture == 'x86' else architecture
		run(['cmake', '-A', cmakeArchitecture, sourceDir], cwd=tempDir)
		run(['cmake', '--build', '.', '--config', 'Release'], cwd=tempDir)
		
		# Copy the built instrumentation DLLs and the Detours withdll tool to the destination directory for the architecture
		targetDir = join(binDir, architecture)
		for file in list(glob.glob(join(tempDir, 'bin', '*.dll'))) + [join(detours['bin_paths'][0], 'withdll.exe')]:
			copy(file, join(targetDir, basename(file)))
