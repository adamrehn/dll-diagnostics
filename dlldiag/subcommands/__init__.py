# Import the descriptors for each of our subcommands
from .deps import DESCRIPTOR as deps
from .docker import DESCRIPTOR as docker
from .trace import DESCRIPTOR as trace

# Expose the list of descriptors as a dictionary keyed by subcommand name
subcommands = {
	'deps': deps,
	'docker': docker,
	'trace': trace
}
