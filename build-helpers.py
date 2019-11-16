import glob, os, shutil, subprocess, sys, tempfile
from os.path import abspath, basename, dirname, join
from subprocess import run

# Retrieve the absolute paths to the source and destination directories
rootDir = dirname(abspath(__file__))
sourceDir = join(rootDir, 'helpers')
binDir = join(rootDir, 'dlldiag', 'bin')

# Build our helper executables for each supported architecture
for architecture in ['x86', 'x64']:
	
	# Create a temporary directory to hold the build
	with tempfile.TemporaryDirectory() as tempDir:
		
		# Perform the build
		cmakeArchitecture = 'Win32' if architecture == 'x86' else architecture
		run(['cmake', '-A', cmakeArchitecture, sourceDir], cwd=tempDir)
		run(['cmake', '--build', '.', '--config', 'Release'], cwd=tempDir)
		
		# Copy each of the built executables to the appropriate destination directory
		targetDir = join(binDir, architecture)
		for executable in glob.glob(join(tempDir, 'Release', '*.exe')):
			destExecutable = join(targetDir, basename(executable))
			print('\n[BUILD-HELPERS.PY] Copy {} => {}\n'.format(executable, destExecutable), file=sys.stderr, flush=True)
			shutil.copy2(executable, destExecutable)
