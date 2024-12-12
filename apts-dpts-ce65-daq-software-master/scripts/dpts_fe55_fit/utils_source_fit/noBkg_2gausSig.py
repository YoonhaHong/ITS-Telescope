#!/usr/bin/env python3

import ROOT
import numpy as np
from utils_source_fit import common as f

def peak_analysis(npzfile,h,h_res,par,fname,nBIN,dx,resultPeak1,resultPeak2,tot_events):
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
    gaus5 = ROOT.TF1("gaus5","gaus",par['xmin_fit_2'],par['xmax_fit_2'])
    h.Fit(gaus4,"RQ")
    h.Fit(gaus5,"RQ")
    # function for final fit
    peak45 = ROOT.TF1("peak45","gaus(0)+gaus(3)",par['xmin_fit'],par['xmax_fit'])
    peak45.SetParNames("A K#alpha","#mu K#alpha","#sigma K#alpha","A K#beta","#mu K#beta","#sigma K#beta")
    peak45.SetParameter(0,gaus4.GetParameter(0))
    peak45.SetParameter(1,gaus4.GetParameter(1))
    peak45.SetParameter(2,gaus4.GetParameter(2))
    peak45.SetParameter(3,gaus5.GetParameter(0))
    peak45.SetParameter(4,gaus5.GetParameter(1))
    peak45.SetParameter(5,gaus5.GetParameter(2))
    h.Fit(peak45,"R")
    # signal Ka only
    peak4_signal = ROOT.TF1("peak4_signal","gaus",par['xmin'],par['xmax'],3)
    f.TF1Settings(peak4_signal,f.signal_color,2,1)
    peak4_signal.FixParameter(0,peak45.GetParameter(0))
    peak4_signal.FixParameter(1,peak45.GetParameter(1))
    peak4_signal.FixParameter(2,peak45.GetParameter(2))
    # signal Kb only
    peak5_signal = ROOT.TF1("peak5_signal","gaus",par['xmin'],par['xmax'],3)
    f.TF1Settings(peak5_signal,f.signal_color+2,2,1)
    peak5_signal.FixParameter(0,peak45.GetParameter(3))
    peak5_signal.FixParameter(1,peak45.GetParameter(4))
    peak5_signal.FixParameter(2,peak45.GetParameter(5))
    # visualize
    h.Draw("HIST,E,X0")
    peak4_signal.Draw("SAME")
    peak5_signal.Draw("SAME")
    peak45.Draw("SAME")
    pad2.cd().Update()
    stat_p45 = f.statsPositioned(h,0.57,0.95,0.48,0.86)
    stat_p45.Draw("SAME")
    legend_p45 = ROOT.TLegend(0.57,0.31,0.95,0.47)
    legend_p45.AddEntry(peak45," gaus K#alpha + gaus K#beta","l")
    legend_p45.AddEntry(peak4_signal," signal K#alpha","l")
    legend_p45.AddEntry(peak5_signal," signal K#beta","l")
    legend_p45.Draw()
    pad2.cd().Update()
    # RESIDUALS
    f.residuals_signal(h,h_res,peak45,pad3,par['xmin_fit'],par['xmax_fit'],nBIN)

    c4.cd()
    c4.Print(fname)
    p4_events = int(peak4_signal.Integral(0,10000)/dx)
    p5_events = int(peak5_signal.Integral(0,10000)/dx)
    p4_resolution = 100.*2.35*peak45.GetParameter(2)/peak45.GetParameter(1)
    p4_resolution_err = 100.*f.std_dev(2.35*peak45.GetParameter(2),2.35*peak45.GetParError(2),peak45.GetParameter(1),peak45.GetParError(1))
    p5_resolution = 100.*2.35*peak45.GetParameter(5)/peak45.GetParameter(4)
    p5_resolution_err = 100.*f.std_dev(2.35*peak45.GetParameter(5),2.35*peak45.GetParError(5),peak45.GetParameter(4),peak45.GetParError(4))
    print("  INFO PEAK 4:")
    print(" Events:     ",p4_events,"+-",np.sqrt(p4_events))
    print(" FWHM:       ",2.35*peak45.GetParameter(2),"+-",2.35*peak45.GetParError(2))
    print(" Resolution: ",p4_resolution,"+-",p4_resolution_err)
    tot_events += p4_events
    print("  INFO PEAK 5:")
    print(" Events:     ",p5_events,"+-",np.sqrt(p5_events))
    print(" FWHM:       ",2.35*peak45.GetParameter(5),"+-",2.35*peak45.GetParError(5))
    print(" Resolution: ",p5_resolution,"+-",p5_resolution_err)
    tot_events += p5_events

    resultPeak1["events"] = p4_events
    resultPeak1["p0"] = peak45.GetParameter(0)
    resultPeak1["mean"] = peak45.GetParameter(1)
    resultPeak1["err mean"] = peak45.GetParError(1)
    resultPeak1["sigma"] = peak45.GetParameter(2)
    resultPeak1["err sigma"] = peak45.GetParError(2)
    resultPeak1["resolution"] = p4_resolution
    resultPeak1["err resolution"] = p4_resolution_err
    resultPeak2["events"] = p5_events
    resultPeak2["p3"] = peak45.GetParameter(3)
    resultPeak2["mean"] = peak45.GetParameter(4)
    resultPeak2["err mean"] = peak45.GetParError(4)
    resultPeak2["sigma"] = peak45.GetParameter(5)
    resultPeak2["err sigma"] = peak45.GetParError(5)
    resultPeak2["resolution"] = p5_resolution
    resultPeak2["err resolution"] = p5_resolution_err

    return resultPeak1, resultPeak2, tot_events