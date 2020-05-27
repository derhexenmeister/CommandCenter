# CircuitPython demo of Piper Sensor Explorer Kit

import time
import board
import busio
import adafruit_mcp9808
import adafruit_tcs34725
import grove_ultrasonic_ranger

i2c_bus = busio.I2C(board.SCL, board.SDA)

I2C_SCAN = False
TEMPERATURE = False
COLOR3472 = False
ULTRASONIC = True

if I2C_SCAN:
    print("Locking bus for I2C_SCAN")
    while not i2c_bus.try_lock():
        pass

while I2C_SCAN:
    print("I2C addresses found:", [hex(device_address)
                                   for device_address in i2c_bus.scan()])
    time.sleep(2)

print("Skipping I2C_SCAN")

# To initialise using the default address:
if TEMPERATURE:
    print("Creating adafruit_mcp9808")
    mcp = adafruit_mcp9808.MCP9808(i2c_bus)
    print("Done creating adafruit_mcp9808")

# To initialise using a specified address:
# Necessary when, for example, connecting A0 to VDD to make address=0x19
# mcp = adafruit_mcp9808.MCP9808(i2c_bus, address=0x19)

while TEMPERATURE:
    tempC = mcp.temperature
    tempF = tempC * 9 / 5 + 32
    print("Temperature: {} C {} F ".format(tempC, tempF))
    time.sleep(2)

print("Skipping TEMPERATURE")

if COLOR3472:
    print("Creating adafruit_tcs34725")
    sensor = adafruit_tcs34725.TCS34725(i2c_bus)
    print("Done creating COLOR3472")

# Main loop reading color and printing it every second.
while COLOR3472:
    # Read the color temperature and lux of the sensor too.
    print('Color: ({0}, {1}, {2})'.format(*sensor.color_rgb_bytes))
    print('Temperature: {0}K'.format(sensor.color_temperature))
    print('Lux: {0}'.format(sensor.lux))
    # Delay for a second and repeat.
    time.sleep(1.0)

print("Skipping COLOR3472")

if ULTRASONIC:
    print('Detecting distance...')
    sonar = grove_ultrasonic_ranger.GroveUltrasonicRanger(sig_pin=board.D7)
    while True:
        try:
            print('{} cm'.format(sonar.distance,))
        except RuntimeError as e:
            print("Retrying due to exception =", e)
            pass
        time.sleep(0.1)

print("Nothing to do")
