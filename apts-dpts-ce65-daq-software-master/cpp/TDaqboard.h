//
//  TDaqboard.h
//
//  Created by Mauro Aresti and Carlo Puggioni on 10/06/2021.
//  Copyright (c) 2021 Mauro Aresti and Carlo Puggioni. All rights reserved.
//

#ifndef __apts_dpts_ce65_software__TDaqboard__
#define __apts_dpts_ce65_software__TDaqboard__

#include <iostream>
#include <fstream>
#include <vector>
#include <deque>
#include <map>
#include <string>
#include <stdint.h>

#include "USB.h"


struct SFieldReg {
    std::string name;
    int  size;
    int  addr;
    uint32_t  min_value;
    uint32_t  max_value;
    uint32_t setValue;
    uint32_t readValue;
};

typedef struct SADCData {
    bool     LDOOn;
    uint64_t TimeStamp;
    float    Temp;
    float    MonV;
    float    MonI;
    float    IDig;
    float    IDigIO;
    float    IAna;
} TADCData;

struct SADCCountData {
    bool              LDOStatus;
    unsigned int      ModuleAddress;
    unsigned short    DataType;
    uint32_t          TimeStamp1;
    uint32_t          TimeStamp2;
    unsigned short    Temp_adc0;
    unsigned short    MonV_adc1;
    unsigned short    MonI_adc2;
    unsigned short    IDig_adc3;
    unsigned short    IDigIO_adc4;
    unsigned short    IAna_adc5;
};

class TDAQBoard : public TUSBBoard {
public:
	//DAQ Vendor And
    static const int DAQ_BOARD_VENDOR_ID  = 0x4b4;
    static const int DAQ_BOARD_PRODUCT_ID = 0xf1;
    //Endpoints
    static const int NEndpoints = 4;
    static const int ENDPOINT_WRITE_REG =0;
    static const int ENDPOINT_READ_REG  =1;
    static const int ENDPOINT_READ_ADC  =2;
    static const int ENDPOINT_READ_DATA =3;
    
    // Schema Instruction Word
    static const int SIZE_WORD        = 4; // byte
    static const int SIZE_ADDR_REG    = 8; // bit
    static const int SIZE_ADDR_MODULE = 4; // bit
    static const int SIZE_READ_WRITE  = 1; // bit
protected:
    // Address Module
    static const int MODULE_FPGA      = 0x0;
    static const int MODULE_ADC       = 0x1;
    static const int MODULE_JTAG      = 0x4;
    static const int MODULE_RESET     = 0x5;
    static const int MODULE_IDENT     = 0x6;
    static const int MODULE_SOFTRESET = 0x7;

    // ADC Module: Register
    static const int ADC_CONFIG0  = 0x0;
    static const int ADC_CONFIG1  = 0x1;
    static const int ADC_CONFIG2  = 0x2;
    static const int ADC_READ0    = 0x3; // Read only
    static const int ADC_READ1    = 0x4; // Read only
    static const int ADC_READ2    = 0x5; // Read only
    static const int ADC_OVERFLOW = 0x9; // Read only

    // JTAG Module: Register
    static const int DAQ_WRITE_INSTR_REG  = 0x0;
    static const int DAQ_WRITE_DATA_REG   = 0x1;


    // RESET Module: Register
    static const int RESET_DURATION    = 0x0;
    static const int RESET_DELAYS      = 0x1;
    static const int RESET_DRST        = 0x2;
    static const int RESET_PRST        = 0x3;
    static const int RESET_PULSE       = 0x4;
    static const int RESET_PULSE_DELAY = 0x5;
    static const int RESET_POWERON     = 0x6;
    ;
    // IDENTIFICATION Module: Register
    static const int IDENT_ADDRESS     = 0x0;
    static const int IDENT_FIRMWARE    = 0x2;

