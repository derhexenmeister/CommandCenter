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
# See http://www.mimirgames.com/articles/games/joystick-input-and-using-deadbands/
# for the motivation and theory
#
# Usage:
#
# import board
# from adafruit_hid.mouse import Mouse
# import usb_hid
# from piper_joystick import PiperJoystickAxis
#
# x_axis = PiperJoystickAxis(board.A4, outputScale=20)
# y_axis = PiperJoystickAxis(board.A3, outputScale=20)
#
# mouse = Mouse(usb_hid.devices)
# while True:
#     dx = x_axis.readJoystickAxis()
#     dy = y_axis.readJoystickAxis()
#     mouse.move(x=dx, y=dy)
#
from analogio import AnalogIn
from math import copysign

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
