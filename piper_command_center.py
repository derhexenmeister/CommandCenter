################################################################################
# The MIT License (MIT)
#
# Copyright (c) 2020 Keith Evans
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
################################################################################
#
# Press the joystick for one second to toggle between controller modes.
#
# Inactive (RED LED):
#   The joystick must remain relatively centered for one second to exit this mode. This
#   is to prevent undesirable HID controls in the event that the joystick is not
#   wired
#
# In Mouse Mode (GREEN LED):
#   The joystick controls cursor movement.
#   The left and right DPAD buttons mimic left and right mouse clicks.
#   The up and down DPAD buttons mimic the mouse scroll wheel.
#
# In Keyboard Mode (BLUE LED):
#   The joystick mimics the arrow keys on a keyboard
#   The buttons mimic Space Bar (Up), Z (Left), X (Down), and C (Right) keys on a keyboard.
#
# *** Basic Joystick Management Usage:
#
# import board
# from adafruit_hid.mouse import Mouse
# import usb_hid
# from piper_command_center import PiperJoystickAxis
#
# x_axis = PiperJoystickAxis(board.A4, outputScale=20)
# y_axis = PiperJoystickAxis(board.A3, outputScale=20)
#
# mouse = Mouse(usb_hid.devices)
# while True:
#	  dx = x_axis.readJoystickAxis()
#	  dy = y_axis.readJoystickAxis()
#	  mouse.move(x=dx, y=dy)
#
# *** Handle all built-in Piper Command Center functionality:
#
# from piper_command_center import PiperCommandCenter
# pcc = PiperCommandCenter()
# while True:
#	  pcc.process()
#
# Note that this also uses exec() to provide minimal REPL functionality. So you
# can paste code such as the following:
#
# led = DigitalInOut(board.D13)
# led.direction = Direction.OUTPUT
# led.value = True
#
# Note that it assumes that the code will be entered quickly, and uses
# input() to obtain a line of code. This is blocking, but isn't called until
# there is input available.
#
################################################################################

from adafruit_debouncer import Debouncer
import adafruit_dotstar
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode
from adafruit_hid.mouse import Mouse
from analogio import AnalogIn
import board
from digitalio import DigitalInOut, Direction, Pull
from math import copysign
import supervisor
import time
import usb_hid

__version__ = "0.5.5"
__repo__ = "https://github.com/derhexenmeister/CommandCenter.git"

################################################################################
# This function allows a user to manage joystick handling themselves.
# See http://www.mimirgames.com/articles/games/joystick-input-and-using-deadbands/
# for the motivation and theory
#
class PiperJoystickAxis:
	def __init__(self, pin, outputScale=20.0, deadbandCutoff=0.1, weight=0.2):
		self.pin = AnalogIn(pin)
		self.outputScale = outputScale
		self.deadbandCutoff = deadbandCutoff
		self.weight = weight
		self.alpha = self._Cubic(self.deadbandCutoff)

	# Cubic function to map input to output in such a way as to give more precision
	# for lower values
	def _Cubic(self, x):
		return self.weight * x ** 3 + (1.0 - self.weight) * x

	# Eliminate the jump present in the deadband, but use the cubic function to give
	# more precision to lower values
	#
	def _cubicScaledDeadband(self, x):
		if abs(x) < self.deadbandCutoff:
			return 0
		else:
			return (self._Cubic(x) - (copysign(1,x)) * self.alpha) / (1.0-self.alpha)

	# The analog joystick output is an unsigned number 0 to 2^16, which we
	# will scale to -1 to +1 for compatibility with the cubic scaled
	# deadband article. This will then remap and return a value
	# still in the range -1 to +1. Finally we multiply by the requested scaler
	# an return an integer which can be used with the mouse HID.
	#
	def readJoystickAxis(self):
		return int(self._cubicScaledDeadband((self.pin.value / 2**15) - 1)*self.outputScale)

################################################################################
# Handle all Piper Command Center built-in functionality
#

# States
#
_UNWIRED  = 0
_WAITING  = 1
_JOYSTICK = 2
_JWAITING = 3
_KEYBOARD = 4
_KWAITING = 5

