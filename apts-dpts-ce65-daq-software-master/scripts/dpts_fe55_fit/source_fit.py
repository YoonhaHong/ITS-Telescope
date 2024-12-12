#!/usr/bin/env python3

import ROOT
#ROOT.gROOT.SetBatch(True)
import argparse, json
import glob
import numpy as np
from matplotlib import pyplot as plt
from tqdm import tqdm
import sys, os
from pathlib import Path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils_source_fit import common as f
from utils_source_fit import expBkg_gausSig
from utils_source_fit import linBkg_gausSig
from utils_source_fit import noBkg_2gausSig

#%% MAIN CODE
def analyse_source(npzfile,parameters_file,outdir):
    if not os.path.exists(outdir): os.makedirs(outdir)
    fname = os.path.join(outdir,Path(npzfile).stem)

    tot_calibrated = np.load(npzfile)
    tot_calibrated = tot_calibrated['calibratedToT']

    with open(parameters_file) as jf:
        parameters = json.load(jf)

    xMIN = parameters["xMIN"]
    xMAX = parameters["xMAX"]
    nBIN = parameters["nBIN"]
    dx = (xMAX-xMIN)/nBIN

    results = {}
    results["Si Ka"] = {}
    results["Ar Ka"] = {}
    results["Si escape"] = {}
    results["Mn Ka"] = {}
    results["Mn Kb"] = {}
    results["Calibration"] = {}

#%% 1. ToT storage in ROOT histogram

    hToTPeak1 = ROOT.TH1F('hToTPeak1','Si K#alpha, K#beta, signal + background', nBIN, xMIN, xMAX)
    hToTPeak1_res = ROOT.TH1F('hToTPeak1_res','', nBIN, xMIN, xMAX)
    hToTPeak1_bkg = ROOT.TH1F('hToTPeak1_bkg','Si K#alpha, K#beta, background', nBIN, xMIN, xMAX)
    hToTPeak1_bkg_res = ROOT.TH1F('hToTPeak1_bkg_res','residuals', nBIN, xMIN, xMAX)

    hToTPeak3 = ROOT.TH1F('hToTPeak3','Si_{es}, signal+background', nBIN, xMIN, xMAX)
    hToTPeak3_res = ROOT.TH1F('hToTPeak3_res','residuals', nBIN, xMIN, xMAX)
    hToTPeak3_bkg = ROOT.TH1F('hToTPeak3_bkg','Si_{es}, background', nBIN, xMIN, xMAX)
    hToTPeak3_bkg_res = ROOT.TH1F('hToTPeak3_bkg_res','residuals', nBIN, xMIN, xMAX)
    
    hToTPeak45 = ROOT.TH1F('hToTPeak45','K#alpha, K#beta', nBIN, xMIN, xMAX)
    hToTPeak45_res = ROOT.TH1F('hToTPeak45','residuals', nBIN, xMIN, xMAX)

    for i in tqdm(range(len(tot_calibrated)),desc="Filling histograms..."):
        hToTPeak1.Fill(tot_calibrated[i])
        hToTPeak1_bkg.Fill(tot_calibrated[i])
        hToTPeak3.Fill(tot_calibrated[i])
        hToTPeak3_bkg.Fill(tot_calibrated[i])
        hToTPeak45.Fill(tot_calibrated[i])

    # quantities for branching ratio
    tot_events = 0

#%% 2. Si FLUORESCENCE PEAK
    results, tot_events = expBkg_gausSig.peak_analysis(npzfile,hToTPeak1,hToTPeak1_res,hToTPeak1_bkg,hToTPeak1_bkg_res,parameters["Si Ka"],fname+"_Si-fluorescence_fit.png",nBIN,dx,results,tot_events)
    
#%% 3. Si ESCAPE PEAK
    results["Si escape"], tot_events = linBkg_gausSig.peak_analysis(npzfile,hToTPeak3,hToTPeak3_res,hToTPeak3_bkg,hToTPeak3_bkg_res,parameters["Si escape"],fname+"_Si-escape_fit.png",nBIN,dx,results["Si escape"],tot_events)

