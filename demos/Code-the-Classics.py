###############################################################################
# Simple Piper Command Center CircuitPython Code
# Tested on: Adafruit ItsyBitsy M4 Express
#
# Thu 23 April 2020
###############################################################################
# This is a simple example of a game controller designed to play the games in
# the book "Code the Classics Volume 1" published by Raspberry Pi Trading Ltd.
# The games themselves are programmed in Python using Pygame Zero by Raspberry
# Pi founder Eben Upton.
#
# The book's PDF is here:
#    https://wireframe.raspberrypi.org/books/code-the-classics1
# And the code is here:
#    https://github.com/Wireframe-Magazine/Code-the-Classics
#
# Player 1 Mode
# ---------------
# DPAD - up/left/right sends up/left/right arrow codes
# DPAD - down sends a space which is often used as a fire cmd
# Joystick - sends up/down/left/right arrow codes
# Joystick press - sends space
#
# Player 2 Mode
# ---------------
# DPAD - up/left/right sends up/left/right codes (*)
# DPAD - down sends a left shift which is used as a kick command in soccer
# Joystick - sends up/down/left/right codes (*)
# Joystick press - sends a left shift which is used as a kick command in soccer
# Up   = k and w keys
# Down = m and s keys
# Left = a key
# Right = d key
#
# These mappings work well for most games, but jumping down
# may be awkward in bunner. Use the joystick if needed. Most
# jumping is in the up/left/right directions so it seems like
# a good compromise until mode switching is implemented.
#
# TBD
# It would be nice to have multiple modes for different games.
# Also a mode where the joystick controlled the mouse.
# Perhaps a rapid fire mode would be useful for some games?
#
###############################################################################
# Assumes that the Piper Command Center is wired as follows:
#
# +-------------+---------------------+--------------------+
# |Button Pad   |ItsyBitsy M4 Express |Description         |
# +-------------+---------------------+--------------------+
# |Pin 4 Green  |D7                   |Right/East, digital |
# +-------------+---------------------+--------------------+
# |Pin 3 Yellow |D9                   |Left/West, digital  |
# +-------------+---------------------+--------------------+
# |Pin 2 Orange |D10                  |Down/South, digital |
# +-------------+---------------------+--------------------+
# |Pin 1 Purple |D13                  |Up/North, digital   |
# +-------------+---------------------+--------------------+
# |GND   Brown  |GND                  |                    |
# +-------------+---------------------+--------------------+
#
# +-----------+---------------------+-----------------------------+
# |Joystick   |ItsyBitsy M4 Express |Description                  |
# +-----------+---------------------+-----------------------------+
# |VCC Red    |3V                   |                             |
# +-----------+---------------------+-----------------------------+
# |Y   Blue   |A3                   |Up-down/North-south, analog  |
# +-----------+---------------------+-----------------------------+
# |X   Grey   |A2                   |Left-right/West-East, analog |
# +-----------+---------------------+-----------------------------+
# |S   White  |D2                   |Push button, digital         |
# +-----------+---------------------+-----------------------------+
# |GND Black  |GND                  |                             |
# +-----------+---------------------+-----------------------------+
#
# +-----------+---------------------+-----------------------------+
# |Touch Pad  |ItsyBitsy M4 Express |Description                  |
# +-----------+---------------------+-----------------------------+
# |Left       |D12                  | TBD                         |
# +-----------+---------------------+-----------------------------+
# |Right      |D11                  | TBD                         |
# +-----------+---------------------+-----------------------------+
#
# Some of the above pin choices were made to leave pins with special
# capabilities free for other experiments
###############################################################################
import board
from digitalio import DigitalInOut, Direction, Pull
from analogio import AnalogIn
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode
from adafruit_debouncer import Debouncer
import touchio

# Which player 1 or 2?
# TBD - allow this to change on-the-fly
#
player = 1

# Directional pad pins need pull-ups enabled
#
right_pin = DigitalInOut(board.D7)
right_pin.direction = Direction.INPUT
right_pin.pull = Pull.UP
right = Debouncer(right_pin)

left_pin = DigitalInOut(board.D9)
left_pin.direction = Direction.INPUT
left_pin.pull = Pull.UP
left = Debouncer(left_pin)

up_pin = DigitalInOut(board.D13)
up_pin.direction = Direction.INPUT
up_pin.pull = Pull.UP
up = Debouncer(up_pin)

