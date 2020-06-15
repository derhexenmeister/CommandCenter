import time
import board

import grove_ultrasonic_ranger

sonar = grove_ultrasonic_ranger.GroveUltrasonicRanger(sig_pin=board.D7)

while True:
    try:
        print((sonar.distance,))
    except RuntimeError as e:
        print("Retrying due to exception =", e)
        pass
    time.sleep(0.1)
