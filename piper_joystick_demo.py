# Demo the Piper Command Center Joystick library
#
import board
from digitalio import DigitalInOut, Direction, Pull
from adafruit_hid.mouse import Mouse
import usb_hid
from piper_joystick import PiperJoystickAxis

# Provide a ground for the joystick - this is to facilitate
# easier wiring
joystick_gnd = DigitalInOut(board.A5)
joystick_gnd.direction = Direction.OUTPUT
joystick_gnd.value = 0

x_axis = PiperJoystickAxis(board.A4, outputScale=20)
y_axis = PiperJoystickAxis(board.A3, outputScale=20)

mouse = Mouse(usb_hid.devices)
while True:
    dx = x_axis.readJoystickAxis()
    dy = y_axis.readJoystickAxis()
    mouse.move(x=dx, y=dy)
