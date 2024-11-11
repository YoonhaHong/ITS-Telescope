#!/usr/bin/python3
from labequipment import HAMEG
import argparse

h=HAMEG('/dev/PS_BABY_TS')

def main():
    parser = argparse.ArgumentParser(description="Voltage for v option")
    parser.add_argument('v', type=float, help='Set Voltage')

    args = parser.parse_args()

    h=HAMEG('/dev/PS_BABY_TS')
    h.set_volt(2,args.v)
    print(f'Setting the DUT PSUB Voltage {args.v}V')
    s = h.status()
    for i in range(len(s[0])):
        power = f'{bool(s[0][i])}'
        voltage = f'{s[1][i]:>4}'
        current = f'{int(s[2][i])}'
        print(f'| Channel {i+1} - Powerd: {power} \t Voltage: {voltage}V \t Fuse: {current}mA |')




if __name__ == "__main__":
    main()