down_pin = DigitalInOut(board.D10)
down_pin.direction = Direction.INPUT
down_pin.pull = Pull.UP
down = Debouncer(down_pin)

# Joystick switch needs pull-ups enabled
joy_press_pin = DigitalInOut(board.D2)
joy_press_pin.direction = Direction.INPUT
joy_press_pin.pull = Pull.UP
joy_press = Debouncer(joy_press_pin)

# Joystick pins are analog inputs
x = AnalogIn(board.A2)
y = AnalogIn(board.A3)

# Touch pins
touch_right = touchio.TouchIn(board.D11) # Requires 1 Mohm pulldown
touch_left = touchio.TouchIn(board.D12)  # Requires 1 Mohm pulldown

# We'll use these to detect button/joystick presses/movement
up_state    = False
down_state  = False
left_state  = False
right_state = False
space_state = False

keyboard = Keyboard(usb_hid.devices)
keyboard_layout = KeyboardLayoutUS(keyboard)  # Change for non-US

while True:
    # Placeholder
    #if touch_left.value:
    #    print("Left touched")
    #if touch_right.value:
    #    print("Right touched")

    # Call the debouncing library frequently
    right.update()
    left.update()
    up.update()
    down.update()
    joy_press.update()

    up_pressed    = False
    down_pressed  = False
    left_pressed  = False
    right_pressed = False
    space_pressed = False

    # Directional PAD
    #
    if not up.value:
        up_pressed = True
    elif not down.value:
        space_pressed = True # intentional
    elif not left.value:
        left_pressed = True
    elif not right.value:
        right_pressed = True

    # This is the joypad switch
    #
    elif not joy_press.value:
        space_pressed = True

    # Joystick (scale to roughly -1 to +1)
    # It might be better not to convert these to floats, but it
    # also is convenient if we ever use them for other purposes.
    #
    left_right = (x.value - 32768)/32768
    up_down = (y.value - 32768)/-32768 # flipped

    # Don't register a key press unless the joystick is moved past
    # a threshold
    #
    if (left_right < -0.25):
        left_pressed = True
    elif (left_right > 0.25):
        right_pressed = True

    if (up_down < -0.25):
        down_pressed = True
    elif (up_down > 0.25):
        up_pressed = True

    # For each type of key, we press it down,
    # release it, or leave it in its current state.
    #
    if not up_state and up_pressed:
        if player == 1:
            keyboard.press(Keycode.UP_ARROW)
        else:
            keyboard.press(Keycode.K)
            keyboard.press(Keycode.W)
        up_state = True
    elif up_state and not up_pressed:
        if player == 1:
            keyboard.release(Keycode.UP_ARROW)
        else:
            keyboard.release(Keycode.K)
            keyboard.release(Keycode.W)
        up_state = False

    if not down_state and down_pressed:
        if player == 1:
            keyboard.press(Keycode.DOWN_ARROW)
        else:
            keyboard.press(Keycode.M)
            keyboard.press(Keycode.S)
        down_state = True
    elif down_state and not down_pressed:
        if player == 1:
            keyboard.release(Keycode.DOWN_ARROW)
        else:
            keyboard.release(Keycode.M)
            keyboard.release(Keycode.S)
        down_state = False

    if not left_state and left_pressed:
        if player == 1:
            keyboard.press(Keycode.LEFT_ARROW)
        else:
            keyboard.press(Keycode.A)
        left_state = True
    elif left_state and not left_pressed:
        if player == 1:
            keyboard.release(Keycode.LEFT_ARROW)
        else:
            keyboard.release(Keycode.A)
        left_state = False

    if not right_state and right_pressed:
        if player == 1:
            keyboard.press(Keycode.RIGHT_ARROW)
        else:
            keyboard.press(Keycode.D)
        right_state = True
    elif right_state and not right_pressed:
        if player == 1:
            keyboard.release(Keycode.RIGHT_ARROW)
        else:
            keyboard.release(Keycode.D)
        right_state = False

    if not space_state and space_pressed:
        if player == 1:
            keyboard.press(Keycode.SPACE)
        else:
            keyboard.press(Keycode.LEFT_SHIFT)
        space_state = True
    elif space_state and not space_pressed:
        if player == 1:
            keyboard.release(Keycode.SPACE)
        else:
            keyboard.release(Keycode.LEFT_SHIFT)
        space_state = False