#%% 4. Mn Ka, Kb PEAKS
    results["Mn Ka"], results["Mn Kb"], tot_events = noBkg_2gausSig.peak_analysis(npzfile,hToTPeak45,hToTPeak45_res,parameters["Mn Ka Kb"],fname+"_Mn-Ka-Kb_fit.png",nBIN,dx,results["Mn Ka"],results["Mn Kb"],tot_events)

    p1_yield = results["Si Ka"]["events"]/tot_events*100
    p1_yield_err = f.std_dev(results["Si Ka"]["events"],np.sqrt(results["Si Ka"]["events"]),tot_events,np.sqrt(tot_events))*100
    p3_yield = results["Si escape"]["events"]/tot_events*100
    p3_yield_err = f.std_dev(results["Si escape"]["events"],np.sqrt(results["Si escape"]["events"]),tot_events,np.sqrt(tot_events))*100
    p4_yield = results["Mn Ka"]["events"]/tot_events*100
    p4_yield_err = f.std_dev(results["Mn Ka"]["events"],np.sqrt(results["Mn Ka"]["events"]),tot_events,np.sqrt(tot_events))*100
    p5_yield = results["Mn Kb"]["events"]/tot_events*100
    p5_yield_err = f.std_dev(results["Mn Kb"]["events"],np.sqrt(results["Mn Kb"]["events"]),tot_events,np.sqrt(tot_events))*100

    print("\n INFO YIELDS")
    print(" Peak1:  ",p1_yield,"+-",p1_yield_err)
    print(" Peak3:  ",p3_yield,"+-",p3_yield_err)
    print(" Peak4:  ",p4_yield,"+-",p4_yield_err)
    print(" Peak5:  ",p5_yield,"+-",p5_yield_err)
    print("\n INFO BRANCHING RATIOS")
    print(" Peak4: ",results["Mn Ka"]["events"]/(results["Mn Ka"]["events"]+results["Mn Kb"]["events"])*100,"+-",f.std_dev(results["Mn Ka"]["events"],np.sqrt(results["Mn Ka"]["events"]),results["Mn Ka"]["events"]+results["Mn Kb"]["events"],np.sqrt(results["Mn Ka"]["events"]+results["Mn Kb"]["events"]))*100)
    print(" Peak5: ",results["Mn Kb"]["events"]/(results["Mn Ka"]["events"]+results["Mn Kb"]["events"])*100,"+-",f.std_dev(results["Mn Kb"]["events"],np.sqrt(results["Mn Kb"]["events"]),results["Mn Ka"]["events"]+results["Mn Kb"]["events"],np.sqrt(results["Mn Ka"]["events"]+results["Mn Kb"]["events"]))*100)

    results["Si Ka"]["yield"] = p1_yield
    results["Si Ka"]["err yield"] = p1_yield_err
    results["Si escape"]["yield"] = p3_yield
    results["Si escape"]["err yield"] = p3_yield_err
    results["Mn Ka"]["yield"] = p4_yield
    results["Mn Ka"]["err yield"] = p4_yield_err
    results["Mn Kb"]["yield"] = p5_yield
    results["Mn Kb"]["err yield"] = p5_yield_err


