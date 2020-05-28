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
################################################################################

from adafruit_debouncer import Debouncer
from adafruit_hid.mouse import Mouse
from analogio import AnalogIn
import board
from digitalio import DigitalInOut, Direction, Pull
from math import copysign
import usb_hid

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
class PiperCommandCenter:
	def __init__(self, joy_x_pin=board.A4, joy_y_pin=board.A3, joy_gnd_pin=board.A5, dpad_l_pin=board.D3, dpad_r_pin=board.D4, dpad_u_pin=board.D1, dpad_d_pin=board.D0, outputScale=20.0, deadbandCutoff=0.1, weight=0.2):
		self.x_axis = PiperJoystickAxis(joy_x_pin, outputScale=outputScale, deadbandCutoff=deadbandCutoff, weight=weight)
		self.y_axis = PiperJoystickAxis(joy_y_pin, outputScale=outputScale, deadbandCutoff=deadbandCutoff, weight=weight)
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
		self.mouse = Mouse(usb_hid.devices)

	def process(self):
		# Call the debouncing library frequently
		self.left.update()
		self.right.update()
		dx = self.x_axis.readJoystickAxis()
		dy = self.y_axis.readJoystickAxis()

		self.mouse.move(x=dx, y=dy)

		if self.left.fell:
			self.mouse.press(Mouse.LEFT_BUTTON)
		elif self.left.rose:
			self.mouse.release(Mouse.LEFT_BUTTON)

		if self.right.fell:
			self.mouse.press(Mouse.RIGHT_BUTTON)
		elif self.right.rose:
			self.mouse.release(Mouse.RIGHT_BUTTON)