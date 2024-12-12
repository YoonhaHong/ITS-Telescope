#!/usr/bin/env python3

import ROOT
import numpy as np
import math
from utils_source_fit import common as f

def BKG_p1(x, p):
    if x[0] > p[3] and x[0] < p[4]:
        ROOT.TF1.RejectPoint()
        return 0
    return p[0] + p[1]*math.exp(-x[0]/p[2])

def EXP_BKG_p1(x, p):
    return p[0] + p[1]*math.exp(-x[0]/p[2])

def PEAK_1(x, p):
    return p[0] + p[1]*math.exp(-x[0]/p[2]) + p[3]*math.exp(-0.5*((x[0]-p[4])/p[5])*((x[0]-p[4])/p[5]))

#%% 1. Si FLUORESCENCE PEAK
def peak_analysis(npzfile,h,h_res,hBkg,hBkg_res,par,fname,nBIN,dx,results,tot_events):
    f.histoSettings(h_res,'',"Fractional difference",0.07,0.07,0.6,"Calibrated ToT (mV)",0.07,0.07,0.0)
    f.histoSettings(hBkg_res,'',"Fractional difference",0.07,0.07,0.6,"Calibrated ToT (mV)",0.07,0.07,0.0)
    hBkg.GetXaxis().SetTitle("Calibrated ToT (mV)")
    hBkg_res.GetXaxis().SetTitle("Calibrated ToT (mV)")
    h_res.GetXaxis().SetTitle("Calibrated ToT (mV)")
    print("="*150)
    print("   [INFO] Processing " + par['name'] + " fluorescence peak...")
    c1 = ROOT.TCanvas('c1', 'c1', 5, 5, 1300, 800)
    c1,pad1,pad2,pad3,pad4,pad5 = f.padBackgroundAndSignal(c1)
    f.printTitle(pad1,"Background and signal fit for " + par['name'] + " fuorescence peak",npzfile)
    pad2.cd()
    # exponential background fit
    h.GetXaxis().SetRangeUser(par['xmin'],par['xmax'])
    h_res.GetXaxis().SetRangeUser(par['xmin'],par['xmax'])
    h.GetYaxis().SetRangeUser(par['ymin'],par['ymax'])
    hBkg.GetXaxis().SetRangeUser(par['xmin'],par['xmax'])
    hBkg_res.GetXaxis().SetRangeUser(par['xmin'],par['xmax'])
    hBkg.GetYaxis().SetRangeUser(par['ymin'],par['ymax'])
    exp_bkg = ROOT.TF1("exp_bkg",BKG_p1,par['xmin_fit'],par['xmax_fit'],5)
    exp_bkg.SetParNames("p_{0}","p_{1}","p_{2}")
    f.TF1Settings(exp_bkg,ROOT.kGreen,4,9)
    exp_bkg.SetParameter(0,4107.12917745)
    exp_bkg.SetParameter(1,46539.97337957)
    exp_bkg.SetParameter(2,152.11505957)
    exp_bkg.FixParameter(3,par['xcut_min'])
    exp_bkg.FixParameter(4,par['xcut_max'])
    hBkg.Fit(exp_bkg,"RQ")
    # define function for visualization
    exp_bkg_rejected = ROOT.TF1("exp_bkg_fin",EXP_BKG_p1,par['xcut_min'],par['xcut_max'],3)
    f.TF1Settings(exp_bkg_rejected,f.bkg_color,2,3)
    exp_bkg_rejected.SetParameters(exp_bkg.GetParameters())
    exp_bkg_L = ROOT.TF1("exp_bkg_L",EXP_BKG_p1,par['xmin_fit'],par['xcut_min'],3)
    f.TF1Settings(exp_bkg_L,f.bkg_color,2,1)
    exp_bkg_L.SetParameters(exp_bkg.GetParameters())
    exp_bkg_R = ROOT.TF1("exp_bkg_R",EXP_BKG_p1,par['xcut_max'],par['xmax_fit'],3)
    f.TF1Settings(exp_bkg_R,f.bkg_color,2,1)
    exp_bkg_R.SetParameters(exp_bkg.GetParameters())
    # BACKGROUND visualization
    hBkg.Draw("HIST,E,X0")
    exp_bkg_rejected.Draw("SAME")
    exp_bkg_L.Draw("SAME")
    exp_bkg_R.Draw("SAME")
    pad2.Update()
    stat_p11 = f.statsPositioned(hBkg,0.55,0.95,0.62,0.86)
    stat_p11.Draw("SAME")
    legend_p11 = ROOT.TLegend(0.55,0.52,0.95,0.61)
    legend_p11.AddEntry(exp_bkg_L," exp bkg","l")
    legend_p11.AddEntry(exp_bkg_rejected," excluded bkg","l")
    legend_p11.Draw()
    pad2.Update()
    # exp + gaus final fit
    pad4.cd()
    peak1 = ROOT.TF1("peak1",PEAK_1,par['xmin_fit'],par['xmax_fit'],6)
    f.TF1Settings(peak1,f.fit_color,2,1)
    peak1.SetParNames("","","","A","#mu","#sigma")
    peak1.FixParameter(0,exp_bkg.GetParameter(0))
    peak1.FixParameter(1,exp_bkg.GetParameter(1))
    peak1.FixParameter(2,exp_bkg.GetParameter(2))
    peak1.SetParameter(3,100)
    peak1.SetParameter(4,400)
    peak1.SetParameter(5,25)
    h.Fit(peak1,"R")
    # signal only
    peak1_signal = ROOT.TF1("peak1_signal","gaus",par['xmin_fit'],par['xmax_fit'],3)
    f.TF1Settings(peak1_signal,f.signal_color,2,1)
    peak1_signal.FixParameter(0,peak1.GetParameter(3))
    peak1_signal.FixParameter(1,peak1.GetParameter(4))
    peak1_signal.FixParameter(2,peak1.GetParameter(5))
    # visualize
    h.Draw("HIST,E,X0")
    peak1.Draw("SAME")
    peak1_signal.Draw("SAME")
    pad4.Update()
    stat_p12 = f.statsPositioned(h,0.55,0.95,0.62,0.86)
    stat_p12.Draw("SAME")
    legend_p12 = ROOT.TLegend(0.55,0.52,0.95,0.61)
    legend_p12.AddEntry(peak1," bkg + gaus","l")
    legend_p12.AddEntry(peak1_signal," signal","l")
    legend_p12.Draw()
    pad4.Update()
    # RESIDUALS
    f.residuals_background(hBkg,hBkg_res,exp_bkg,pad3,par['xmin_fit'],par['xcut_min'],par['xcut_max'],par['xmax_fit'],nBIN)
    f.residuals_signal(h,h_res,peak1,pad5,par['xmin_fit'],par['xmax_fit'],nBIN)

    c1.cd()
    c1.Print(fname)

    p1_events = int(peak1_signal.Integral(0,10000)/dx)
    p1_resolution = 100.*2.35*peak1.GetParameter(5)/peak1.GetParameter(4)
    p1_resolution_err = 100.*f.std_dev(2.35*peak1.GetParameter(5),2.35*peak1.GetParError(5),peak1.GetParameter(4),peak1.GetParError(4))
    print("  INFO PEAK 1:")
    print(" Events:     ",p1_events,"+-",np.sqrt(p1_events))
    print(" FWHM:       ",2.35*peak1.GetParameter(5),"+-",2.35*peak1.GetParError(5))
    print(" Resolution: ",p1_resolution,"+-",p1_resolution_err)
    tot_events += p1_events

    results["Si Ka"]["events"] = p1_events
    results["Si Ka"]["p0"] = peak1.GetParameter(0)
    results["Si Ka"]["p1"] = peak1.GetParameter(1)
    results["Si Ka"]["p2"] = peak1.GetParameter(2)
    results["Si Ka"]["p3"] = peak1.GetParameter(3)
    results["Si Ka"]["mean"] = peak1.GetParameter(4)
    results["Si Ka"]["err mean"] = peak1.GetParError(4)
    results["Si Ka"]["sigma"] = peak1.GetParameter(5)
    results["Si Ka"]["err sigma"] = peak1.GetParError(5)
    results["Si Ka"]["resolution"] = p1_resolution
    results["Si Ka"]["err resolution"] = p1_resolution_err

    return results, tot_events