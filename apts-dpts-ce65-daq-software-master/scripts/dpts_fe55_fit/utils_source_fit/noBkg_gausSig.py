#!/usr/bin/env python3

import ROOT
import numpy as np
from utils_source_fit import common as f

def peak_analysis(npzfile,h,h_res,par,fname,nBIN,dx,resultPeak1,tot_events):
    f.histoSettings(h_res,'',"Fractional difference",0.07,0.07,0.6,"Calibrated ToT (mV)",0.07,0.07,0.0)
    h.GetXaxis().SetTitle("Calibrated ToT (mV)")
    h_res.GetXaxis().SetTitle("Calibrated ToT (mV)")
    print("="*150)
    print("   [INFO] Processing "+ par['name'] +" peak...")
    c4 = ROOT.TCanvas('c4', 'c4', 5, 5, 750, 800)
    c4,pad1,pad2,pad3 = f.padSignalOnly(c4)
    f.printTitle(pad1,"Signal fit for " + par['name'],npzfile)
    pad2.cd()
    h.GetXaxis().SetRangeUser(par['xmin'],par['xmax'])
    h.GetYaxis().SetRangeUser(par['ymin'],par['ymax'])
    h_res.GetXaxis().SetRangeUser(par['xmin'],par['xmax'])
    # define functions for preliminary fit
    gaus4 = ROOT.TF1("gaus4","gaus",par['xmin_fit_1'],par['xmax_fit_1'])
    h.Fit(gaus4,"RQ")
    # function for final fit
    peak = ROOT.TF1("peak","gaus",par['xmin_fit'],par['xmax_fit'])
    peak.SetParNames("A K#alpha","#mu K#alpha","#sigma K#alpha","A K#beta","#mu K#beta","#sigma K#beta")
    peak.SetParameter(0,gaus4.GetParameter(0))
    peak.SetParameter(1,gaus4.GetParameter(1))
    peak.SetParameter(2,gaus4.GetParameter(2))
    h.Fit(peak,"R")
    # signal Ka only
    signal = ROOT.TF1("signal","gaus",par['xmin'],par['xmax'],3)
    f.TF1Settings(signal,f.signal_color,2,1)
    signal.FixParameter(0,peak.GetParameter(0))
    signal.FixParameter(1,peak.GetParameter(1))
    signal.FixParameter(2,peak.GetParameter(2))
    # visualize
    h.Draw("HIST,E,X0")
    signal.Draw("SAME")
    peak.Draw("SAME")
    pad2.cd().Update()
    stat = f.statsPositioned(h,0.57,0.95,0.48,0.86)
    stat.Draw("SAME")
    legend = ROOT.TLegend(0.57,0.31,0.95,0.47)
    legend.AddEntry(peak," gaus K#alpha + gaus K#beta","l")
    legend.AddEntry(signal," signal K#alpha","l")
    legend.Draw()
    pad2.cd().Update()
    # RESIDUALS
    f.residuals_signal(h,h_res,peak,pad3,par['xmin_fit'],par['xmax_fit'],nBIN)

    c4.cd()
    c4.Print(fname)
    p4_events = int(signal.Integral(0,10000)/dx)
    p4_resolution = 100.*2.35*peak.GetParameter(2)/peak.GetParameter(1)
    p4_resolution_err = 100.*f.std_dev(2.35*peak.GetParameter(2),2.35*peak.GetParError(2),peak.GetParameter(1),peak.GetParError(1))
    print("  INFO PEAK 4:")
    print(" Events:     ",p4_events,"+-",np.sqrt(p4_events))
    print(" FWHM:       ",2.35*peak.GetParameter(2),"+-",2.35*peak.GetParError(2))
    print(" Resolution: ",p4_resolution,"+-",p4_resolution_err)
    tot_events += p4_events

    resultPeak1["events"] = p4_events
    resultPeak1["p0"] = peak.GetParameter(0)
    resultPeak1["mean"] = peak.GetParameter(1)
    resultPeak1["err mean"] = peak.GetParError(1)
    resultPeak1["sigma"] = peak.GetParameter(2)
    resultPeak1["err sigma"] = peak.GetParError(2)
    resultPeak1["resolution"] = p4_resolution
    resultPeak1["err resolution"] = p4_resolution_err

    return resultPeak1, tot_events