    // SOFTRESET Module Register
    static const int SOFTRESET_DURATION   = 0x0;
    static const int SOFTRESET_FPGA_RESET = 0x1;
    static const int SOFTRESET_FX3_RESET  = 0x2;
private:
    std::vector <SFieldReg> fAckHeader;
    std::vector <SFieldReg> fAckData;
    std::vector <SFieldReg> fADCConfigReg0;
    std::vector <SFieldReg> fADCConfigReg1;
    std::vector <SFieldReg> fADCRead0;
    std::vector <SFieldReg> fADCRead1;
    std::vector <SFieldReg> fADCRead2;
    std::vector <SFieldReg> fADCHeader;
    std::vector <SFieldReg> fIDReg;;
    std::vector <SFieldReg> fIDFirmware;

    bool fDummy;
    std::map <std::string,int> fMapNameId;


// Readout ADC
    std::ofstream fADCFileCSV_RO;
    std::vector <SADCCountData> fADCPacket;
    uint32_t fLastADCWords[6];
    int      fNumADCEvent;
    int      fNumLastADCWords;
    void     ReadFirmwareVersion ();
protected:
    uint32_t fFirmwareVersion;

    void     GetBinaryStringFromInt         (unsigned char * binStr, uint32_t number, int sizeWord);
    uint32_t GetIntFromBinaryString         (int numByte, unsigned char *str);
    int  GetNumberByte(int number);
    uint32_t GetMaskBit(int sizeField, int numByteBefore);
    bool DecodeStringRead(std::vector <SFieldReg>& reg,uint32_t value);
    bool SetFieldValue(std::vector <SFieldReg>& reg, int id, uint32_t value);
    bool GetRegValue(std::vector <SFieldReg> reg, uint32_t * value);
    
    
    void SplitStringRead(unsigned char *string_read, unsigned char *header, unsigned char *data);
    void DefineADCConfigReg0 ();
    void DefineADCConfigReg1 ();
    void DefineADCRead0      ();
    void DefineADCRead1      ();
    void DefineADCRead2      ();
    void DefineIDReg         ();
    void DefineAckHeader     ();
    void DefineAckData       ();
    void DefineADCHeader     ();
    void DefineIDFirmware    ();


    bool CheckNameExist(std::string name);
    void DumpMap();


public:
    TDAQBoard (libusb_device *ADevice);
    virtual const char *GetClassName () { return "TDAQBoard 1";};
    bool SendWord(uint32_t value);
    bool ReadAck();


    bool SendFieldValue(std::string name, std::vector <SFieldReg>& reg, uint32_t value);
   

    // The following methods are supposed to get register addresses and values at input parameters and translate them into the corresponding command
    // "Command" here means the 1-to-4 word structure which is to be sent to the USB interface.
    // The methods will then directly call the correct USB transfer function, inherited from TUSBBoard
    // Parameters and types of return values still to be defined, the ints are only placeholders...



    bool WriteRegister       (int module, int addr_reg,int value);
    bool ReadRegister        (std::vector <SFieldReg>& reg, uint32_t *ReadValue);
    uint32_t ReadRegister    (int module, int addr_reg);
    bool ReadRegister        (int AAddress, uint32_t *AValue);
    bool WriteRegister       (std::vector <SFieldReg>& reg);
    


    bool            PowerOn      (int &AOverflow, bool disablePOR=false);
    int             GetBoardAddress ();
    bool            ResetBoardFPGA  (int ADuration = 8);
    bool            ResetBoardFX3   (int ADuration = 8);
    uint32_t        GetIntFromBinaryStringReversed (int numByte, unsigned char *str);

    std::string     GetFirmwareName     ();
    uint32_t        GetFirmwareVersion  () {return fFirmwareVersion;};
    void            SetFirmwareVersion  (uint32_t ver) { if (fDummy) fFirmwareVersion = ver; }
    uint32_t        GetFirmwareDate     () {return (fFirmwareVersion & 0xffffff);};


// ADC
    int GetIdField(std::string name);
    std::vector <SFieldReg>& GetADCConfigReg0(){return fADCConfigReg0;};
    std::vector <SFieldReg>& GetADCConfigReg1(){return fADCConfigReg1;};
    std::vector <SFieldReg>& GetADCRead0(){return fADCRead0;};
    std::vector <SFieldReg>& GetADCRead1(){return fADCRead1;};
    std::vector <SFieldReg>& GetADCRead2(){return fADCRead2;};
    
