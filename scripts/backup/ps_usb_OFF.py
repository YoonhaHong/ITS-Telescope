#!/usr/bin/python3
from labequipment import HAMEG

h=HAMEG('/dev/PS_USB_TRG')

h.power(False,1)
