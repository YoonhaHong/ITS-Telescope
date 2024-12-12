#Script to check the currents Ia, Ib and Id during power on and each DAC settings

#!/usr/bin/env python3
import mlr1daqboard
import sys
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import time
import datetime
from datetime import datetime
import logging
import argparse
from time import sleep

# setting the parameters now to save idle time later
step_spleep_fine=0.01
step_fine=1000
step_spleep_coarse=1
step_coarse=600
currentA=np.empty(step_fine)
currentD=np.empty(step_fine)
step_time=np.empty(step_fine)

print("timestamp i_a i_d i_b")

apts = mlr1daqboard.APTSDAQBoard()

sleepTime = 0

print(1000000*time.time(),apts.read_isenseA(),apts.read_isenseD(),apts.read_isenseB(),"beforeLDO32->ON")
apts.write_register(14,0x32,0x1) # LDO32 -> ON
print(1000000*time.time(),apts.read_isenseA(),apts.read_isenseD(),apts.read_isenseB(),"afterLDO32->ON")

print(1000000*time.time(),apts.read_isenseA(),apts.read_isenseD(),apts.read_isenseB(),"beforeLDO33->ON")
apts.write_register(14,0x33,0x1) # LDO33 -> ON
print(1000000*time.time(),apts.read_isenseA(),apts.read_isenseD(),apts.read_isenseB(),"afterLDO33->ON")

sleep(0.001)

print(1000000*time.time(),apts.read_isenseA(),apts.read_isenseD(),apts.read_isenseB(),"beforeU28ref")
apts.write_register( 0x04, 0x01, (0x8<<24)|1 ) # set DAC U28 internal reference
print(1000000*time.time(),apts.read_isenseA(),apts.read_isenseD(),apts.read_isenseB(),"afterU28ref")

print(1000000*time.time(),apts.read_isenseA(),apts.read_isenseD(),apts.read_isenseB(),"beforeU29ref")
apts.write_register( 0x05, 0x01, (0x8<<24)|1 ) # set DAC U29 internal reference
print(1000000*time.time(),apts.read_isenseA(),apts.read_isenseD(),apts.read_isenseB(),"afterU29ref")

# print(1000000*time.time(),apts.read_isenseA(),apts.read_isenseD(),apts.read_isenseB(),"beforeAllToZero")
# for dac in apts.DAC_REGS.keys(): apts.set_dac(dac,0) # all dacs to 0
# sleep(0.002)
# print(1000000*time.time(),apts.read_isenseA(),apts.read_isenseD(),apts.read_isenseB(),"afterAllToZero")

sleep(0.002)

print(1000000*time.time(),apts.read_isenseA(),apts.read_isenseD(),apts.read_isenseB(),"beforeCE_COL_AP_IBIASN")
apts.set_idac('CE_COL_AP_IBIASN',             800) # unit uA
print(1000000*time.time(),apts.read_isenseA(),apts.read_isenseD(),apts.read_isenseB(),"beforeCE_COL_AP_IBIASN")

sleep(sleepTime)

print(1000000*time.time(),apts.read_isenseA(),apts.read_isenseD(),apts.read_isenseB(),"beforeCE_MAT_AP_IBIAS4SF_DP_IBIASF")
apts.set_idac('CE_MAT_AP_IBIAS4SF_DP_IBIASF', 6000)
print(1000000*time.time(),apts.read_isenseA(),apts.read_isenseD(),apts.read_isenseB(),"afterCE_MAT_AP_IBIAS4SF_DP_IBIASF")

sleep(sleepTime)

print(1000000*time.time(),apts.read_isenseA(),apts.read_isenseD(),apts.read_isenseB(),"beforeCE_PMOS_AP_DP_IRESET")
apts.set_idac('CE_PMOS_AP_DP_IRESET',         0.1)
print(1000000*time.time(),apts.read_isenseA(),apts.read_isenseD(),apts.read_isenseB(),"afterCE_PMOS_AP_DP_IRESET")

sleep(sleepTime)

print(1000000*time.time(),apts.read_isenseA(),apts.read_isenseD(),apts.read_isenseB(),"beforeAP_IBIASP_DP_IDB")
apts.set_idac('AP_IBIASP_DP_IDB',             80.0)
print(1000000*time.time(),apts.read_isenseA(),apts.read_isenseD(),apts.read_isenseB(),"afterAP_IBIASP_DP_IDB")

sleep(sleepTime)

# for n in range(step_fine):
#     print(1000000*time.time(),apts.read_isenseA(),apts.read_isenseD(),apts.read_isenseB())
#     sleep(step_spleep_fine)

print(1000000*time.time(),apts.read_isenseA(),apts.read_isenseD(),apts.read_isenseB(),"beforeAP_IBIAS3_DP_IBIAS")
apts.set_idac('AP_IBIAS3_DP_IBIAS',           800.0)
print(1000000*time.time(),apts.read_isenseA(),apts.read_isenseD(),apts.read_isenseB(),"afterAP_IBIAS3_DP_IBIAS")

sleep(sleepTime)

# for n in range(step_fine):
#     print(1000000*time.time(),apts.read_isenseA(),apts.read_isenseD(),apts.read_isenseB())
#     sleep(step_spleep_fine)

print(1000000*time.time(),apts.read_isenseA(),apts.read_isenseD(),apts.read_isenseB(),"beforeCE_VOFFSET_AP_DP_VH")
apts.set_vdac('CE_VOFFSET_AP_DP_VH',          1200) # unit mV
print(1000000*time.time(),apts.read_isenseA(),apts.read_isenseD(),apts.read_isenseB(),"afterCE_VOFFSET_AP_DP_VH")

sleep(sleepTime)

print(1000000*time.time(),apts.read_isenseA(),apts.read_isenseD(),apts.read_isenseB(),"beforeAP_VRESET")
apts.set_vdac('AP_VRESET',                    200)
print(1000000*time.time(),apts.read_isenseA(),apts.read_isenseD(),apts.read_isenseB(),"afterAP_VRESET")

#print("----DACS ARE NOW SET----")

#sleep(2)

for n in range(step_fine):
    step_time[n]=1000000*time.time()
    currentA[n]=apts.read_isenseA()
    currentD[n]=apts.read_isenseD()
    #print(f"After:{step_time[n]:0.2f} seconds, Currents after Proximity ON: Ia = {apts.read_isenseA():0.2f} mA, Id = {apts.read_isenseD():0.2f} mA, Ib = {apts.read_isenseB():0.2f} mA ")
    print(1000000*time.time(),apts.read_isenseA(),apts.read_isenseD(),apts.read_isenseB())
    sleep(step_spleep_fine)
    
    
plt.plot(step_time, currentA)
plt.plot(step_time, currentD)
plt.show()

exit()

for n in range(step_coarse):
    print(1000000*time.time(),apts.read_isenseA(),apts.read_isenseD(),apts.read_isenseB())
    sleep(step_spleep_coarse)


