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
# In Minecraft Mode (CYAN LED):
#   Description TBD
#   Requires 3 additional buttons to be wired to SCK, MOSI, MISO
#
################################################################################

from adafruit_debouncer import Debouncer
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode
from adafruit_hid.mouse import Mouse
from analogio import AnalogIn
from digitalio import DigitalInOut, Direction, Pull
from math import copysign
import adafruit_dotstar
import board
import supervisor
import time
import usb_hid

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

################################################################################
# Handle all Piper Command Center built-in functionality
#

# States
#
_UNWIRED        = 0
_WAITING        = 1
_JOYSTICK       = 2
_JWAITING       = 3
_KEYBOARD       = 4
_KWAITING_TO_J  = 5
_KWAITING_TO_MC = 6
_MINECRAFT      = 7
_MWAITING       = 8

# Minecraft modes
#
_MC_DEFAULT     = 0
_MC_FLYINGDOWN  = 1
_MC_SPRINTING   = 2
_MC_CROUCHING   = 3
_MC_UTILITY     = 4

# Keycodes for joystick button press
#                 _MC_DEFAULT    _MC_FLYINGDOWN      _MC_SPRINTING  _MC_CROUCHING  _MC_UTILITY
_MC_JOYSTICK_Z = [Keycode.SPACE, Keycode.LEFT_SHIFT, Keycode.SPACE, Keycode.SPACE, Keycode.F5]

class PiperCommandCenter:
    def __init__(self, joy_x_pin=board.A4, joy_y_pin=board.A3, joy_z_pin=board.D2, joy_gnd_pin=board.A5, dpad_l_pin=board.D3, dpad_r_pin=board.D4, dpad_u_pin=board.D1, dpad_d_pin=board.D0, mc_top_pin=board.SCK, mc_middle_pin=board.MOSI, mc_bottom_pin=board.MISO, outputScale=20.0, deadbandCutoff=0.1, weight=0.2):
        self.x_axis = PiperJoystickAxis(joy_x_pin, outputScale=outputScale, deadbandCutoff=deadbandCutoff, weight=weight)
        self.y_axis = PiperJoystickAxis(joy_y_pin, outputScale=outputScale, deadbandCutoff=deadbandCutoff, weight=weight)
        self.joy_z = PiperJoystickZ(joy_z_pin)
        self.dpad = PiperDpad(dpad_l_pin, dpad_r_pin, dpad_u_pin, dpad_d_pin)
        self.minecraftbuttons = PiperMineCraftButtons(mc_top_pin, mc_middle_pin, mc_bottom_pin)

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
        self.mc_mode = _MC_DEFAULT
        self.mc_flyingdown_req = False
        self.mc_sprinting_req = False
        self.mc_crouching_req = False
        self.mc_utility_req = False