    uint32_t ReadADC      (std::vector <SFieldReg>& reg, int id);
    uint32_t ReadMonI     ();
    uint32_t ReadMonV     ();
    float ReadDigitalI    ();
    float ReadOutputI     ();
    float ReadAnalogI     ();
    bool  GetLDOStatus    (int &AOverflow);
    void  DecodeOverflow  (int AOverflow);
    static int      CurrentToADC (int ACurrent);  // conversion functions for IDD, IDDO and IDDA ADCs
    static float    ADCToCurrent (int AValue);    // current values given in mA
    static float    ADCToTemperature (int AValue);
    void            ReadAllADCs  ();
    float           GetTemperature();
    void            DecodeADCData         (unsigned char *data_buf, TADCData &Data);
    bool SendIrefValues(std::vector <SFieldReg>& ADCreg0, std::vector <SFieldReg>& ADCreg1,uint32_t iref0,uint32_t iref1,uint32_t iref2);
    bool SendADCControlReg(std::vector <SFieldReg>& ADCreg0, uint32_t LDOSelfShtdn, uint32_t LDOff);
    bool SendStartStreamDataADC(std::vector <SFieldReg>& ADCreg0);
    bool SendEndStreamDataADC(std::vector <SFieldReg>& ADCreg0);
    bool SendADCConfigReg0(std::vector <SFieldReg>& ADCreg0,uint32_t iref0,uint32_t iref1,uint32_t LDOSelfShtdn, uint32_t LDOff, uint32_t StreamADC,uint32_t ADCSelfStop, uint32_t DisableResetTimeStamp, uint32_t EnablePacketBased);
    bool SendADCConfigReg1(std::vector <SFieldReg>& ADCreg1,uint32_t iref2);
    bool ReadoutADCPacketRawData(int *ANumEv, int *ALength, int AMaxLength, bool *endRun, std::ofstream * AFileRawData, bool write =true, bool countEV = true);
    bool ReadoutADCPacket(int *ANumEv, int *ALength, int AMaxLength, bool *endRun);
    uint32_t GetADCLDOstatus(int id_event)     {return fADCPacket.at(id_event).LDOStatus;}
    uint32_t GetADCModuleAddress(int id_event) {return fADCPacket.at(id_event).ModuleAddress;}
    uint32_t GetADCDataType(int id_event)      {return fADCPacket.at(id_event).DataType;}
    uint32_t GetADCTimeStamp1(int id_event)    {return fADCPacket.at(id_event).TimeStamp1;}
    uint32_t GetADCTimeStamp2(int id_event)    {return fADCPacket.at(id_event).TimeStamp2;}
    uint32_t GetADC0(int id_event)	       {return fADCPacket.at(id_event).Temp_adc0;}
    uint32_t GetADC1(int id_event)	       {return fADCPacket.at(id_event).MonV_adc1;}
    uint32_t GetADC2(int id_event)	       {return fADCPacket.at(id_event).MonI_adc2;}
    uint32_t GetADC3(int id_event)	       {return fADCPacket.at(id_event).IDig_adc3;}
    uint32_t GetADC4(int id_event)	       {return fADCPacket.at(id_event).IDigIO_adc4;}
    uint32_t GetADC5(int id_event)             {return fADCPacket.at(id_event).IAna_adc5;}
    unsigned long long GetADCTimeStamp(int id_event)        {return (((unsigned long long)(GetADCTimeStamp2(id_event))) << 24) + GetADCTimeStamp1(id_event);}
    void CreateCSVFileADC_RO(const char * fileName);
    void AddEventCSVFileADC_RO(int num_event);
    void DumpADCWords(int id_event);

};


#endif /* defined(__apts_dpts_ce65_software__TDaqboard__) */
