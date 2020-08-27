################################################################################
# The MIT License (MIT)
#
# Copyright (c) 2020 Matthew Matz
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
## Sets the specified pin to be an output and to the specified logic level
def setPin(__pinName, __pinState):
  __pinName.direction = Direction.OUTPUT
  __pinName.value = __pinState

## Reads the specified pin by setting it to an input and setting it's pull-up/down and then returning its value
def checkPin(__pinName, __pinPull):
  __pinName.direction = Direction.INPUT
  __pinName.pull = __pinPull
  return __pinName.value

## reads an analog voltage from the specified pin
def readVoltage(__pinName):
  return (__pinName.value * 3.3) / 65536

## instructs the connected computer to play a sound by sending control characters and the name
## (or instructions related to) the specified sound
def playSound(_soundName): print(chr(19), _soundName, chr(19), end="")

## instructs the connected to computer to display the specified string in the specified color in pop-up
def shout(_color, _text): print(chr(18), str(_color) + "|" + str(_text), chr(18), end="")

## translates emojis to their corresponding control characters
def emojiCharacter(c):
  if c == "in-love": return chr(20)
  if c == "sad": return chr(21)
  if c == "happy": return chr(22)
  if c == "thinking": return chr(23)
  if c == "quiet": return chr(24)
  if c == "confused": return chr(25)
  if c == "suspicious": return chr(26)
  if c == "unhappy": return chr(27)
  if c == "bored": return chr(28)
  if c == "surprised": return chr(29)

## compares two colors (3-tuples) and outputs a value from 0 (opposite) to 100 (the same).
def colorCompare(_a, _b):
  try:
    _c = (abs(_a[0] - _b[0]) + abs(_a[1] - _b[1]) + abs(_a[2] - _b[2])) * 20 / 153
  except:
    return 0
  return _c

## compares two numbers (int or float) and outputs a value from 0 (very different) to 100 (the same).
def numberCompare(_a, _b):
  try:
    _c = (1 - abs(_a-_b)/(abs(_a) + abs(_b))) * 100
  except:
    return 0
  return _c

## compares two strings and outputs a value from 0 (very different) to 100 (the same).
def stringCompare(_a, _b):
  try:
    _c = set(list(_a))
    _d = set(list(_b))
    _e = _c.intersection(_d)
    _f = (float(len(_e)) / (len(_c) + len(_d) - len(_e))) * 100
  except:
    return 0
  return _f
