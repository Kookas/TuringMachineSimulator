from time import sleep
from re import match
from argparse import ArgumentParser
from sys import stdout, stdin
from keypress import keypress
from tape import Tape

class RuleNotFound(Exception):
	def __init__(self, state, char):
		self.value = (state, char)
	def __str__(self):
		return repr("No rule found from state {0[0]} with char {0[1]}.".format(self.value))

class IncorrectSymbolCount(Exception):
	def __init__(self, count):
		self.count = count
	def __str__(self):
		return repr("Incorrect number of rule symbols (must be a multiple of 5, is {count}).".format(count=self.count))

class TapeBlank(Exception):
	def __str__(self):
		return repr("The input tape is blank.")

class TuringMachine:
	'''
	A full-tape Turing machine.

	To set the rules for the machine,
	pass them as an array of 5-tuples
	to the `rules` attribute. The format
	of the 5-tuples is as follows:

		current_state, current_symbol, next_state, next_symbol, head_direction

	To execute the program, first set the
	`tape` attribute. Then use `run()` for
	automatic execution, or `step()` to
	progress to the next step.

	The following attributes are
	available for configuration:

		display_rules   - display the current rule alongside the current state.
		display_path    - display the path of states at the end.
		step_time       - the time between automatic steps when using `run()`.

		silent       	- skip showing intermediate steps.
		verbose			- show extra information at each step.

		live            - show the state as a live display on a single line.
	'''

	# Configuration

	STATE_INIT = '1'
	STATE_HALT = '0'

	WILDCARD = '*'

	display_rules = False
	display_path = True
	step_time = 0.25

	silent = False
	verbose = False

	live = False

	# State

	state = STATE_INIT
	head = STATE_HALT
	rule = None

	_tape = Tape()

	@property
	def tape(self):
		return self._tape

	@tape.setter
	def tape(self, value):
		"""
		Feeds input tape to the Turing machine.
		"""

		self._tape = Tape(value)
		self.reset()

	# Tracking

	stepc = 0
	head_moves = 0
	path = []

	# Stores max length of string in live mode

	live_stdout_maxlen = 0

	def __init__(self, rules):
		self.rules = rules

	def reset(self):
		"""
		Resets the state of the Turing machine to the
		start.
		"""

		# Reset state variables

		self.state = self.STATE_INIT
		self.head = 0
		self.rule = None

		# Reset tracking variables

		self.stepc = 0
		self.head_moves = 0
		self.path = [self.STATE_INIT]

		self.print_state()

	def find_rule(self, state, scan):
		"""
		Given a state and scan, attempts to find a matching
		rule according to this Turing machine.
		"""

		for r in self.rules:
			if str(r[0]) == state and (str(r[1]) == scan or str(r[1]) == self.WILDCARD):
				return r

		raise RuleNotFound(state, scan)

	def step(self):
		"""
		Progresses the Turing machine state.
		"""

		if not self._tape:
			raise TapeBlank

		self.stepc += 1

		# Add empty spaces to array when
		# pointer moves beyond right edge

		scan = self._tape[self.head]
		self.rule = self.find_rule(self.state, scan)

		# Replace character as per rule

		replace = str(self.rule[3]) if str(self.rule[3]) != self.WILDCARD else scan
		self._tape[self.head] = replace

		# Update Turing state

		head_direction = int(self.rule[4])

		self.state = str(self.rule[2])
		self.head += head_direction

		if head_direction:
			self.head_moves += 1

		self.path.append(self.state)

		# Print state

		self.step_print(self.state == self.STATE_HALT, self.state == self.STATE_HALT)

	def run(self):
		"""
		Automatically progresses the Turing machine state
		every `step_time` seconds until program halt.
		"""

		while self.state != self.STATE_HALT:
			self.step()

			if not self.silent:
				sleep(self.step_time)
			
		return self._tape

	# Print functions

	def step_print(self, end_mode = False, silent_override = False):
		"""
		Prints info about the current step.
		"""

		if end_mode:
			self.print_state(False, silent_override)

			print('')

			# Live mode needs an extra blank line

			if self.live:
				print('')

			self.print_tracking()
		else:
			self.print_state(True, silent_override)

	def print_tracking(self, nl = True):
		"""
		Prints tracking info so far.
		"""

		self.print_stepc(nl)
		self.print_head_moves(nl)

		if self.display_path:
			self.print_path(nl)

	def print_state(self, show_head = False, silent_override = False):
		"""
		Prints info about the current state.
		"""

		# Silence override provided for 'essential' info

		if self.silent and not silent_override:
			return False

		# Convert tape to string and insert head symbol

		tape_string = str(self._tape).replace('_', ' ')
		out = tape_string + ' ' if not show_head else tape_string[:self.head] + '|' + tape_string[self.head:]

		# Uses carriage-return character for overwriting
		# the previous state when in live display mode

		end = '\r' if self.live else '\n'

		# Prepare format string

		formatstr = "{stepc} ({state}): >{out}<"

		if self.display_rules:
			formatstr += " R: {rule}"

		formatted = formatstr.format(rule = self.rule, stepc = self.stepc, state = self.state, out=out)

		# Padding to overwrite previous characters when the string shortens

		self.live_stdout_maxlen = len(formatted) if len(formatted) > self.live_stdout_maxlen else self.live_stdout_maxlen		
		padding = (self.live_stdout_maxlen - len(formatted)) * ' '

		# Write

		stdout.write(formatted)

		if self.verbose:
			stdout.write(' ')
			self.print_tracking(False)
		
		stdout.write(padding)

		stdout.write(end)
		stdout.flush()

	def print_stepc(self, nl = True):
		"""
		Prints the step count so far.
		"""

		stdout.write("Steps: {stepc}{end}".format(stepc=self.stepc, end='\n' if nl else ' '))

	def print_head_moves(self, nl = True):
		"""
		Prints the number of head moves so far.
		"""

		stdout.write("Head moves: {moves}{end}".format(moves=self.head_moves, end='\n' if nl else ' '))

	def print_path(self, nl = True):
		"""
		Prints the state path so far.
		"""

		stdout.write("State path: {path}{end}".format(path=self.path, end='\n' if nl else ' '))

