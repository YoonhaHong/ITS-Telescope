//
//  TestSystem.h
//
//  Created by Mauro Aresti and Carlo Puggioni on 10/06/2021.
//  Copyright (c) 2021 Mauro Aresti and Carlo Puggioni. All rights reserved.
//

#ifndef __apts_dpts_ce65_software__TestSystem__
#define __apts_dpts_ce65_software__TestSystem__

#include <iostream>
#include <vector>
#include <map>
#include <string>

//#include "libusb.h"
#include <libusb-1.0/libusb.h>

#include "USB.h"
#include "TDaqboard.h"



const int DAQ_BOARD_VENDOR_ID  = 0x4b4;
const int DAQ_BOARD_PRODUCT_ID = 0xf1;
const int INTERFACE_NUMBER     = 0;

extern bool StopADCData;

class TTestSetup {
 private:
    int  InitLibUsb      ();
    bool IsDAQBoard      (libusb_device *ADevice);
    int  AddDAQBoard     (libusb_device *ADevice);

 protected:
    int                    fNDAQBoards;
    std::vector<TDAQBoard*> fDAQBoards;
    struct libusb_context * fContext;

 public:
    TTestSetup        ();
    ~TTestSetup       ();
    virtual int  FindDAQBoards          ();
    int          GetNDAQBoards          () {return fNDAQBoards;};
    virtual TDAQBoard   *GetDAQBoard    (int i);   
    struct libusb_context * GetContext   () {return fContext;};
    void cleanExit();
    
};

#endif /* defined(__apts_dpts_ce65_software__TestSystem__) */
