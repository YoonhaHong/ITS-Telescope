#!/usr/bin/python3
from labequipment import HAMEG

h=HAMEG('/dev/PS_BABY_TS')

print('Powering ON...')
h.power(True, 1)

s = h.status()
for i in range(len(s[0])):
    power = f'{bool(s[0][i])}'
    voltage = f'{(s[1][i]):>4}'
    current = f'{int(s[2][i]*1000):>4}'
    print(f'| Channel {i+1} - Powered: {power} \t Voltage: {voltage}V \t Fuse: {current}mA |')
