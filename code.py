# This file will enable the Piper Command Center to function as a
# game controller
#
import piper_command_center_modes
pcc = piper_command_center_modes.PiperCommandCenter()
while True:
    pcc.process()
