#Script to check the currents Ia, Id and Ib
#!/usr/bin/env python3
import mlr1daqboard
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import time
import argparse
from time import sleep


apts = mlr1daqboard.APTSDAQBoard()
print(f"Currents after Proximity ON: Ia = {apts.read_isenseA():0.2f} mA, Id = {apts.read_isenseD():0.2f} mA, Ib = {apts.read_isenseB():0.2f} mA ")

for n in range(16):
    sleep(1)
    print(f"Currents after Proximity ON: Ia = {apts.read_isenseA():0.2f} mA, Id = {apts.read_isenseD():0.2f} mA, Ib = {apts.read_isenseB():0.2f} mA ")