def _read_rules(file):
	"""
	Given an open file `file`, reads rules
	into 5-tuples separated by some
	non-alphanumeric, non-underscore
	delineator.
	"""

	rules = []
	cfg = {}

	tup_buf = []
	sym_buf = ''
	cfg_buf = ''

	symc = 0

	state = 'std'

	eof = False

	def state_reader():
		nonlocal state, cfg_buf, sym_buf, symc, tup_buf, cfg, rules, eof
		
		if state == 'std':
			if match("[-\w\*]", char) and not eof:
				# Read into symbol buffer.

				sym_buf += char

			elif char == ':' and not eof:
				# Store name in buffer variable and reset
				# symbol variable.

				cfg_buf = sym_buf.lower()
				sym_buf = ''

				# Enter cfg state.

				state = 'cfg'

			elif sym_buf:				
				# Previous characters were a rule symbol.
				# Store rule symbol in tuple buffer.

				tup_buf.append(sym_buf)
				sym_buf = ''
				symc += 1

				# Once 5 symbols found, add tuple to rules
				# and clear tuple buffer.

				if len(tup_buf) == 5:
					rules.append(tuple(tup_buf))
					tup_buf = []

			elif char == '#':
				state = 'cmt'

		if state == 'cfg':
			if match("[^\s\:]", char) and not eof:
				# Read into symbol buffer.

				sym_buf += char

			elif sym_buf:
				# Previous characters were a config value.

				# Add config key-value pair to cfg
				# and clear buffers.

				cfg[cfg_buf] = sym_buf
				cfg_buf = ''
				sym_buf = ''

				# Move to next state.

				state = 'std'

		elif state == 'cmt':
			if char == '\n':
				state = 'std'

	for line in file:
		for char in line:
			state_reader()

	eof = True
	
	state_reader()

	if symc % 5:
		raise IncorrectSymbolCount(symc)

	return (rules, cfg)

def _parse_args():
	"""
	For parsing args when run as __main__.
	"""

	parser = ArgumentParser(description='Simulates the action of a Turing Machine.')

	parser.add_argument('path', help="Path of a file containing rule quintuples.")
	parser.add_argument('input', help="Input string.")

	parser.add_argument('--rules', action='store_true', help="Displays the rules alongside the state.")

	parser.add_argument('--step_time', type=float, default=0.250, help="Sets the delay between steps (in seconds). Default is 0.25.")
	parser.add_argument('--fast', action='store_const', dest='step_time', const=0, help="Removes the delay between steps (equivalent to --step_time=0).")

	parser.add_argument('--silent', action='store_true', help="Hides intermediate states.")
	parser.add_argument('--verbose', action='store_true', help="Includes additional information beside each step.")

	parser.add_argument('--live', action='store_true', help="Displays a single, continuously changing state representation")

	parser.add_argument('-s', action='store_true', dest='stepping_mode', help="Enables stepping mode, in which you press a key to progress to each further step.")
	parser.add_argument('-l', action='store_true', dest='loop_mode', help="Enables loop mode. The program will continually prompt for further input after each run.")
	return parser.parse_args()

def _stepping_mode(turing):
	while 1:
		x = keypress()

		if ord(x) == 3:	# Interrupt on Ctrl+C
			raise KeyboardInterrupt
		elif x == 'i':	# Show current info so far
			turing.verbose = not turing.verbose

		turing.step()
		
		if turing.state == turing.STATE_HALT:
			break

if __name__ == "__main__":
	# Parse

	argv = vars(_parse_args())

	# Load

	with open(argv['path'], 'r') as f:
		rules = _read_rules(f)
		turing = TuringMachine(rules[0])
		
		if 'init' in rules[1]:
			turing.STATE_INIT = rules[1]['init']

		if 'halt' in rules[1]:
			turing.STATE_HALT = rules[1]['halt']

	# Configure

	turing.display_rules = argv['rules']
	turing.step_time = argv['step_time']

	turing.silent = argv['silent']
	turing.verbose = argv['verbose']

	turing.live = argv['live']

	# Input

	loop = True
	tape = argv['input']

	while loop:
		if not tape:
			tape = input("\nInput additional tape.\n")
			print('')

		turing.tape = tape

		# Execute

		if argv['stepping_mode'] and not argv['silent']:
			_stepping_mode(turing)
		else:
			output = turing.run()

		tape = ''
		loop = argv['loop_mode']