#%% Compute capacity
# https://www.globalsino.com/EM/page3804.html
# https://cxc.harvard.edu/cal/Acis/Cal_prods/matrix/notes/Fl-esc.html
    print("="*150)
    print(r"   [INFO] Doing energy calibration...")
    peaks_value_mV = [results["Si Ka"]["mean"]    , results["Si escape"]["mean"]    , results["Mn Ka"]["mean"]     , results["Mn Kb"]["mean"]]
    peaks_err_mV =   [results["Si Ka"]["err mean"], results["Si escape"]["err mean"], results["Mn Ka"]["err mean"] , results["Mn Kb"]["err mean"]]
    peaks_value_e = [483.0,1156.0,1639.0,1808.0]
    peaks_err_e = [1.0,1.0,1.0,1.0]

    print("Peaks value mV: ",peaks_value_mV)
    print("Peaks error mV: ",peaks_err_mV)
    print("Peaks value e-: ",peaks_value_e)
    print("Peaks error e-: ",peaks_err_e)

    c7 = ROOT.TCanvas('c7', 'c7', 5, 5, 1000, 800)
    c7.cd()
    c7.SetGrid()
    c7.SetLeftMargin(0.12)
    gEnergyCalibration = ROOT.TGraphErrors()
    gEnergyCalibration.SetTitle("Energy calibration")
    gEnergyCalibration.SetMarkerStyle(8)
    gEnergyCalibration.SetMarkerSize(1)
    gEnergyCalibration.GetXaxis().SetTitle("Measured peak mean value (mV)")
    gEnergyCalibration.GetYaxis().SetTitle("Peak mean value from literature (e-)")
    gEnergyCalibration.SetMarkerColor(ROOT.kBlue+2)
    gEnergyCalibration.SetFillColor(ROOT.kBlue+2)
    gEnergyCalibration.SetLineColor(ROOT.kBlue+2)
    gEnergyCalibration.GetXaxis().SetRangeUser(300,2000)

    for i in range(len(peaks_value_mV)):
        print(i, peaks_value_mV[i],peaks_value_e[i], peaks_err_mV[i],peaks_err_e[i])
        gEnergyCalibration.AddPoint(peaks_value_mV[i],peaks_value_e[i])
        gEnergyCalibration.SetPointError(i,peaks_err_mV[i],peaks_err_e[i])

    lin = ROOT.TF1("lin","pol1",350,2000)
    lin.SetParNames("offset","slope")
    lin.SetParameters(-2,1)
    gEnergyCalibration.Fit(lin,"R")
    c7.Update()
    gEnergyCalibration.Draw("AP")
    c7.Update()
    gEnergyCalibration.GetXaxis().SetRangeUser(300,2000)
    c7.Update()
    stat = f.statsPositioned(gEnergyCalibration,0.15,0.5,0.7,0.87)
    stat.Draw()
    c7.Update()
    c7.Print(fname+"_energy_calibration.png")

    results["Calibration"]["slope"] = lin.GetParameter(1)
    results["Calibration"]["err slope"] = lin.GetParError(1)
    results["Calibration"]["offset"] = lin.GetParameter(0)
    results["Calibration"]["err offset"] = lin.GetParError(0)
    results["Calibration"]["chi2"] = lin.GetChisquare()
    results["Calibration"]["NDF"] = lin.GetNDF()
    results["Si Ka"]["e- value"] = peaks_value_e[0]
    results["Si escape"]["e- value"] = peaks_value_e[1]
    results["Mn Ka"]["e- value"] = peaks_value_e[2]
    results["Mn Kb"]["e- value"] = peaks_value_e[3]

    Cap = lin.GetParameter(1) * 160.2 #[aF]
    errCap = lin.GetParError(1) * 160.2 #[aF]
    print("Value of capacitance is: (",Cap,"+-",errCap,") aF")

    with open(fname+"_results.json",'w') as jf:
        json.dump(results,jf,indent=4,allow_nan=True)


#%% RESIDUALS

if __name__=="__main__":
    parser = argparse.ArgumentParser("Source data analysis.",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("file", help=".npz file created by sourceana.py or directory containing such files.")
    parser.add_argument("json", help=".json file with the parameters to be used for the fit of each peak.")
    parser.add_argument('--outdir' , default="./plots", help="Directory with output files")
    args = parser.parse_args()

    if '.npz' in args.file:
        analyse_source(args.file,args.json,args.outdir)
    else:
        if '*' not in args.file: args.file+='*analyzed.npz'
        print("Processing all file matching pattern ", args.file)
        for f in tqdm(glob.glob(args.file),desc="Processing file"):
            analyse_source(args.file,args.json,args.outdir)
            plt.close('all')