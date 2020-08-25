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
# *** Handle all built-in Piper Command Center functionality:
#
# from piper_command_center_modes import PiperCommandCenter
# pcc = PiperCommandCenter()
# while True:
#     pcc.process()
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

from piper_command_center import PiperJoystickAxis, PiperJoystickZ, PiperDpad, PiperMineCraftButtons

import adafruit_dotstar
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode
from adafruit_hid.mouse import Mouse
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
import board
from digitalio import DigitalInOut, Direction, Pull
import supervisor
import time
import usb_hid

__version__ = "0.1"
__repo__ = "https://github.com/derhexenmeister/CommandCenter.git"

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

    def process_repl_cmds(self):
        # Assume that the command will be pasted, because input()
        # will block until end of line
        #
        if supervisor.runtime.serial_bytes_available:
            cmd = input()
            exec(cmd)

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
        self.process_repl_cmds()

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
                    self.state = _KEYBOARD
                    self.releaseJoystickHID()
        elif self.state == _KEYBOARD:
            self.dotstar_led[0] = (0, 0, 255)
            if self.joy_z.zPressed() and not self.minecraftbuttons.bottomPressed():
                self.timer = time.monotonic()
                self.state = _KWAITING_TO_J
            elif self.joy_z.zPressed() and self.minecraftbuttons.bottomPressed():
                self.timer = time.monotonic()
                self.state = _KWAITING_TO_MC
        elif self.state == _KWAITING_TO_J:
            if not self.joy_z.zPressed() or self.minecraftbuttons.bottomPressed():
                self.state = _KEYBOARD
                self.up_pressed = False
                self.down_pressed = False
                self.left_pressed = False
                self.right_pressed = False
            else:
                if time.monotonic() - self.timer > 1.0:
                    self.state = _JOYSTICK
                    self.releaseKeyboardHID()
        elif self.state == _KWAITING_TO_MC:
            if not self.joy_z.zPressed() or not self.minecraftbuttons.bottomPressed():
                self.state = _KEYBOARD
                self.up_pressed = False
                self.down_pressed = False
                self.left_pressed = False
                self.right_pressed = False
            else:
                if time.monotonic() - self.timer > 1.0:
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
                self.state = _MWAITING
        elif self.state == _MWAITING:
            if not self.joy_z.zPressed() or not self.dpad.upPressed() or not self.dpad.downPressed() or not self.dpad.leftPressed() or not self.dpad.rightPressed():
                self.state = _MINECRAFT
            else:
                if time.monotonic() - self.timer > 1.0:
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