#    def process_repl_cmds(self):
#        # Assume that the command will be pasted, because input()
#        # will block until end of line
#        #
#        if supervisor.runtime.serial_bytes_available:
#            cmd = input()
#            exec(cmd)

    def releaseJoystickHID(self):
        self.mouse.release(Mouse.LEFT_BUTTON)
        self.mouse.release(Mouse.RIGHT_BUTTON)

    def releaseKeyboardHID(self):
        self.keyboard.release(Keycode.UP_ARROW)
        self.keyboard.release(Keycode.DOWN_ARROW)
        self.keyboard.release(Keycode.LEFT_ARROW)
        self.keyboard.release(Keycode.RIGHT_ARROW)
        self.keyboard.release(Keycode.SPACE)
        self.keyboard.release(Keycode.X)
        self.keyboard.release(Keycode.Z)
        self.keyboard.release(Keycode.C)

    def releaseMinecraftHID(self):
        self.mouse.release(Mouse.LEFT_BUTTON)
        self.mouse.release(Mouse.MIDDLE_BUTTON)
        self.mouse.release(Mouse.RIGHT_BUTTON)

        self.keyboard.release(Keycode.A)
        self.keyboard.release(Keycode.CONTROL)
        self.keyboard.release(Keycode.D)
        self.keyboard.release(Keycode.E)
        self.keyboard.release(Keycode.ESCAPE)
        self.keyboard.release(Keycode.F5)
        self.keyboard.release(Keycode.LEFT_SHIFT)
        self.keyboard.release(Keycode.Q)
        self.keyboard.release(Keycode.S)
        self.keyboard.release(Keycode.SPACE)
        self.keyboard.release(Keycode.W)

    def process(self):
        #self.process_repl_cmds()

        # Call the debouncing library frequently
        self.joy_z.update()
        self.dpad.update()
        self.minecraftbuttons.update()

        dx = self.x_axis.readJoystickAxis()
        dy = self.y_axis.readJoystickAxis()

        # Command Center State Machine
        #
        if self.state == _UNWIRED:
            self.dotstar_led[0] = ((time.monotonic_ns() >> 23) % 256, 0, 0)
            if dx == 0 and dy == 0:
                self.state = _WAITING
                #print("Transition to WAITING")
                self.timer = time.monotonic()
        elif self.state == _WAITING:
            self.dotstar_led[0] = ((time.monotonic_ns() >> 23) % 256, 0, 0)
            if dx != 0 or dy != 0:
                #print("Transition to UNWIRED")
                self.state = _UNWIRED
            else:
                if time.monotonic() - self.timer > 0.5:
                    #print("Transition to JOYSTICK")
                    self.state = _JOYSTICK
        elif self.state == _JOYSTICK:
            self.dotstar_led[0] = (0, 255, 0)
            if self.joy_z.zPressed():
                self.timer = time.monotonic()
                #print("Transition to JWAITING")
                self.state = _JWAITING
        elif self.state == _JWAITING:
            if not self.joy_z.zPressed():
                #print("Transition to JOYSTICK")
                self.state = _JOYSTICK
            else:
                if time.monotonic() - self.timer > 1.0:
                    #print("Transition to KEYBOARD")
                    self.state = _KEYBOARD
                    self.releaseJoystickHID()
        elif self.state == _KEYBOARD:
            self.dotstar_led[0] = (0, 0, 255)
            if self.joy_z.zPressed() and not self.minecraftbuttons.bottomPressed():
                self.timer = time.monotonic()
                #print("Transition to KWAITING_TO_J")
                self.state = _KWAITING_TO_J
            elif self.joy_z.zPressed() and self.minecraftbuttons.bottomPressed():
                self.timer = time.monotonic()
                #print("Transition to KWAITING_TO_MC")
                self.state = _KWAITING_TO_MC
        elif self.state == _KWAITING_TO_J:
            if not self.joy_z.zPressed() or self.minecraftbuttons.bottomPressed():
                #print("Transition to KEYBOARD")
                self.state = _KEYBOARD
                self.up_pressed = False
                self.down_pressed = False
                self.left_pressed = False
                self.right_pressed = False
            else:
                if time.monotonic() - self.timer > 1.0:
                    #print("Transition to JOYSTICK")
                    self.state = _JOYSTICK
                    self.releaseKeyboardHID()
        elif self.state == _KWAITING_TO_MC:
            if not self.joy_z.zPressed() or not self.minecraftbuttons.bottomPressed():
                #print("Transition to KEYBOARD")
                self.state = _KEYBOARD
                self.up_pressed = False
                self.down_pressed = False
                self.left_pressed = False
                self.right_pressed = False
            else:
                if time.monotonic() - self.timer > 1.0:
                    #print("Transition to MINECRAFT")
                    self.state = _MINECRAFT
                    self.releaseKeyboardHID()
        elif self.state == _MINECRAFT:
            if self.mc_mode == _MC_DEFAULT :
                self.dotstar_led[0] = (0, 255, 255) # cyan
            elif self.mc_mode == _MC_FLYINGDOWN:
                self.dotstar_led[0] = (255, 0, 255) # magenta
            elif self.mc_mode == _MC_SPRINTING:
                self.dotstar_led[0] = (255, 128, 128) # pink
            elif self.mc_mode == _MC_CROUCHING:
                self.dotstar_led[0] = (255, 165, 0) # orange
            elif self.mc_mode == _MC_UTILITY:
                self.dotstar_led[0] = (255, 255, 0) # yellow

            if self.joy_z.zPressed() and self.dpad.upPressed() and self.dpad.downPressed() and self.dpad.leftPressed() and self.dpad.rightPressed():
                self.timer = time.monotonic()
                #print("Transition to MWAITING")
                self.state = _MWAITING
        elif self.state == _MWAITING:
            if not self.joy_z.zPressed() or not self.dpad.upPressed() or not self.dpad.downPressed() or not self.dpad.leftPressed() or not self.dpad.rightPressed():
                #print("Transition to MINECRAFT")
                self.state = _MINECRAFT
            else:
                if time.monotonic() - self.timer > 1.0:
                    #print("Transition to JOYSTICK")
                    self.state = _JOYSTICK
                    self.releaseMinecraftHID()

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

        # Command Center Keyboard Handling
        #
        if self.state == _KEYBOARD or self.state == _KWAITING_TO_J or self.state == _KWAITING_TO_MC:
            if self.dpad.upPressedEvent():
                self.keyboard.press(Keycode.SPACE)
            elif self.dpad.upReleasedEvent():
                self.keyboard.release(Keycode.SPACE)

            if self.dpad.downPressedEvent():
                self.keyboard.press(Keycode.X)
            elif self.dpad.downReleasedEvent():
                self.keyboard.release(Keycode.X)

            if self.dpad.leftPressedEvent():
                self.keyboard.press(Keycode.Z)
            elif self.dpad.leftReleasedEvent():
                self.keyboard.release(Keycode.Z)

            if self.dpad.rightPressedEvent():
                self.keyboard.press(Keycode.C)
            elif self.dpad.rightReleasedEvent():
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

        # Command Center Minecraft Handling
        #
        if self.state == _MINECRAFT:
            # Modifier button
            #
            if self.minecraftbuttons.bottomPressed():
                if self.joy_z.zPressedEvent():
                    self.mc_flyingdown_req = True
                    self.mc_sprinting_req  = False
                    self.mc_crouching_req  = False
                    self.mc_utility_req    = False
                elif self.dpad.upPressedEvent():
                    self.mc_flyingdown_req = False
                    self.mc_sprinting_req  = True
                    self.mc_crouching_req  = False
                    self.mc_utility_req    = False
                elif self.dpad.downPressedEvent():
                    self.mc_flyingdown_req = False
                    self.mc_sprinting_req  = False
                    self.mc_crouching_req  = True
                    self.mc_utility_req    = False
                elif self.dpad.leftPressedEvent():
                    self.mc_flyingdown_req = False
                    self.mc_sprinting_req  = False
                    self.mc_crouching_req  = False
                    self.mc_utility_req    = True

            if self.minecraftbuttons.bottomReleasedEvent():
                self.releaseMinecraftHID()
                if self.mc_flyingdown_req:
                    self.mc_mode = _MC_FLYINGDOWN
                    self.mc_flyingdown_req = False
                elif self.mc_sprinting_req:
                    self.mc_mode = _MC_SPRINTING
                    self.mc_sprinting_req = False
                    self.keyboard.press(Keycode.CONTROL)
                elif self.mc_crouching_req:
                    self.mc_mode = _MC_CROUCHING
                    self.mc_crouching_req = False
                    self.keyboard.press(Keycode.LEFT_SHIFT)
                elif self.mc_utility_req:
                    self.mc_mode = _MC_UTILITY
                    self.mc_utility_req = False
                else:
                    self.mc_mode = _MC_DEFAULT

            # Joystick functionality for mouse movement is always active
            #
            # Mouse movement is paced - may need to adjust
            #
            if time.monotonic() - self.last_mouse > 0.005:
                self.last_mouse = time.monotonic()
                self.mouse.move(x=dx, y=dy)

            # Top and bottom buttons changed by mod key in default mode
            #
            if self.mc_mode == _MC_DEFAULT and self.minecraftbuttons.bottomPressed():
                if self.minecraftbuttons.topPressedEvent():
                    self.keyboard.press(Keycode.Q)
                elif self.minecraftbuttons.topReleasedEvent():
                    self.keyboard.release(Keycode.Q)

                if self.minecraftbuttons.middlePressedEvent():
                    self.mouse.press(Mouse.MIDDLE_BUTTON)
                elif self.minecraftbuttons.middleReleasedEvent():
                    self.mouse.release(Mouse.MIDDLE_BUTTON)
            else:
                if self.minecraftbuttons.topPressedEvent():
                    self.mouse.press(Mouse.LEFT_BUTTON)
                elif self.minecraftbuttons.topReleasedEvent():
                    self.mouse.release(Mouse.LEFT_BUTTON)

                if self.minecraftbuttons.middlePressedEvent():
                    self.mouse.press(Mouse.RIGHT_BUTTON)
                elif self.minecraftbuttons.middleReleasedEvent():
                    self.mouse.release(Mouse.RIGHT_BUTTON)

            # Don't generate key presses for buttons if modifier key is pressed
            #
            if not self.minecraftbuttons.bottomPressed():
                # Joystick button changes based on minecraft mode
                #
                if self.joy_z.zPressedEvent():
                    self.keyboard.press(_MC_JOYSTICK_Z[self.mc_mode])
                elif self.joy_z.zReleasedEvent():
                    self.keyboard.release(_MC_JOYSTICK_Z[self.mc_mode])

                # DPAD buttons special in utility mode
                #
                if self.mc_mode == _MC_UTILITY:
                    if self.dpad.upPressedEvent():
                        self.mouse.move(wheel=-1)

                    if self.dpad.downPressedEvent():
                        self.mouse.move(wheel=1)

                    if self.dpad.leftPressedEvent():
                        self.keyboard.press(Keycode.E)
                    elif self.dpad.leftReleasedEvent():
                        self.keyboard.release(Keycode.E)

                    if self.dpad.rightPressedEvent():
                        self.keyboard.press(Keycode.ESCAPE)
                    elif self.dpad.rightReleasedEvent():
                        self.keyboard.release(Keycode.ESCAPE)
                else:
                    if self.dpad.upPressedEvent():
                        self.keyboard.press(Keycode.W)
                    elif self.dpad.upReleasedEvent():
                            self.keyboard.release(Keycode.W)

                    if self.dpad.downPressedEvent():
                        self.keyboard.press(Keycode.S)
                    elif self.dpad.downReleasedEvent():
                        self.keyboard.release(Keycode.S)

                    if self.dpad.leftPressedEvent():
                        self.keyboard.press(Keycode.A)
                    elif self.dpad.leftReleasedEvent():
                        self.keyboard.release(Keycode.A)

                    if self.dpad.rightPressedEvent():
                        self.keyboard.press(Keycode.D)
                    elif self.dpad.rightReleasedEvent():
                        self.keyboard.release(Keycode.D)

################################################################################
# Handle all built-in Piper Command Center functionality:
#
pcc = PiperCommandCenter()
while True:
    pcc.process()