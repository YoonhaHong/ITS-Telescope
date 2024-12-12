//
//  TestSystem.cpp
//
//  Created by Mauro Aresti and Carlo Puggioni on 10/06/2021.
//  Copyright (c) 2021 Mauro Aresti and Carlo Puggioni. All rights reserved.
//

#include "TTestsetup.h"
#include "stdio.h"
#include <unistd.h>
#include <cstdlib>

////////////////////////////////////////////////////////////////////////
//                                                                    //
//                    class TTestSetup                                //
//                                                                    //
////////////////////////////////////////////////////////////////////////



TTestSetup::TTestSetup () {
    InitLibUsb();
}


TTestSetup::~TTestSetup() {
    for (int i = 0; i < fNDAQBoards; i++) {
        delete fDAQBoards.at(i);
    }
}


int TTestSetup::InitLibUsb() {
    int err = libusb_init(&fContext);
    if (err) {
        std::cout << "Error " << err << " while trying to init libusb " << std::endl;
    }
    return err;
}

bool TTestSetup::IsDAQBoard(libusb_device *ADevice) {

    libusb_device_descriptor desc;
    libusb_get_device_descriptor(ADevice, &desc);

//    std::cout << std::hex << "Vendor id " << (int)desc.idVendor << ", Product id " << (int)desc.idProduct << std::dec << std::endl;

    if ((desc.idVendor == DAQ_BOARD_VENDOR_ID) && (desc.idProduct == DAQ_BOARD_PRODUCT_ID)) {
      //std::cout << "Serial number " << (int)desc.iSerialNumber << std::endl;
        return true;
    }

    return false;
}

int TTestSetup::AddDAQBoard (libusb_device *ADevice) {
    TDAQBoard *db;
   
    db = new TDAQBoard(ADevice);

    if (db) {
        fDAQBoards.push_back(db);
        fNDAQBoards ++;
        return 0;
    }
    else {
        return -1;
    }
}

int TTestSetup::FindDAQBoards () {
    fNDAQBoards = 0;
    int err     = 0;
    InitLibUsb();
    libusb_device **list;

    ssize_t cnt = libusb_get_device_list(fContext, &list);

    if (cnt < 0) {
        std::cout << "Error getting device list" << std::endl;
        return -1;
    }

    for (ssize_t i = 0; i < cnt; i++) {
        libusb_device *device = list[i];
        if (IsDAQBoard(device)) {
    	    err = AddDAQBoard(device);
            if (err) {
                std::cout << "Problem adding DAQ board" << std::endl;
                libusb_free_device_list(list, 1);
                return err;
            }
        }
    }
    libusb_free_device_list(list, 1);
    return err;
}

TDAQBoard * TTestSetup::GetDAQBoard  (int i) {
  if (i >= fNDAQBoards) {
    std::cout << "ERROR: Trying to access non existing DAQ board " << i << ". Exiting ... " << std::endl;
    exit (EXIT_FAILURE);
  }
  return fDAQBoards.at(i);
}

void TTestSetup::cleanExit() {
    struct libusb_context *context = GetContext();
    libusb_exit(context);
    //exit (AExitValue);
}
