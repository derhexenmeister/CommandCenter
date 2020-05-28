# Demo the Piper Command Center Joystick library
#
import board
from digitalio import DigitalInOut, Direction, Pull
from adafruit_hid.mouse import Mouse
import usb_hid
from adafruit_debouncer import Debouncer
from piper_joystick import PiperJoystickAxis

# Setup DPAD
#
left_pin = DigitalInOut(board.D3)
left_pin.direction = Direction.INPUT
left_pin.pull = Pull.UP
left = Debouncer(left_pin)

right_pin = DigitalInOut(board.D4)
right_pin.direction = Direction.INPUT
right_pin.pull = Pull.UP
right = Debouncer(right_pin)

# Provide a ground for the joystick - this is to facilitate
# easier wiring
joystick_gnd = DigitalInOut(board.A5)
joystick_gnd.direction = Direction.OUTPUT
joystick_gnd.value = 0

# Setup joystick pins, and choose an outputScale which results in an
# easy to control mouse pointer
#
x_axis = PiperJoystickAxis(board.A4, outputScale=20)
y_axis = PiperJoystickAxis(board.A3, outputScale=20)

mouse = Mouse(usb_hid.devices)
while True:
    # Call the debouncing library frequently
    left.update()
    right.update()
    dx = x_axis.readJoystickAxis()
    dy = y_axis.readJoystickAxis()

    mouse.move(x=dx, y=dy)

    if left.fell:
        mouse.press(Mouse.LEFT_BUTTON)
    elif left.rose:
        mouse.release(Mouse.LEFT_BUTTON)

    if right.fell:
        mouse.press(Mouse.RIGHT_BUTTON)
    elif right.rose:
        mouse.release(Mouse.RIGHT_BUTTON)

