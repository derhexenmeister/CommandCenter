# User's program goes here
#
import adafruit_dotstar
from analogio import AnalogIn
import board
from digitalio import DigitalInOut, Direction, Pull
import time

dotstar_led = adafruit_dotstar.DotStar(board.APA102_SCK, board.APA102_MOSI, 1)
dotstar_led[0] = (255, 0, 255)

# Do this just to make sure that the pins are available for use - deinited by code.py
#
left_pin = DigitalInOut(board.D3)
right_pin = DigitalInOut(board.D4)
up_pin = DigitalInOut(board.D1)
down_pin = DigitalInOut(board.D0)
joy_z_pin = DigitalInOut(board.D2)
ypin = AnalogIn(board.A3)
xpin = AnalogIn(board.A4)
gpin = DigitalInOut(board.A5)

print("Running user code")
time.sleep(2)
print("Exiting user code")