class PiperCommandCenter:
	def __init__(self, joy_x_pin=board.A4, joy_y_pin=board.A3, joy_z_pin=board.D2, joy_gnd_pin=board.A5, dpad_l_pin=board.D3, dpad_r_pin=board.D4, dpad_u_pin=board.D1, dpad_d_pin=board.D0, outputScale=20.0, deadbandCutoff=0.1, weight=0.2):
		self.x_axis = PiperJoystickAxis(joy_x_pin, outputScale=outputScale, deadbandCutoff=deadbandCutoff, weight=weight)
		self.y_axis = PiperJoystickAxis(joy_y_pin, outputScale=outputScale, deadbandCutoff=deadbandCutoff, weight=weight)

		self.joy_z_pin = DigitalInOut(joy_z_pin)
		self.joy_z_pin.direction = Direction.INPUT
		self.joy_z_pin.pull = Pull.UP
		self.joy_z = Debouncer(self.joy_z_pin)

                # Drive pin low if requested for easier joystick wiring
		if joy_gnd_pin is not None:
			# Provide a ground for the joystick - this is to facilitate
			# easier wiring
			self.joystick_gnd = DigitalInOut(joy_gnd_pin)
			self.joystick_gnd.direction = Direction.OUTPUT
			self.joystick_gnd.value = 0

		# Setup DPAD
		#
		self.left_pin = DigitalInOut(dpad_l_pin)
		self.left_pin.direction = Direction.INPUT
		self.left_pin.pull = Pull.UP
		self.left = Debouncer(self.left_pin)

		self.right_pin = DigitalInOut(dpad_r_pin)
		self.right_pin.direction = Direction.INPUT
		self.right_pin.pull = Pull.UP
		self.right = Debouncer(self.right_pin)

		self.up_pin = DigitalInOut(dpad_u_pin)
		self.up_pin.direction = Direction.INPUT
		self.up_pin.pull = Pull.UP
		self.up = Debouncer(self.up_pin)

		self.down_pin = DigitalInOut(dpad_d_pin)
		self.down_pin.direction = Direction.INPUT
		self.down_pin.pull = Pull.UP
		self.down = Debouncer(self.down_pin)

                self.keyboard = Keyboard(usb_hid.devices)
                self.keyboard_layout = KeyboardLayoutUS(self.keyboard)  # Change for non-US
		self.mouse = Mouse(usb_hid.devices)

                # State
                #
                self.state = _UNWIRED
                self.timer = time.monotonic()
                self.last_mouse_wheel = time.monotonic()
                self.last_mouse = time.monotonic()
                self.dotstar_led = adafruit_dotstar.DotStar(board.APA102_SCK, board.APA102_MOSI, 1)
                self.dotstar_led.brightness = 0.6
                self.up_pressed = False
                self.down_pressed = False
                self.left_pressed = False
                self.right_pressed = False

	def process_repl_cmds(self):
		# Assume that the command will be pasted, because input()
		# will block until end of line
		#
		if supervisor.runtime.serial_bytes_available:
			cmd = input()
			exec(cmd)

	def process(self):
		self.process_repl_cmds()

		# Call the debouncing library frequently
		self.joy_z.update()
		self.left.update()
		self.right.update()
		self.up.update()
		self.down.update()
		dx = self.x_axis.readJoystickAxis()
		dy = self.y_axis.readJoystickAxis()

                # Command Center State Machine
                #
                if self.state == _UNWIRED:
                    self.dotstar_led[0] = ((time.monotonic_ns() >> 23) % 256, 0, 0)
                    if dx == 0 and dy == 0:
                        self.state = _WAITING
                        self.timer = time.monotonic()
                elif self.state == _WAITING:
                    self.dotstar_led[0] = ((time.monotonic_ns() >> 23) % 256, 0, 0)
                    if dx != 0 or dy != 0:
                        self.state = _UNWIRED
                    else:
                        if time.monotonic() - self.timer > 0.5:
                            self.state = _JOYSTICK
                elif self.state == _JOYSTICK:
                    self.dotstar_led[0] = (0, 255, 0)
                    if not self.joy_z.value:
                        self.timer = time.monotonic()
                        self.state = _JWAITING
                elif self.state == _JWAITING:
                    if self.joy_z.value:
                        self.state = _JOYSTICK
                    else:
                        if time.monotonic() - self.timer > 1.0:
                            self.state = _KEYBOARD
                            self.mouse.release(Mouse.LEFT_BUTTON)
                            self.mouse.release(Mouse.RIGHT_BUTTON)
                elif self.state == _KEYBOARD:
                    self.dotstar_led[0] = (0, 0, 255)
                    if not self.joy_z.value:
                        self.timer = time.monotonic()
                        self.state = _KWAITING
                elif self.state == _KWAITING:
                    if self.joy_z.value:
                        self.state = _KEYBOARD
                        self.up_pressed = False
                        self.down_pressed = False
                        self.left_pressed = False
                        self.right_pressed = False

                    else:
                        if time.monotonic() - self.timer > 1.0:
                            self.state = _JOYSTICK
                            self.keyboard.release(Keycode.UP_ARROW)
                            self.keyboard.release(Keycode.DOWN_ARROW)
                            self.keyboard.release(Keycode.LEFT_ARROW)
                            self.keyboard.release(Keycode.RIGHT_ARROW)
                            self.keyboard.release(Keycode.SPACE)
                            self.keyboard.release(Keycode.X)
                            self.keyboard.release(Keycode.Z)
                            self.keyboard.release(Keycode.C)

                # Command Center Joystick Handling
                #
                if self.state == _JOYSTICK or self.state == _JWAITING:
                    # TODO - figure out a way to pace the mouse movements for consistency
                    #
                    dwheel = 0
                    if not self.up.value:
                        dwheel=-1
                    elif not self.down.value:
                        dwheel=1

                    # Initial quick and dirty mouse movement pacing
                    #
                    if time.monotonic() - self.last_mouse > 0.005:
                        self.last_mouse = time.monotonic()
                        self.mouse.move(x=dx, y=dy)

                    # Initial quick and dirty mouse scroll wheel pacing
                    #
                    if time.monotonic() - self.last_mouse_wheel > 0.1:
                        self.last_mouse_wheel = time.monotonic()
                        self.mouse.move(wheel=dwheel)

                    if self.left.fell:
                            self.mouse.press(Mouse.LEFT_BUTTON)
                    elif self.left.rose:
                            self.mouse.release(Mouse.LEFT_BUTTON)

                    if self.right.fell:
                            self.mouse.press(Mouse.RIGHT_BUTTON)
                    elif self.right.rose:
                            self.mouse.release(Mouse.RIGHT_BUTTON)

                # Command Center Keyboard Handling
                #
                if self.state == _KEYBOARD or self.state == _KWAITING:
                    if self.up.fell:
                        self.keyboard.press(Keycode.SPACE)
                    elif self.up.rose:
                        self.keyboard.release(Keycode.SPACE)

                    if self.down.fell:
                        self.keyboard.press(Keycode.X)
                    elif self.down.rose:
                        self.keyboard.release(Keycode.X)

                    if self.left.fell:
                        self.keyboard.press(Keycode.Z)
                    elif self.left.rose:
                        self.keyboard.release(Keycode.Z)

                    if self.right.fell:
                        self.keyboard.press(Keycode.C)
                    elif self.right.rose:
                        self.keyboard.release(Keycode.C)

                    if dx == 0:
                        if self.left_pressed:
                            self.left_pressed = False
                            self.keyboard.release(Keycode.LEFT_ARROW)
                        if self.right_pressed:
                            self.right_pressed = False
                            self.keyboard.release(Keycode.RIGHT_ARROW)
                    elif dx > 0:
                        if self.left_pressed:
                            self.left_pressed = False
                            self.keyboard.release(Keycode.LEFT_ARROW)
                        if not self.right_pressed:
                            self.right_pressed = True
                            self.keyboard.press(Keycode.RIGHT_ARROW)
                    elif dx < 0:
                        if not self.left_pressed:
                            self.left_pressed = True
                            self.keyboard.press(Keycode.LEFT_ARROW)
                        if self.right_pressed:
                            self.right_pressed = False
                            self.keyboard.release(Keycode.RIGHT_ARROW)

                    if dy == 0:
                        if self.up_pressed:
                            self.up_pressed = False
                            self.keyboard.release(Keycode.UP_ARROW)
                        if self.down_pressed:
                            self.down_pressed = False
                            self.keyboard.release(Keycode.DOWN_ARROW)
                    elif dy < 0:
                        if not self.up_pressed:
                            self.up_pressed = True
                            self.keyboard.press(Keycode.UP_ARROW)
                        if self.down_pressed:
                            self.down_pressed = False
                            self.keyboard.release(Keycode.DOWN_ARROW)
                    elif dy > 0:
                        if self.up_pressed:
                            self.up_pressed = False
                            self.keyboard.release(Keycode.UP_ARROW)
                        if not self.down_pressed:
                            self.down_pressed = True
                            self.keyboard.press(Keycode.DOWN_ARROW)

