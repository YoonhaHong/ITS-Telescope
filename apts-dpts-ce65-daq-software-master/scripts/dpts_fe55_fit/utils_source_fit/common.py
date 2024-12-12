#!/usr/bin/env python3

import ROOT
ROOT.gROOT.SetBatch(True)
import numpy as np
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# colors
bkg_color = ROOT.kBlue-4
fit_color = ROOT.kRed
signal_color = ROOT.kGreen+1
histo_color = ROOT.kBlack

# gStyle options
ROOT.gStyle.SetOptStat(0)
ROOT.gStyle.SetOptFit(1)
ROOT.gStyle.SetHistLineColor(histo_color)
ROOT.gStyle.SetPadRightMargin(0.04)
ROOT.gStyle.SetPadLeftMargin(0.085)
ROOT.gStyle.SetPadTopMargin(0.10)
ROOT.gStyle.SetPadBottomMargin(0.10)
ROOT.gStyle.SetFitFormat("5.1f")
ROOT.gStyle.SetStatFontSize(0.1)
ROOT.gStyle.SetPadTickX(1)

def std_dev(mu1, sigma1, mu2, sigma2):
    return np.sqrt(1/mu2**2*sigma1**2+mu1**2/mu2**4*sigma2**2)

def histoSettings(histo,title,YTitle,YTitleSize,YLabelSize,YTitleOff,XTitle,XTitleSize,XLabelSize,XTitleOff):
    histo.SetTitle(title)
    histo.GetYaxis().SetTitle(YTitle)
    histo.GetYaxis().SetTitleSize(YTitleSize)
    histo.GetYaxis().SetLabelSize(YLabelSize)
    histo.GetYaxis().SetTitleOffset(YTitleOff)
    histo.GetXaxis().SetTitle(XTitle)
    histo.GetXaxis().SetTitleSize(XTitleSize)
    histo.GetXaxis().SetLabelSize(XLabelSize)
    histo.GetXaxis().SetTitleOffset(XTitleOff)
    histo.SetMarkerStyle(8)
    histo.SetMarkerSize(0.3)

def TF1Settings(TF1,color,width,style):
    TF1.SetLineColor(color)
    TF1.SetLineWidth(width)
    TF1.SetLineStyle(style)

def statsPositioned(histo,xStart,xEnd,yStart,yEnd):
    stat = histo.FindObject("stats")
    stat.SetX1NDC(xStart)# new x start position
    stat.SetX2NDC(xEnd)# new x end position
    stat.SetY1NDC(yStart)# new y start position
    stat.SetY2NDC(yEnd)# new y end position
    #stat.SetFillStyle(0) # TRANSPARENT
    return stat

def printTitle(pad1,string_title,npzfile):
    title = ROOT.TLatex()
    pad1.cd()
    title.SetTextSize(0.45)
    title.DrawLatex(.05,.40,string_title)
    titleFile = ROOT.TLatex()
    titleFile.SetTextSize(0.25)
    titleFile.DrawLatex(.05,.15,os.path.basename(npzfile))

def padBackgroundAndSignal(canvas):
    canvas.Divide(2)
    pad1 = ROOT.TPad("pad1","This is pad1",0.001,0.90,0.999,0.999)
    canvas.cd()
    pad1.Draw()
    pad2 = ROOT.TPad("pad2","This is pad2",0.001,0.30,0.999,0.90)
    pad3 = ROOT.TPad("pad3","This is pad3",0.001,0.001,0.999,0.30)
    canvas.cd(1)
    pad2.Draw()
    pad3.Draw()
    pad2.SetBottomMargin(0)
    pad2.SetBorderMode(0)
    pad3.SetTopMargin(0)
    pad3.SetBottomMargin(0.2)
    pad3.SetBorderMode(0)
    pad4 = ROOT.TPad("pad4","This is pad4",0.001,0.30,0.999,0.90)
    pad5 = ROOT.TPad("pad5","This is pad5",0.001,0.001,0.999,0.30)
    canvas.cd(2)
    pad4.Draw()
    pad5.Draw()
    pad4.SetBottomMargin(0)
    pad4.SetBorderMode(0)
    pad5.SetTopMargin(0)
    pad5.SetBottomMargin(0.2)
    pad5.SetBorderMode(0)
    return canvas,pad1,pad2,pad3,pad4,pad5

def padSignalOnly(canvas):
    pad1 = ROOT.TPad("pad1","This is pad1",0.001,0.90,0.999,0.999)
    canvas.cd()
    pad1.Draw()
    pad2 = ROOT.TPad("pad2","This is pad2",0.001,0.30,0.999,0.90)
    pad3 = ROOT.TPad("pad3","This is pad3",0.001,0.001,0.999,0.30)
    canvas.cd(1)
    pad2.Draw()
    pad3.Draw()
    pad2.SetBottomMargin(0)
    pad2.SetBorderMode(0)
    pad3.SetTopMargin(0)
    pad3.SetBottomMargin(0.2)
    pad3.SetBorderMode(0)
    return canvas,pad1,pad2,pad3

def residuals_signal(histo,histo_res,function,canvas,minX,maxX,nBIN):
    histo_res.GetYaxis().SetRangeUser(0.81,1.19)
    for i in range(nBIN):
        if (histo.GetBinCenter(i)>minX and histo.GetBinCenter(i)<maxX):
            diff = histo.GetBinContent(i)/function.Eval(histo.GetBinCenter(i))
            err = histo.GetBinError(i)/function.Eval(histo.GetBinCenter(i))
            histo_res.SetBinContent(i,diff)
            histo_res.SetBinError(i,err)
    ref_line = ROOT.TF1("ref_line","pol0",0,20000,1)
    TF1Settings(ref_line,ROOT.kGray+2,1,3)
    ref_line.FixParameter(0,1)
    canvas.cd()
    histo_res.Fit(ref_line)
    histo_res.Draw("E,X0")
    ref_line.Draw("SAME")
    canvas.Update()
    histo_res.SetStats(0)
    canvas.Update()

def residuals_background(histo,histo_res,function,canvas,minX,minHoleX,maxHoleX,maxX,nBIN):
    histo_res.GetYaxis().SetRangeUser(0.81,1.19)
    for i in range(nBIN):
        if ( (histo.GetBinCenter(i)>minX and histo.GetBinCenter(i)<minHoleX) or (histo.GetBinCenter(i)>maxHoleX and histo.GetBinCenter(i)<maxX)):
            diff = histo.GetBinContent(i)/function.Eval(histo.GetBinCenter(i))
            err = histo.GetBinError(i)/function.Eval(histo.GetBinCenter(i))
            histo_res.SetBinContent(i,diff)
            histo_res.SetBinError(i,err)
    ref_line = ROOT.TF1("ref_line","pol0",0,20000,1)
    TF1Settings(ref_line,ROOT.kGray+2,1,3)
    ref_line.FixParameter(0,1)
    canvas.cd()
    histo_res.Fit(ref_line)
    histo_res.Draw("E,X0")
    ref_line.Draw("SAME")
    canvas.Update()
    histo_res.SetStats(0)
    canvas.Update()