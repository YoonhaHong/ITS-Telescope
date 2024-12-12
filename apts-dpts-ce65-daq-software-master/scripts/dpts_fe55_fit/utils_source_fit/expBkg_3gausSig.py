#!/usr/bin/env python3

import ROOT
import numpy as np
import math
from utils_source_fit import common as f

def BKG_p1(x, p):
    if x[0] > p[4] and x[0] < p[5]:
        ROOT.TF1.RejectPoint()
        return 0
    return p[0] + p[1]*math.exp(-(x[0]+p[3])/p[2])

def EXP_BKG_p1(x, p):
    return p[0] + p[1]*math.exp(-(x[0]+p[3])/p[2])

def PEAK_1(x, p):
    return p[0] + p[1]*math.exp(-(x[0]+p[3])/p[2]) + p[4]*math.exp(-0.5*((x[0]-p[5])/p[6])*((x[0]-p[5])/p[6])) + p[7]*math.exp(-0.5*((x[0]-p[8])/p[9])*((x[0]-p[8])/p[9])) + p[10]*math.exp(-0.5*((x[0]-p[11])/p[12])*((x[0]-p[11])/p[12]))

#%% 1. Si FLUORESCENCE PEAK
def peak_analysis(npzfile,hSi,hSi_res,hSiBkg,hSiBkg_res,par,fname,nBIN,dx,results1,results2,tot_events,xmin_statBox=0.55,xmax_statBox=0.95):
    f.histoSettings(hSi_res,'',"Fractional difference",0.07,0.07,0.6,"Calibrated ToT (mV)",0.07,0.07,0.0)
    f.histoSettings(hSiBkg_res,'',"Fractional difference",0.07,0.07,0.6,"Calibrated ToT (mV)",0.07,0.07,0.0)
    hSiBkg.GetXaxis().SetTitle("Calibrated ToT (mV)")
    hSiBkg_res.GetXaxis().SetTitle("Calibrated ToT (mV)")
    hSi_res.GetXaxis().SetTitle("Calibrated ToT (mV)")
    print("="*150)
    print("   [INFO] Processing " + par['name 1'] + ", " + par['name 2'] + " peak...")
    c1 = ROOT.TCanvas('c1', 'c1', 5, 5, 1300, 800)
    c1,pad1,pad2,pad3,pad4,pad5 = f.padBackgroundAndSignal(c1)
    f.printTitle(pad1,"Background and signal fit for " + par['name 1'] + ", " + par['name 2'] + " peaks",npzfile)
    pad2.cd()
    # exponential background fit
    hSi.GetXaxis().SetRangeUser(par['xmin'],par['xmax'])
    hSi_res.GetXaxis().SetRangeUser(par['xmin'],par['xmax'])
    hSi.GetYaxis().SetRangeUser(par['ymin'],par['ymax'])
    hSiBkg.GetXaxis().SetRangeUser(par['xmin'],par['xmax'])
    hSiBkg_res.GetXaxis().SetRangeUser(par['xmin'],par['xmax'])
    hSiBkg.GetYaxis().SetRangeUser(par['ymin'],par['ymax'])
    exp_bkg = ROOT.TF1("exp_bkg",BKG_p1,par['xmin_fit'],par['xmax_fit'],6)
    exp_bkg.SetParNames("p_{0}","p_{1}","p_{2}","p_{3}")
    f.TF1Settings(exp_bkg,ROOT.kGreen,4,9)
    exp_bkg.SetParameter(0,10.0)
    exp_bkg.SetParameter(1,2373.0)
    exp_bkg.SetParameter(2,1842.0)
    exp_bkg.SetParameter(3,17.0)
    exp_bkg.FixParameter(4,par['xcut_min'])
    exp_bkg.FixParameter(5,par['xcut_max'])
    hSiBkg.Fit(exp_bkg,"RQ")
    # define function for visualization
    exp_bkg_rejected = ROOT.TF1("exp_bkg_fin",EXP_BKG_p1,par['xcut_min'],par['xcut_max'],4)
    f.TF1Settings(exp_bkg_rejected,ROOT.kAzure+10,2,1)
    exp_bkg_rejected.SetParameters(exp_bkg.GetParameters())
    exp_bkg_L = ROOT.TF1("exp_bkg_L",EXP_BKG_p1,par['xmin_fit'],par['xcut_min'],4)
    f.TF1Settings(exp_bkg_L,f.bkg_color,2,1)
    exp_bkg_L.SetParameters(exp_bkg.GetParameters())
    exp_bkg_R = ROOT.TF1("exp_bkg_R",EXP_BKG_p1,par['xcut_max'],par['xmax_fit'],4)
    f.TF1Settings(exp_bkg_R,f.bkg_color,2,1)
    exp_bkg_R.SetParameters(exp_bkg.GetParameters())
    # BACKGROUND visualization
    hSiBkg.Draw("HIST,E,X0")
    exp_bkg_rejected.Draw("SAME")
    exp_bkg_L.Draw("SAME")
    exp_bkg_R.Draw("SAME")
    pad2.Update()
    stat_p11 = f.statsPositioned(hSiBkg,xmin_statBox,xmax_statBox,0.62,0.86)
    stat_p11.Draw("SAME")
    legend_p11 = ROOT.TLegend(xmin_statBox,0.52,xmax_statBox,0.61)
    legend_p11.AddEntry(exp_bkg_L," exp bkg","l")
    legend_p11.AddEntry(exp_bkg_rejected," excluded bkg","l")
    legend_p11.Draw()
    pad2.Update()
    # exp + gaus final fit
    pad4.cd()
    # define functions for preliminary fit
    gaus1_p = ROOT.TF1("gaus1_p","gaus",par['xmin_fit_1'],par['xmax_fit_1'])
    gaus2_p = ROOT.TF1("gaus2_p","gaus",par['xmin_fit_2'],par['xmax_fit_2'])
    gaus3_p = ROOT.TF1("gaus3_p","gaus",par['xmin_fit_3'],par['xmax_fit_3'])
    hSi.Fit(gaus1_p,"RQ")
    hSi.Fit(gaus2_p,"RQ")
    hSi.Fit(gaus3_p,"RQ")
    peak1 = ROOT.TF1("peak1",PEAK_1,par['xmin_fit'],par['xmax_fit'],13)
    f.TF1Settings(peak1,f.fit_color,2,1)
    peak1.SetParNames("","","","","peak 1 A","peak 1 #mu","peak 1 #sigma",par['name 1']+" A",par['name 1']+" #mu",par['name 1']+" #sigma",par['name 2']+" A")
    peak1.SetParName(11,par['name 2']+" #mu")
    peak1.SetParName(12,par['name 2']+" #sigma")
    peak1.FixParameter(0,exp_bkg.GetParameter(0))
    peak1.FixParameter(1,exp_bkg.GetParameter(1))
    peak1.FixParameter(2,exp_bkg.GetParameter(2))
    peak1.FixParameter(3,exp_bkg.GetParameter(3))
    peak1.SetParameter(4,gaus1_p.GetParameter(0))
    peak1.SetParameter(5,gaus1_p.GetParameter(1))
    peak1.SetParameter(6,gaus1_p.GetParameter(2))
    peak1.SetParameter(7,gaus2_p.GetParameter(0))
    peak1.SetParameter(8,gaus2_p.GetParameter(1))
    peak1.SetParameter(9,gaus2_p.GetParameter(2))
    peak1.SetParameter(10,gaus3_p.GetParameter(0))
    peak1.SetParameter(11,gaus3_p.GetParameter(1))
    peak1.SetParameter(12,gaus3_p.GetParameter(2))
    # set limits for paramenter values
    peak1.SetParLimits(5,par['xmin_fit_1'],par['xmax_fit_1'])
    peak1.SetParLimits(8,par['xmin_fit_2'],par['xmax_fit_2'])
    hSi.Fit(peak1,"R")
    # signal only
    peak1_signal = ROOT.TF1("peak1_signal","gaus",par['xmin'],par['xmax'],3)
    f.TF1Settings(peak1_signal,f.signal_color,2,1)
    peak1_signal.FixParameter(0,peak1.GetParameter(4))
    peak1_signal.FixParameter(1,peak1.GetParameter(5))
    peak1_signal.FixParameter(2,peak1.GetParameter(6))
    peak2_signal = ROOT.TF1("peak3_signal","gaus",par['xmin'],par['xmax'],3)
    f.TF1Settings(peak2_signal,f.signal_color+2,2,1)
    peak2_signal.FixParameter(0,peak1.GetParameter(7))
    peak2_signal.FixParameter(1,peak1.GetParameter(8))
    peak2_signal.FixParameter(2,peak1.GetParameter(9))
    peak3_signal = ROOT.TF1("peak3_signal","gaus",par['xmin'],par['xmax'],3)
    f.TF1Settings(peak3_signal,f.signal_color+3,2,1)
    peak3_signal.FixParameter(0,peak1.GetParameter(10))
    peak3_signal.FixParameter(1,peak1.GetParameter(11))
    peak3_signal.FixParameter(2,peak1.GetParameter(12))
    # visualize
    hSi.Draw("HIST,E,X0")
    peak1.Draw("SAME")
    peak1_signal.Draw("SAME")
    peak2_signal.Draw("SAME")
    peak3_signal.Draw("SAME")
    pad4.Update()
    stat_p12 = f.statsPositioned(hSi,xmin_statBox,xmax_statBox,0.42,0.86)
    stat_p12.Draw("SAME")
    legend_p12 = ROOT.TLegend(xmin_statBox,0.22,xmax_statBox,0.41)
    legend_p12.AddEntry(peak1," bkg + gaus","l")
    legend_p12.AddEntry(peak1_signal," signal peak 1","l")
    legend_p12.AddEntry(peak2_signal," signal "+par['name 1'],"l")
    legend_p12.AddEntry(peak3_signal," signal "+par['name 2'],"l")
    legend_p12.Draw()
    pad4.Update()
    # RESIDUALS
    f.residuals_background(hSiBkg,hSiBkg_res,exp_bkg,pad3,par['xmin_fit'],par['xcut_min'],par['xcut_max'],par['xmax_fit'],nBIN)
    f.residuals_signal(hSi,hSi_res,peak1,pad5,par['xmin_fit'],par['xmax_fit'],nBIN)
    
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

    results1["events"] = p1_events
    results1["p0"] = peak1.GetParameter(0)
    results1["p1"] = peak1.GetParameter(1)
    results1["p2"] = peak1.GetParameter(2)
    results1["p3"] = peak1.GetParameter(3)
    results1["mean"] = peak1.GetParameter(8)
    results2["mean"] = peak1.GetParameter(11)
    results2["err mean"] = peak1.GetParError(11)
    results1["err mean"] = peak1.GetParError(8)
    results1["sigma"] = peak1.GetParameter(5)
    results1["err sigma"] = peak1.GetParError(5)
    results1["resolution"] = p1_resolution
    results1["err resolution"] = p1_resolution_err

    return results1, results2, tot_events