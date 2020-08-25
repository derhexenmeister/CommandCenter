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
#     dx = x_axis.readJoystickAxis()
#     dy = y_axis.readJoystickAxis()
#     mouse.move(x=dx, y=dy)
#
################################################################################

from adafruit_debouncer import Debouncer
from analogio import AnalogIn
import board
from digitalio import DigitalInOut, Direction, Pull
from math import copysign

__version__ = "0.7.2"
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
# Joystick button handled separately
#
class PiperJoystickZ:
    def __init__(self, joy_z_pin=board.D2):
        self.joy_z_pin = DigitalInOut(joy_z_pin)
        self.joy_z_pin.direction = Direction.INPUT
        self.joy_z_pin.pull = Pull.UP
        self.joy_z = Debouncer(self.joy_z_pin)

    def update(self):
        self.joy_z.update()

    def zPressed(self):
        return not self.joy_z.value

    def zPressedEvent(self):
        return self.joy_z.fell

    def zReleasedEvent(self):
        return self.joy_z.rose

################################################################################
# This class allows a user to manage DPAD handling.
# Call update regularly to handle DPAD button debouncing
#
# leftPressed, rightPressed, upPressed, downPressed:
#   Indicates if the corresponding button is currently pressed
#
# leftPressedEvent, rightPressedEvent, upPressedEvent, upPressedEvent:
#   Indicates if the corresponding button was just pressed
#
# leftReleasedEvent, rightReleasedEvent, upReleasedEvent, upReleasedEvent:
#   Indicates if the corresponding button was just released
#
class PiperDpad:
    def __init__(self, dpad_l_pin=board.D3, dpad_r_pin=board.D4, dpad_u_pin=board.D1, dpad_d_pin=board.D0):
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

    def update(self):
        self.left.update()
        self.right.update()
        self.up.update()
        self.down.update()

    def leftPressed(self):
        return not self.left.value

    def leftPressedEvent(self):
        return self.left.fell

    def leftReleasedEvent(self):
        return self.left.rose

    def rightPressed(self):
        return not self.right.value

    def rightPressedEvent(self):
        return self.right.fell

    def rightReleasedEvent(self):
        return self.right.rose

    def upPressed(self):
        return not self.up.value

    def upPressedEvent(self):
        return self.up.fell

    def upReleasedEvent(self):
        return self.up.rose

    def downPressed(self):
        return not self.down.value

    def downPressedEvent(self):
        return self.down.fell

    def downReleasedEvent(self):
        return self.down.rose

################################################################################
# Minecraft button handling
# Call update regularly to handle button debouncing
#
# topPressed, middlePressed, bottomPressed
#   Indicates if the corresponding button is currently pressed
#
# topPressedEvent, middlePressedEvent, bottomPressedEvent
#   Indicates if the corresponding button was just pressed
#
# topReleasedEvent, middleReleasedEvent, bottomReleasedEvent
#   Indicates if the corresponding button was just released
#
class PiperMineCraftButtons:
    def __init__(self, mc_top_pin=board.SCK, mc_middle_pin=board.MOSI, mc_bottom_pin=board.MISO):
        # Setup Minecraft Buttons
        #
        if mc_top_pin is not None:
            self.mc_top_pin = DigitalInOut(mc_top_pin)
            self.mc_top_pin.direction = Direction.INPUT
            self.mc_top_pin.pull = Pull.UP
            self.mc_top = Debouncer(self.mc_top_pin)
        else:
            self.mc_top = None

        if mc_middle_pin is not None:
            self.mc_middle_pin = DigitalInOut(mc_middle_pin)
            self.mc_middle_pin.direction = Direction.INPUT
            self.mc_middle_pin.pull = Pull.UP
            self.mc_middle = Debouncer(self.mc_middle_pin)
        else:
            self.mc_middle = None

        if mc_bottom_pin is not None:
            self.mc_bottom_pin = DigitalInOut(mc_bottom_pin)
            self.mc_bottom_pin.direction = Direction.INPUT
            self.mc_bottom_pin.pull = Pull.UP
            self.mc_bottom = Debouncer(self.mc_bottom_pin)
        else:
            self.mc_bottom = None

    def update(self):
        if self.mc_top:
            self.mc_top.update()
        if self.mc_middle:
            self.mc_middle.update()
        if self.mc_bottom:
            self.mc_bottom.update()

    def topPressed(self):
        if self.mc_top:
            return not self.mc_top.value
        else:
            return False

    def topPressedEvent(self):
        if self.mc_top:
            return self.mc_top.fell
        else:
            return False

    def topReleasedEvent(self):
        if self.mc_top:
            return self.mc_top.rose
        else:
            return False

    def middlePressed(self):
        if self.mc_middle:
            return not self.mc_middle.value
        else:
            return False

    def middlePressedEvent(self):
        if self.mc_middle:
            return self.mc_middle.fell
        else:
            return False

    def middleReleasedEvent(self):
        if self.mc_middle:
            return self.mc_middle.rose
        else:
            return False

    def bottomPressed(self):
        if self.mc_bottom:
            return not self.mc_bottom.value
        else:
            return False

    def bottomPressedEvent(self):
        if self.mc_bottom:
            return self.mc_bottom.fell
        else:
            return False

    def bottomReleasedEvent(self):
        if self.mc_bottom:
            return self.mc_bottom.rose
        else:
            return False

