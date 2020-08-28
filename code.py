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
# This file enables the Piper Command Center to function as a
# joystick. This does not rely on anything in the lib directory, it's
# using only built-in libraries and is otherwise self-contained.
#
from adafruit_debouncer import Debouncer
import adafruit_dotstar
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode
from adafruit_hid.keycode import Keycode
from adafruit_hid.mouse import Mouse
from analogio import AnalogIn
import board
from digitalio import DigitalInOut, Direction, Pull
from math import copysign
import supervisor
import time
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

    def deinit(self):
        self.pin.deinit()

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

    def deinit(self):
        self.joy_z_pin.deinit()

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

    def deinit(self):
        self.up_pin.deinit()
        self.down_pin.deinit()
        self.left_pin.deinit()
        self.right_pin.deinit()

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
# Handle all Piper Command Center joystick functionality
#

# States
#
_UNWIRED        = 0
_WAITING        = 1
_JOYSTICK       = 2
_JWAITING       = 3
_USERCODE       = 4

class PiperCommandCenter:
    def __init__(self, joy_x_pin=board.A4, joy_y_pin=board.A3, joy_z_pin=board.D2, joy_gnd_pin=board.A5, dpad_l_pin=board.D3, dpad_r_pin=board.D4, dpad_u_pin=board.D1, dpad_d_pin=board.D0, outputScale=20.0, deadbandCutoff=0.1, weight=0.2):
        self.x_axis = PiperJoystickAxis(joy_x_pin, outputScale=outputScale, deadbandCutoff=deadbandCutoff, weight=weight)
        self.y_axis = PiperJoystickAxis(joy_y_pin, outputScale=outputScale, deadbandCutoff=deadbandCutoff, weight=weight)
        self.joy_z = PiperJoystickZ(joy_z_pin)
        self.dpad = PiperDpad(dpad_l_pin, dpad_r_pin, dpad_u_pin, dpad_d_pin)

        # Drive pin low if requested for easier joystick wiring
        if joy_gnd_pin is not None:
            # Provide a ground for the joystick - this is to facilitate
            # easier wiring
            self.joystick_gnd = DigitalInOut(joy_gnd_pin)
            self.joystick_gnd.direction = Direction.OUTPUT
            self.joystick_gnd.value = 0

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
        self.dotstar_led.brightness = 0.2
        self.up_pressed = False
        self.down_pressed = False
        self.left_pressed = False
        self.right_pressed = False

    def process(self):
        # Call the debouncing library frequently
        self.joy_z.update()
        self.dpad.update()

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
            if self.joy_z.zPressed():
                self.timer = time.monotonic()
                self.state = _JWAITING
        elif self.state == _JWAITING:
            if not self.joy_z.zPressed():
                self.state = _JOYSTICK
            else:
                if time.monotonic() - self.timer > 1.0:
                    self.mouse.release(Mouse.LEFT_BUTTON)
                    self.mouse.release(Mouse.RIGHT_BUTTON)
                    self.state = _USERCODE
        elif self.state == _USERCODE:
            self.dotstar_led[0] = (0, 0, 0)
            self.dotstar_led.deinit()
            self.joystick_gnd.deinit()
            self.x_axis.deinit()
            self.y_axis.deinit()
            self.dpad.deinit()
            self.joy_z.deinit()
            try:
                # Load usercode.py
                __import__("usercode")
            except ImportError:
                print("Missing usercode.py file")
            # If we get here due to an exception or the user code exiting
            # then restart as it's probably going to by the most stable
            # strategy
            #
            supervisor.reload()

        # Command Center Joystick Handling
        #
        if self.state == _JOYSTICK or self.state == _JWAITING:
            # Determine mouse wheel direction
            #
            dwheel = 0
            if self.dpad.upPressed():
                dwheel=-1
            elif self.dpad.downPressed():
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

            if self.dpad.leftPressedEvent():
                    self.mouse.press(Mouse.LEFT_BUTTON)
            elif self.dpad.leftReleasedEvent():
                    self.mouse.release(Mouse.LEFT_BUTTON)

            if self.dpad.rightPressedEvent():
                    self.mouse.press(Mouse.RIGHT_BUTTON)
            elif self.dpad.rightReleasedEvent():
                    self.mouse.release(Mouse.RIGHT_BUTTON)

################################################################################
# Start up the joystick handler
#
pcc = PiperCommandCenter()
while True:
    pcc.process()
