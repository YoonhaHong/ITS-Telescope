#!/usr/bin/env python3

import ROOT
import numpy as np
from utils_source_fit import common as f

def BKG_linear(x, p):
    if (x[0]<p[2] and x[0]>p[3]):
        ROOT.TF1.RejectPoint()
        return 0
    return p[0] + p[1]*x[0]

def peak_analysis(npzfile,h,h_res,hBkg,hBkg_res,par,fname,nBIN,dx,results,tot_events):
    f.histoSettings(h_res,'',"Fractional difference",0.07,0.07,0.6,"Calibrated ToT (mV)",0.07,0.07,0.0)
    f.histoSettings(hBkg_res,'',"Fractional difference",0.07,0.07,0.6,"Calibrated ToT (mV)",0.07,0.07,0.0)
    h.GetXaxis().SetTitle("Calibrated ToT (mV)")
    h_res.GetXaxis().SetTitle("Calibrated ToT (mV)")
    hBkg.GetXaxis().SetTitle("Calibrated ToT (mV)")
    hBkg_res.GetXaxis().SetTitle("Calibrated ToT (mV)")
    print("="*150)
    print("   [INFO] Processing " + par['name'] + " peak...")
    canvas = ROOT.TCanvas('canvas', 'canvas', 5, 5, 1300, 800)
    canvas,pad1,pad2,pad3,pad4,pad5 = f.padBackgroundAndSignal(canvas)
    f.printTitle(pad1,"Background and signal fit for " + par['name'] + " peak",npzfile)
    pad2.cd()
    h.GetXaxis().SetRangeUser(par['xmin'],par['xmax'])
    h.GetYaxis().SetRangeUser(par['ymin'],par['ymax'])
    h_res.GetXaxis().SetRangeUser(par['xmin'],par['xmax'])
    hBkg.GetXaxis().SetRangeUser(par['xmin'],par['xmax'])
    hBkg.GetYaxis().SetRangeUser(par['ymin'],par['ymax'])
    hBkg_res.GetXaxis().SetRangeUser(par['xmin'],par['xmax'])
    # define function for linear background
    lin_bkg_p = ROOT.TF1("lin_bkg_p",BKG_linear,par['xmin_fit'],par['xmax_fit'],4)
    lin_bkg_p.SetParNames("p_{0}","p_{1}")
    lin_bkg_p.SetParameter(0,3500)
    lin_bkg_p.SetParameter(1,3)
    lin_bkg_p.FixParameter(2,par['xcut_max'])
    lin_bkg_p.FixParameter(3,par['xcut_min'])
    hBkg.Fit(lin_bkg_p,"RQ")
    # define function for visualization
    lin_bkg_rejected = ROOT.TF1("lin_bkg_fin","pol1",par['xcut_min'],par['xcut_max'],2)
    f.TF1Settings(lin_bkg_rejected,f.bkg_color,2,3)
    lin_bkg_rejected.SetParameters(lin_bkg_p.GetParameters())
    lin_bkg_L = ROOT.TF1("lin_bkg_L","pol1",par['xmin_fit'],par['xcut_min'],2)
    f.TF1Settings(lin_bkg_L,f.bkg_color,2,1)
    lin_bkg_L.SetParameters(lin_bkg_p.GetParameters())
    lin_bkg_R = ROOT.TF1("lin_bkg_R","pol1",par['xcut_max'],par['xmax_fit'],2)
    f.TF1Settings(lin_bkg_R,f.bkg_color,2,1)
    lin_bkg_R.SetParameters(lin_bkg_p.GetParameters())
    # BACKGROUND visualization
    hBkg.Draw("HIST,E,X0")
    lin_bkg_rejected.Draw("SAME")
    lin_bkg_L.Draw("SAME")
    lin_bkg_R.Draw("SAME")
    pad2.cd().Update()
    stat_p11 = f.statsPositioned(hBkg,0.55,0.95,0.62,0.86)
    stat_p11.Draw("SAME")
    legend_p11 = ROOT.TLegend(0.55,0.52,0.95,0.61)
    legend_p11.AddEntry(lin_bkg_L," lin bkg","l")
    legend_p11.AddEntry(lin_bkg_rejected," excluded bkg","l")
    legend_p11.Draw()
    pad2.cd().Update()
    # define function for preliminary fit
    pad4.cd()
    gaus = ROOT.TF1("gaus","gaus",par['xcut_min'],par['xcut_max'])
    h.Fit(gaus,"RQ")
    # final fit lin + gaus
    peak = ROOT.TF1("peak","pol1(0)+gaus(2)",par['xmin_fit'],par['xmax_fit'],5)
    peak.SetParNames("p_{0}","p_{1}","A","#mu","#sigma")
    peak.FixParameter(0,lin_bkg_p.GetParameter(0))
    peak.FixParameter(1,lin_bkg_p.GetParameter(1))
    peak.SetParameter(2,gaus.GetParameter(0))
    peak.SetParameter(3,gaus.GetParameter(1))
    peak.SetParameter(4,gaus.GetParameter(2))
    peak.SetParLimits(4,10,gaus.GetParameter(2))
    h.Fit(peak,"R")
    # signal only
    peak_signal = ROOT.TF1("peak_signal","gaus",par['xmin'],par['xmax'],3)
    f.TF1Settings(peak_signal,f.signal_color,2,1)
    peak_signal.FixParameter(0,peak.GetParameter(2))
    peak_signal.FixParameter(1,peak.GetParameter(3))
    peak_signal.FixParameter(2,peak.GetParameter(4))
    # visualize
    h.Draw("HIST,E,X0")
    peak.Draw("SAME")
    peak_signal.Draw("SAME")
    pad4.cd().Update()
    stat_p12 = f.statsPositioned(h,0.55,0.95,0.62,0.86)
    stat_p12.Draw("SAME")
    legend_p12 = ROOT.TLegend(0.55,0.52,0.95,0.61)
    legend_p12.AddEntry(peak," bkg + gaus","l")
    legend_p12.AddEntry(peak_signal," signal","l")
    legend_p12.Draw()
    pad4.cd().Update()
    # RESIDUALS
    f.residuals_background(hBkg,hBkg_res,lin_bkg_p,pad3,par['xmin_fit'],par['xcut_min'],par['xcut_max'],par['xmax_fit'],nBIN)
    f.residuals_signal(h,h_res,peak,pad5,par['xmin_fit'],par['xmax_fit'],nBIN)

    canvas.cd()
    canvas.Print(fname)
    events = int(peak_signal.Integral(0,10000)/dx)
    resolution = 100.*2.35*peak.GetParameter(4)/peak.GetParameter(3)
    resolution_err = 100.*f.std_dev(2.35*peak.GetParameter(4),2.35*peak.GetParError(4),peak.GetParameter(3),peak.GetParError(3))
    print("  INFO PEAK :")
    print(" Events:     ",events,"+-",np.sqrt(events))
    print(" FWHM:       ",2.35*peak.GetParameter(4),"+-",2.35*peak.GetParError(4))
    print(" Resolution: ",resolution,"+-",resolution_err)
    tot_events += events

    results["events"] = events
    results["p0"] = peak.GetParameter(0)
    results["p1"] = peak.GetParameter(1)
    results["p2"] = peak.GetParameter(2)
    results["mean"] = peak.GetParameter(3)
    results["err mean"] = peak.GetParError(3)
    results["sigma"] = peak.GetParameter(4)
    results["err sigma"] = peak.GetParError(4)
    results["resolution"] = resolution
    results["err resolution"] = resolution_err

    return results, tot_events