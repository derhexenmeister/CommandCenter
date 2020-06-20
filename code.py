# This file will enable the Piper Command Center to function as a
# game controller
#
from piper_command_center import PiperCommandCenter
pcc = PiperCommandCenter()
while True:
    pcc.process()
