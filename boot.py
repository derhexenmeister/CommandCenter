# See https://learn.adafruit.com/circuitpython-essentials/circuitpython-storage
# for a discussion
#
import board
from digitalio import DigitalInOut, Direction, Pull
import storage

# Use DPAD switches to control filesystem mode 
#
left_pin = DigitalInOut(board.D3)
left_pin.direction = Direction.INPUT
left_pin.pull = Pull.UP

right_pin = DigitalInOut(board.D4)
right_pin.direction = Direction.INPUT
right_pin.pull = Pull.UP

up_pin = DigitalInOut(board.D1)
up_pin.direction = Direction.INPUT
up_pin.pull = Pull.UP

down_pin = DigitalInOut(board.D0)
down_pin.direction = Direction.INPUT
down_pin.pull = Pull.UP
		
# If any DPAD switch is not pressed, then CircuitPython can write to the drive.
# To allow the host to write, press all 4 DPAD buttons during boot.
#
print("DPAD left  = ", left_pin.value)
print("DPAD right = ", right_pin.value)
print("DPAD up    = ", up_pin.value)
print("DPAD down  = ", down_pin.value)
print("Notes:")
print("True = not pressed, False = pressed")
print("Press all DPAD keys to enable host to read/write the CIRCUITPY drive")

readonly = not (left_pin.value or right_pin.value or up_pin.value or down_pin.value)

if readonly:
    print("Mounting CIRCUITPY as read-only to CircuitPython, read/write to host")
else:
    print("Mounting CIRCUITPY as read/write to CircuitPython, read-only to host")

# Handle storage management
#
# readonly (bool) – True when the filesystem should be readonly to CircuitPython
#
storage.remount("/", readonly)
