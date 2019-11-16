from os.path import abspath, dirname, join
from setuptools import setup

# Read the README markdown data from README.md
with open(abspath(join(dirname(__file__), 'README.md')), 'rb') as readmeFile:
	__readme__ = readmeFile.read().decode('utf-8')

setup(
	name='dll-diagnostics',
	version='0.0.1',
	description='Tools for diagnosing DLL dependency loading issues',
	long_description=__readme__,
	long_description_content_type='text/markdown',
	classifiers=[
		'License :: OSI Approved :: MIT License',
		'Programming Language :: Python :: 3.6',
		'Programming Language :: Python :: 3.7',
		'Programming Language :: Python :: 3.8',
		'Topic :: Software Development :: Build Tools',
		'Environment :: Console'
	],
	keywords='dll windows containers',
	url='http://github.com/adamrehn/dll-diagnostics',
	author='Adam Rehn',
	author_email='adam@adamrehn.com',
	license='MIT',
	packages=['dlldiag', 'dlldiag.common', 'dlldiag.subcommands'],
	zip_safe=False,
	python_requires = '>=3.5',
	install_requires = [
		'colorama',
		'pefile',
		'pywin32',
		'setuptools>=38.6.0',
		'termcolor',
		'twine>=1.11.0',
		'wheel>=0.31.0'
	],
	package_data = {
		'dlldiag': ['bin/*/*.exe']
	},
	entry_points = {
		'console_scripts': ['dlldiag=dlldiag:main']
	}
)
