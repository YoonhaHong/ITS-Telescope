//
//  TDaqboard.cpp
//
//  Created by Mauro Aresti and Carlo Puggioni on 10/06/2021.
//  Copyright (c) 2021 Mauro Aresti and Carlo Puggioni. All rights reserved.
//

#include "TDaqboard.h"
#include "stdio.h"
#include <math.h>
#include "stdint.h"
#include <cstring>
#include <fstream>
#include <iostream>
#include <unistd.h>
#include <cstdlib>

#include <chrono>

//#define MYDEBUG

//---------------------------------------------------------------------------------------------


////////////////////////////////////////////////////////////////////////
//                                                                    //
//                    class TDAQBoard                                 //
//                                                                    //
////////////////////////////////////////////////////////////////////////

#define ASSERTBUFFERLENGTH(maxLength, current, additional) if (current + additional > maxLength) { std::cerr << "Buffer too small (current = " << current << ", add = " << additional << ", max = " << maxLength << "). Exiting!" << std::endl; return false; }

TDAQBoard::TDAQBoard(libusb_device *ADevice) : TUSBBoard(ADevice) {
    // set object variable

    fNumADCEvent     = 0;
    fNumLastADCWords = 0;

    DefineAckHeader     ();
    DefineAckData       ();
    DefineADCHeader     ();
    DefineADCConfigReg0 ();
    DefineADCConfigReg1 ();
    DefineADCRead0      ();
    DefineADCRead1      ();
    DefineADCRead2      ();
    DefineIDReg         ();
    DefineIDFirmware    ();

    if (ADevice) {
        fDummy = false;
    }
    else {
        fFirmwareVersion = 0;
        fDummy = true;
    }
}


void TDAQBoard::DefineAckHeader(){
    SFieldReg field;
// DataType
    field.name = "header";
    field.size = 32;
    field.min_value = 0;
    field.max_value = 0xFFFFFFFF;
    field.setValue = 0;
    fAckHeader.push_back(field);
}

void TDAQBoard::DefineAckData(){
    SFieldReg field;
// DataType
    field.name = "Data";
    field.size = 32;
    field.min_value = 0;
    field.max_value = 0xFFFFFFFF;
    field.setValue = 0;
    fAckData.push_back(field);
}

void TDAQBoard::DefineADCConfigReg0(){
    SFieldReg field;
    int id=0;
    field.addr = ADC_CONFIG0 + (MODULE_ADC << SIZE_ADDR_REG);
// Iref0
    field.name = "Iref0";
    field.size = 12;
    field.min_value = 0;
    field.max_value = 4095;
    field.setValue = 100;
    fADCConfigReg0.push_back(field);
    if (CheckNameExist(field.name)){
        fMapNameId[field.name]=id;
        id++;
    }
// Iref1
    field.name = "Iref1";
    field.size = 12;
    field.min_value = 0;
    field.max_value = 4095;
    field.setValue = 500;
    fADCConfigReg0.push_back(field);
    if (CheckNameExist(field.name)){
        fMapNameId[field.name]=id;
        id++;
    }
// Enable or Disable LDOs self shutdown
    field.name = "EnLDOSelfShtdn";
    field.size = 1;
    field.min_value = 0;
    field.max_value = 1;
    field.setValue = 1;
    fADCConfigReg0.push_back(field);
    if (CheckNameExist(field.name)){
        fMapNameId[field.name]=id;
        id++;
    }
// Enable or Disable LDO shutdown
    field.name = "EnLDOff";
    field.size = 1;
    field.min_value = 0;
    field.max_value = 1;
    field.setValue = 1;
    fADCConfigReg0.push_back(field);
    if (CheckNameExist(field.name)){
        fMapNameId[field.name]=id;
        id++;
    }
// Enable or Disable ADC Stream Data.
    field.name = "EnStreamADCData";
    field.size = 1;
    field.min_value = 0;
    field.max_value = 1;
    field.setValue = 0;
    fADCConfigReg0.push_back(field);
    if (CheckNameExist(field.name)){
        fMapNameId[field.name]=id;
        id++;
    }
// Enable or Disable ADC Stream Data.
    field.name = "ADCSelfStop";
    field.size = 1;
    field.min_value = 0;
    field.max_value = 1;
    field.setValue = 0;
    fADCConfigReg0.push_back(field);
    if (CheckNameExist(field.name)){
        fMapNameId[field.name]=id;
        id++;
    }
// Enable or Disable ADC Stream Data.
    field.name = "ADCDisableResetTimeStamp";
    field.size = 1;
    field.min_value = 0;
    field.max_value = 1;
    field.setValue = 0;
    fADCConfigReg0.push_back(field);
    if (CheckNameExist(field.name)){
        fMapNameId[field.name]=id;
        id++;
    }
// Enable or Disable ADC Stream Data.
    field.name = "ADCEnablePacketBased";
    field.size = 1;
    field.min_value = 0;
    field.max_value = 1;
    field.setValue = 0;
    fADCConfigReg0.push_back(field);
    if (CheckNameExist(field.name)){
        fMapNameId[field.name]=id;
        id++;
    }
}

void TDAQBoard::DefineADCConfigReg1(){
    int id=0;
    SFieldReg field;
    field.addr = ADC_CONFIG1 + (MODULE_ADC << SIZE_ADDR_REG);
// Iref2
    field.name = "Iref2";
    field.size = 12;
    field.min_value = 0;
    field.max_value = 4095;
    field.setValue = 100;
    fADCConfigReg1.push_back(field);
    if (CheckNameExist(field.name)){
        fMapNameId[field.name]=id;
        id++;
    }
}




void TDAQBoard::DefineADCRead0(){
    int id=0;
    SFieldReg field;
    field.addr = ADC_READ0 + (MODULE_ADC << SIZE_ADDR_REG);
// ADC_NTC
    field.name = "ADC_NTC";
    field.size = 12;
    field.min_value = 0;
    field.max_value = 4095;
    field.readValue = 0;
    fADCRead0.push_back(field);
    if (CheckNameExist(field.name)){
        fMapNameId[field.name]=id;
        id++;
    }
// ADC_MONV
    field.name = "ADC_MONV";
    field.size = 12;
    field.min_value = 0;
    field.max_value = 4095;
    field.readValue = 0;
    fADCRead0.push_back(field);
    if (CheckNameExist(field.name)){
        fMapNameId[field.name]=id;
        id++;
    }
}

void TDAQBoard::DefineADCRead1(){
    int id=0;
    SFieldReg field;
    field.addr = ADC_READ1 + (MODULE_ADC << SIZE_ADDR_REG);
// ADC_MONI
    field.name = "ADC_MONI";
    field.size = 12;
    field.min_value = 0;
    field.max_value = 4095;
    field.readValue = 0;
    fADCRead1.push_back(field);
    if (CheckNameExist(field.name)){
        fMapNameId[field.name]=id;
        id++;
    }
// ADC_V18D
    field.name = "ADC_V18D";
    field.size = 12;
    field.min_value = 0;
    field.max_value = 4095;
    field.readValue = 0;
    fADCRead1.push_back(field);
    if (CheckNameExist(field.name)){
        fMapNameId[field.name]=id;
        id++;
    }
}

void TDAQBoard::DefineADCRead2(){
    int id=0;
    SFieldReg field;
    field.addr = ADC_READ2 + (MODULE_ADC << SIZE_ADDR_REG);
// ADC_V18O
    field.name = "ADC_V18O";
    field.size = 12;
    field.min_value = 0;
    field.max_value = 4095;
    field.readValue = 0;
    fADCRead2.push_back(field);
    if (CheckNameExist(field.name)){
        fMapNameId[field.name]=id;
        id++;
    }
// ADC_V18A
    field.name = "ADC_V18A";
    field.size = 12;
    field.min_value = 0;
    field.max_value = 4095;
    field.readValue = 0;
    fADCRead2.push_back(field);
    if (CheckNameExist(field.name)){
        fMapNameId[field.name]=id;
        id++;
    }
}

void TDAQBoard::DefineADCHeader(){
    SFieldReg field;
// DataType
    field.name = "DataType";
    field.size = 2;
    field.min_value = 0;
    field.max_value = 1;
    field.setValue = 0;
    fADCHeader.push_back(field);
// Module Address
    field.name = "ModuleAddr";
    field.size = 4;
    field.min_value = 0;
    field.max_value = 4;
    field.setValue = 0;
    fADCHeader.push_back(field);
// Error Bits
    field.name = "ErrorBits";
    field.size = 4;
    field.min_value = 0;
    field.max_value = 15;
    field.setValue = 0;
    fADCHeader.push_back(field);
// ADC Active
    field.name = "ADC Active";
    field.size = 6;
    field.min_value = 0;
    field.max_value = 63;
    field.setValue = 0;
    fADCHeader.push_back(field);
// Spare
    field.name = "Spare";
    field.size = 16;
    field.min_value = 0;
    field.max_value = 0;
    field.setValue = 0;
    fADCHeader.push_back(field);
    // TimeStamp1
    field.name = "TimeStamp1";
    field.size = 32;
    field.min_value = 0;
    field.max_value = 16777215;
    field.setValue = 0;
    fADCHeader.push_back(field);
    // TimeStamp2
    field.name = "TimeStamp2";
    field.size = 32;
    field.min_value = 0;
    field.max_value = 16777215;
    field.setValue = 0;
    fADCHeader.push_back(field);
}



void TDAQBoard::DefineIDReg(){
    int id=0;
    SFieldReg field;
    field.addr = IDENT_ADDRESS + (MODULE_IDENT << SIZE_ADDR_REG);

    field.name = "BoardAddress";
    field.size = 8;
    field.min_value = 0;
    field.max_value = 0xff;
    field.setValue = 0;
    fIDReg.push_back(field);
    if (CheckNameExist(field.name)){
        fMapNameId[field.name]=id;
        id++;
    }
}

void TDAQBoard::DefineIDFirmware(){
    int id=0;
    SFieldReg field;
    field.addr = IDENT_FIRMWARE + (MODULE_IDENT << SIZE_ADDR_REG);

    field.name = "Day";
    field.size = 8;
    field.min_value = 0;
    field.max_value = 0xff;
    field.setValue = 0;
    fIDFirmware.push_back(field);
    if (CheckNameExist(field.name)){
        fMapNameId[field.name]=id;
        id++;
    }

    field.name = "Month";
    field.size = 4;
    field.min_value = 0;
    field.max_value = 0xc;
    field.setValue = 0;
    fIDFirmware.push_back(field);
    if (CheckNameExist(field.name)){
        fMapNameId[field.name]=id;
        id++;
    }

    field.name = "Year";
    field.size = 12;
    field.min_value = 0;
    field.max_value = 0xfff;
    field.setValue = 0;
    fIDFirmware.push_back(field);
    if (CheckNameExist(field.name)){
        fMapNameId[field.name]=id;
        id++;
    }

    field.name = "FirmwareType";
    field.size = 8;
    field.min_value = 0;
    field.max_value = 0xff;
    field.setValue = 0;
    fIDFirmware.push_back(field);
    if (CheckNameExist(field.name)){
        fMapNameId[field.name]=id;
        id++;
    }
}


bool TDAQBoard::SendFieldValue(std::string name, std::vector <SFieldReg>& reg, uint32_t value){
    int id=-1;
    bool err;
    uint32_t value_reg=-1;
    id=GetIdField(name);
    if (id ==-1) return false;
    err=SetFieldValue(reg, id, value);
    if(err==false) return false;
    err=GetRegValue(reg,&value_reg);
    if(err==false || value_reg==-1) return false;
    //WriteADCRegister(reg.at(id).addr,value_reg);
    WriteRegister(reg);
    return true;
}

bool TDAQBoard::SendIrefValues(std::vector <SFieldReg>& ADCreg0, std::vector <SFieldReg>& ADCreg1, uint32_t iref0,uint32_t iref1, uint32_t iref2){
    bool err;
    uint32_t value_reg=-1;
    err=SetFieldValue(ADCreg0, 0, iref0);
    if(err==false) return false;
    err=SetFieldValue(ADCreg0, 1, iref1);
    if(err==false) return false;
    err=SetFieldValue(ADCreg1, 0, iref2);
    if(err==false) return false;
    err=GetRegValue(ADCreg0,&value_reg);
    if(err==false || value_reg==-1) return false;
    WriteRegister(ADCreg0);
    err=GetRegValue(ADCreg1,&value_reg);
    if(err==false || value_reg==-1) return false;
    WriteRegister(ADCreg1);
    return true;
}

bool TDAQBoard::SendADCControlReg(std::vector <SFieldReg>& ADCreg0, uint32_t LDOSelfShtdn, uint32_t LDOff){
    bool err;
    uint32_t value_reg=-1;
    err=SetFieldValue(ADCreg0, 2, LDOSelfShtdn);
    if(err==false) return false;
    err=GetRegValue(ADCreg0,&value_reg);
    if(err==false || value_reg==-1) return false;
    err=SetFieldValue(ADCreg0, 3, LDOff);
    if(err==false) return false;
    err=GetRegValue(ADCreg0,&value_reg);
    if(err==false || value_reg==-1) return false;
    WriteRegister(ADCreg0);
    return true;
}

bool TDAQBoard::SendADCConfigReg0(std::vector <SFieldReg>& ADCreg0,uint32_t iref0,uint32_t iref1,uint32_t LDOSelfShtdn, uint32_t LDOff,uint32_t StreamADC, uint32_t ADCSelfStop, uint32_t DisableResetTimeStamp, uint32_t EnablePacketBased){
    bool err;
    uint32_t value_reg=-1;
    err=SetFieldValue(ADCreg0, 0, iref0);
    if(err==false) return false;
    err=SetFieldValue(ADCreg0, 1, iref1);
    if(err==false) return false;
    err=SetFieldValue(ADCreg0, 2, LDOSelfShtdn);
    if(err==false) return false;
    err=SetFieldValue(ADCreg0, 3, LDOff);
    if(err==false) return false;
    err=SetFieldValue(ADCreg0, 4, StreamADC);
    if(err==false) return false;
    err=SetFieldValue(ADCreg0, 5, ADCSelfStop);
    if(err==false) return false;
    err=SetFieldValue(ADCreg0, 6, DisableResetTimeStamp);
    if(err==false) return false;
    err=SetFieldValue(ADCreg0, 7, EnablePacketBased);
    if(err==false) return false;
    err=GetRegValue(ADCreg0,&value_reg);
    if(err==false || value_reg==-1) return false;
    WriteRegister(ADCreg0);
    return true;
}

bool TDAQBoard::SendADCConfigReg1(std::vector <SFieldReg>& ADCreg1,uint32_t iref2){
    bool err;
    uint32_t value_reg=-1;
    err=SetFieldValue(ADCreg1, 0, iref2);
    if(err==false) return false;
    err=GetRegValue(ADCreg1,&value_reg);
    if(err==false || value_reg==-1) return false;
    WriteRegister(ADCreg1);
    return true;
}

bool TDAQBoard::ReadoutADCPacketRawData(int *ANumEv, int *ALength, int AMaxLength, bool *endRun, std::ofstream * AFileRawData,bool write, bool countEV){
    unsigned char data_buf[AMaxLength];
    int length=0;
    int num_ADC_word=6;
    int size_word =4; //byte
    uint32_t lastWord=0;
    *ALength = ReceiveData(ENDPOINT_READ_ADC, data_buf, AMaxLength);
   /* for (int i=0; i< *ALength; i++){
       printf("%02X ",data_buf[i]);
       }
    printf("\n\n");  */
    if(write == true){
        AFileRawData->write((const char * )data_buf,*ALength);
	}
    if(countEV == true){	
        length=*ALength+(fNumLastADCWords*size_word);
        *ANumEv=length / (num_ADC_word*size_word);
        //std::cout <<"Length " <<*ALength << " AMaxLength "<<" fNumLastADCWords "<< fNumLastADCWords << AMaxLength <<std::endl;
        fNumLastADCWords=(length % (num_ADC_word*size_word))/size_word;
        }     
    lastWord = GetIntFromBinaryStringReversed(size_word, data_buf + *ALength - size_word);    
    if (lastWord == 0xcafefade) *endRun = true;
    else *endRun = false;
    return true;
}

bool TDAQBoard::ReadoutADCPacket(int *ANumEv, int *ALength, int AMaxLength, bool *endRun){
    int i=0;
    int currentPos=0;
    unsigned char data_buf[AMaxLength];
    int num_ADC_word=6;
    int size_word =4; //byte
    int count_ev;
    int numLastADCWord=0;
    uint32_t lastWord=0;
    uint32_t AADCWord[num_ADC_word];
    SADCCountData ADCEvent;
    fADCPacket.clear();
    numLastADCWord=fNumLastADCWords;
    *ALength = ReceiveData(ENDPOINT_READ_ADC, data_buf, AMaxLength);
    //std::cout << std::dec << "  Length " << *ALength << "  Max Length " << AMaxLength << std::endl;
    fNumADCEvent=*ALength / (num_ADC_word*size_word);
    fNumLastADCWords=(*ALength % (num_ADC_word*size_word))/size_word;
    //std::cout << "Num Event " <<  fNumADCEvent << " Num Last Word " << fNumLastADCWords << std::endl;
    for (count_ev=0; count_ev<fNumADCEvent; count_ev++){
        if (numLastADCWord >0){
            for (i=0;i<numLastADCWord;i++){
                AADCWord[i]=fLastADCWords[i];
                //std::cout << "Last Word " << AADCWord[i] <<" i " << i << " numLastADCWords "<<fNumLastADCWords <<std::endl;
            }
            for (i=numLastADCWord;i<num_ADC_word;i++){
                AADCWord[i]=GetIntFromBinaryStringReversed(size_word, data_buf + currentPos);
                currentPos +=size_word;
            }
            fNumADCEvent=((*ALength-((num_ADC_word -numLastADCWord)*size_word))/(num_ADC_word*size_word))+1;
            fNumLastADCWords=((*ALength-((num_ADC_word -numLastADCWord)*size_word)) % (num_ADC_word*size_word))/size_word;
            numLastADCWord=0;
        }
        else{
            for (i=0; i<num_ADC_word;i++){
                AADCWord[i]=GetIntFromBinaryStringReversed(size_word, data_buf + currentPos);
                currentPos +=size_word;
                //std::cout << "word[" << i << "] " << AADCWord[i] << std::endl;
            }
        }
        ADCEvent.LDOStatus     = (AADCWord[0] & 0x00000040) >> 6;
        ADCEvent.ModuleAddress = (AADCWord[0] & 0x0000003C) >> 2;
        ADCEvent.DataType      = AADCWord[0]  & 0x00000003;
        ADCEvent.TimeStamp1    = AADCWord[1]  & 0x00ffffff;
        ADCEvent.TimeStamp2    = AADCWord[2]  & 0x00ffffff;
        ADCEvent.Temp_adc0     = AADCWord[3]  & 0x00000fff;
        ADCEvent.MonV_adc1     = (AADCWord[3] & 0x00fff000) >> 12;
        ADCEvent.MonI_adc2     = AADCWord[4]  & 0x00000fff;
        ADCEvent.IDig_adc3     = (AADCWord[4] & 0x00fff000) >> 12;
        ADCEvent.IDigIO_adc4   = AADCWord[5]  & 0x00000fff;
        ADCEvent.IAna_adc5     = (AADCWord[5] & 0x00fff000) >> 12;
        fADCPacket.push_back(ADCEvent);
        /*std::cout <<  " LDO Status "    << ADCEvent.LDOStatus;
          std::cout <<  " ModuleAddress " << ADCEvent.ModuleAddress;
          std::cout <<  " DataType "      << ADCEvent.DataType;
          std::cout <<  " TimeStamp1 "    << ADCEvent.TimeStamp1;
          std::cout <<  " TimeStamp2 "    << ADCEvent.TimeStamp2;
          std::cout <<  " Temp_adc0 "     << ADCEvent.Temp_adc0;
          std::cout <<  " MonV_adc1 "     << ADCEvent.MonV_adc1;
          std::cout <<  " MonI_adc2 "     << ADCEvent.MonI_adc2;
          std::cout <<  " IDig_adc3 "     << ADCEvent.IDig_adc3;
          std::cout <<  " IDigIO_adc4 "   << ADCEvent.IDigIO_adc4;
          std::cout <<  " IAna_adc5 "     << ADCEvent.IAna_adc5 << std::endl;*/
    }

    if (fNumLastADCWords>0){
        for (i=0; i< fNumLastADCWords; i++){
            fLastADCWords[i]=GetIntFromBinaryStringReversed(size_word, data_buf + currentPos);
            //std::cout << "Last Word " << std::hex << fLastADCWords[i] << std::dec << " i " << i << " fNumLastADCWords "<<fNumLastADCWords <<std::endl;
            currentPos +=size_word;
        }
    }
    fNumADCEvent=count_ev;
    *ANumEv=fNumADCEvent;
    //std::cout << "Num Events  " << fNumADCEvent << std::endl;
    lastWord = GetIntFromBinaryStringReversed(size_word, data_buf + *ALength - size_word);
    if (lastWord == 0xcafefade) *endRun = true;
    else *endRun = false;
    return true;
}

void TDAQBoard::CreateCSVFileADC_RO(const char * fileName){
    fADCFileCSV_RO.open (fileName, std::ofstream::out);
    fADCFileCSV_RO << "rownum;Time_Stamp[47:0](dec);ADC0[11:0](dec);ADC1[11:0](dec);ADC2[11:0](dec);ADC3[11:0](dec);ADC4[11:0](dec);ADC5[11:0](dec);";
    fADCFileCSV_RO <<"LDOStat[0];DataType;ModuleAddress(dec);";
    fADCFileCSV_RO << "Time_Stamp[47:0](hex);ADC0[11:0](hex);ADC1[11:0](hex);ADC2[11:0](hex);ADC3[11:0](hex);ADC4[11:0](hex);ADC5[11:0](hex)";
    fADCFileCSV_RO << std::endl;
}

void TDAQBoard::AddEventCSVFileADC_RO(int num_event){
    num_event +=1;
    for(int i=0;i< fNumADCEvent; i++){
        fADCFileCSV_RO << std::dec << num_event <<";" << GetADCTimeStamp(i) << ";";
        fADCFileCSV_RO << std::dec << GetADC0(i) << ";" << GetADC1(i) << ";" << GetADC2(i)  << ";" << GetADC3(i) << ";" << GetADC4(i) << ";" << GetADC5(i) << ";";
        fADCFileCSV_RO << std::dec << GetADCLDOstatus(i) << ";" << GetADCDataType(i) << ";" << GetADCModuleAddress(i) << ";";
        fADCFileCSV_RO << std::hex << GetADCTimeStamp(i) << ";";
        fADCFileCSV_RO << std::hex << GetADC0(i) << ";" << GetADC1(i) << ";" << GetADC2(i)  << ";" << GetADC3(i) << ";" << GetADC4(i) << ";" << GetADC5(i) << ";";
        //std::cout << "num_event  " << num_event << " fNumADCEvent2  " << fNumADCEvent << " i "<< i << std::endl ;
        fADCFileCSV_RO << std::endl;
        num_event++;
    }
}

void TDAQBoard::DumpADCWords (int id_event){
    std::cout <<  "LDO Status "      << std::hex <<  GetADCLDOstatus(id_event);
    std::cout <<  " Module Address " << std::hex <<  GetADCModuleAddress(id_event);
    std::cout <<  " DataType "       << std::hex <<  GetADCDataType(id_event);
    std::cout <<  " Time stamp "     << std::hex <<  GetADCTimeStamp(id_event);
    std::cout <<  " Time stamp 1 "   << std::hex <<  GetADCTimeStamp1(id_event);
    std::cout <<  " Time stamp 2 "   << std::hex <<  GetADCTimeStamp2(id_event);
    std::cout <<  " ADC0 "	      << std::hex <<  GetADC0(id_event);
    std::cout <<  " ADC1 "	      << std::hex <<  GetADC1(id_event);
    std::cout <<  " ADC2 "	      << std::hex <<  GetADC2(id_event);
    std::cout <<  " ADC3 "	      << std::hex <<  GetADC3(id_event);
    std::cout <<  " ADC4 "	      << std::hex <<  GetADC4(id_event);
    std::cout <<  " ADC5 "	      << std::hex <<  GetADC5(id_event);
    std::cout << std::dec << std::endl;
}

bool TDAQBoard::SendStartStreamDataADC(std::vector <SFieldReg>& ADCreg0){
    bool err;
    err= SendFieldValue("EnStreamADCData",ADCreg0,1);
    return err;
}


bool TDAQBoard::SendEndStreamDataADC(std::vector <SFieldReg>& ADCreg0){
    bool err;
    err = SendFieldValue("EnStreamADCData",ADCreg0,0);
    return err;
}

bool TDAQBoard::CheckNameExist(std::string name){
    std::map<std::string,int>::iterator iter = fMapNameId.find(name);
    if (iter == fMapNameId.end()){
	    return true;
	}
	std::cout << "Error: The name of field already eixst !!!" << std::endl;
    return false;
}

int TDAQBoard::GetIdField(std::string name){
    int id=-1;
    std::map<std::string,int>::iterator iter = fMapNameId.find(name);
    if (iter != fMapNameId.end()) id= iter->second;
    else std::cout << "Error: Field "<< name <<" don't found !!!" << std::endl;
    return id;
}

void TDAQBoard::DumpMap(){

    std::cout << "Dump Map Name Id" << std::endl;
    for (std::map<std::string,int>::iterator iter = fMapNameId.begin(); iter!=fMapNameId.end(); ++iter){
        std::cout << iter->first << " => " << iter->second << std::endl;
    }
}


/*
 * The function divides an integer in bytes and put the result in a string. Reverts the byte order
 */
void TDAQBoard::GetBinaryStringFromInt(unsigned char * binStr, uint32_t number, int sizeWord){

    for (int i=0; i<sizeWord; i++) {
        binStr[i] = number & 0xff;
        number >>= 8;
    }

}


/*
 * The function converts a string 32 bit in integer. Keeps the byte order
 */
uint32_t TDAQBoard::GetIntFromBinaryString(int numByte, unsigned char *str){
    uint32_t number=0;
    int pos=0;
    int exp = numByte -1;
    while (pos < numByte){
    	number= number + (uint32_t)(str[pos] << 8*exp);
    	exp--;
    	pos++;
    }
    return number;
}


uint32_t TDAQBoard::GetIntFromBinaryStringReversed(int numByte, unsigned char *str){
    uint32_t number = 0;
    int      pos    = 0;
    while (pos < numByte){
    	number= number + (uint32_t)(str[pos] << 8*pos);
    	pos++;
    }
    return number;
}


/*
 * Get number of byte to rappresent a decimal number in a binary string.
 */
int TDAQBoard::GetNumberByte(int number){
    int numByte = 1;
    uint32_t num;
    num=255;
    if (number > 0 ){
        while (number > num){
            num = 255 + (num * 255);
            numByte++;
        }
        return numByte;
    }
    return -1;
}

bool TDAQBoard::SetFieldValue(std::vector <SFieldReg>& reg, int id, uint32_t value_reg){
    if (value_reg < reg.at(id).min_value || value_reg > reg.at(id).max_value){
        std::cout << "Error: the value of" << reg.at(id).name <<  "must be a value between" << reg.at(id).min_value << "and" << reg.at(id).max_value << "(requested was " << value_reg << ")"<< std::endl;
        return false;
    }
    if (id < 0 || id > reg.size()) {
        std::cout << "Error: the id value of" << reg.at(id).name <<  "must be a value between 0 and" << reg.size() << std::endl;
        return false;
    }
    reg.at(id).setValue=value_reg;
    return true;
}

// value will be contains the integer value of register
bool TDAQBoard::GetRegValue(std::vector <SFieldReg> reg,uint32_t * value){
    uint32_t calc_value=-1;
    int size=0;
    if(reg.size() < 1) return false;
    size=0;
    for (int i = 0; i<reg.size(); i++){
        if(i==0){
            calc_value=reg.at(i).setValue;
        }
        if(i>0){
            size=size+reg.at(i-1).size;
            calc_value=calc_value + (reg.at(i).setValue << size);
        }
        *value= calc_value;
    }
    return true;
}

uint32_t TDAQBoard::GetMaskBit(int sizeField, int numBitBefore){
    uint32_t bitMask=1;
    if (sizeField <=0 || numBitBefore < 0){
        std::cout << "Error: The size of field or the number of bit is not correct !!!."<< std::endl;
        return 0;
    }
    for (int i=1;i<sizeField;i++){
        bitMask= (bitMask << 1) +1;
    }
    bitMask=bitMask << numBitBefore;
    return bitMask;
}

bool TDAQBoard::DecodeStringRead(std::vector <SFieldReg>& reg,uint32_t value){
    int numBitBefore=0;
    uint32_t value_field=0;
    for (int i=0; i< reg.size(); i++){
        value_field = (value & GetMaskBit(reg.at(i).size, numBitBefore)) >> numBitBefore;
        numBitBefore += reg.at(i).size;
        reg.at(i).readValue = value_field;
#ifdef MYDEBUG
        std::cout << std::dec<<reg.at(i).name << " : \t" << reg.at(i).readValue << std::endl;
#endif
        value_field=0;
    }
    return true;
}

void TDAQBoard::SplitStringRead(unsigned char *string_read, unsigned char *header, unsigned char *data){
    int i,k;
#ifdef MYDEBUG
    printf ("\nWordHeader:");
#endif
    k=0;
    for (i=3; i>=0; i--){
        header[k]=string_read[i];
#ifdef MYDEBUG
        printf ("%02X", header[k]);
#endif
        k++;
    }
    //header[k]='\0';
    k=0;
#ifdef MYDEBUG
    printf ("\nWordData:");
#endif
    for (i=7; i>=4; i--){
        data[k]=string_read[i];
#ifdef MYDEBUG
        printf ("%02X", data[k]);
#endif
        k++;
    }
#ifdef MYDEBUG
    printf("\n");
#endif
    //data[k]='\0';
}

bool TDAQBoard::SendWord(uint32_t value){
    int err;
    unsigned char data_buf[SIZE_WORD];
    std::cout << std::hex << "SendWord: Send Value: 0x" << value << std::dec << std::endl;
#ifdef MYDEBUG
    std::cout << std::hex << "SendWord: Send Value: 0x" << value << std::dec << std::endl;
#endif
    GetBinaryStringFromInt(data_buf, value,SIZE_WORD);
    err=SendData (ENDPOINT_WRITE_REG,data_buf,SIZE_WORD);
    if(err<0) return false;
    return true;
}

bool TDAQBoard::ReadAck(){
    uint32_t receiveValueHeader=-1;
    uint32_t receiveValueData=-1;
    unsigned char data_buf[SIZE_WORD*2];
    unsigned char header[SIZE_WORD];
    unsigned char data[SIZE_WORD];
    int err;

    err=ReceiveData(ENDPOINT_READ_REG, data_buf,SIZE_WORD*2);
    if(err<0) return false;
    SplitStringRead(data_buf,header,data);
    receiveValueHeader=GetIntFromBinaryString(SIZE_WORD,header);
#ifdef MYDEBUG
    std::cout << std::hex << "ReadAck: Header Value: 0x" << receiveValueHeader << std::dec << std::endl;
#endif
    receiveValueData=GetIntFromBinaryString(SIZE_WORD,data);
#ifdef MYDEBUG
    std::cout << std::hex << "ReadAck: Data Value: 0x" << receiveValueData << std::dec << std::endl;
#endif
    DecodeStringRead(fAckHeader,receiveValueHeader);
    DecodeStringRead(fAckData,receiveValueData);
    return true;
}

bool TDAQBoard::ReadRegister(std::vector <SFieldReg>& reg, uint32_t *ReadValue){
    uint32_t receiveValueHeader=-1;
    uint32_t receiveValueData=-1;
    unsigned char data_buf[SIZE_WORD*2];
    unsigned char header[SIZE_WORD];
    unsigned char data[SIZE_WORD];
    uint32_t command;
    int err;
    command = reg.at(0).addr + (1 << (SIZE_ADDR_REG + SIZE_ADDR_MODULE));
    // std::cout << std::hex << "Send Value: 0x" << command << std::endl;
    GetBinaryStringFromInt(data_buf, command,SIZE_WORD);
    err=SendData (ENDPOINT_WRITE_REG,data_buf,SIZE_WORD);
    if(err<0) return false;
    err=ReceiveData(ENDPOINT_READ_REG, data_buf,SIZE_WORD*2);
    if(err<0) return false;
    SplitStringRead(data_buf,header,data);
    receiveValueHeader=GetIntFromBinaryString(SIZE_WORD,header);
    //std::cout << std::hex << "Header Value: 0x" << receiveValueHeader << std::endl;
    receiveValueData=GetIntFromBinaryString(SIZE_WORD,data);
    //std::cout << std::hex << "Read Value: 0x" << receiveValueData << std::endl;
    *ReadValue = receiveValueData;
    DecodeStringRead(fAckHeader,receiveValueHeader);
    DecodeStringRead(reg,receiveValueData);
    return true;
}

//
//---------------------------------------------------------------------------------------------  
uint32_t TDAQBoard::ReadRegister(int module, int addr_reg){
    int addr = 0;
    uint32_t value;
    addr = addr_reg + (module << SIZE_ADDR_REG );
    ReadRegister(addr, &value);
    //std::cout  << "Read ADC Register: " << std::hex << addr  << " Value " << value << std::endl; 
    return value;
    }


bool TDAQBoard::ReadRegister(int AAddress, uint32_t *AValue){
    uint32_t receiveValueHeader=-1;
    uint32_t receiveValueData=-1;
    unsigned char data_buf[SIZE_WORD*2];
    unsigned char header[SIZE_WORD];
    unsigned char data[SIZE_WORD];
    uint32_t command;
    int err;
    command =  AAddress + (1 << (SIZE_ADDR_REG + SIZE_ADDR_MODULE));
    // std::cout << std::hex << "Send Value: 0x" << command << std::dec << std::endl;
    GetBinaryStringFromInt(data_buf, command,SIZE_WORD);
    err=SendData (ENDPOINT_WRITE_REG,data_buf,SIZE_WORD);
    if(err<0) return false;
    err=ReceiveData(ENDPOINT_READ_REG, data_buf,SIZE_WORD*2);
    if(err<0) return false;
    SplitStringRead(data_buf,header,data);
    receiveValueHeader=GetIntFromBinaryString(SIZE_WORD,header);
    //std::cout << std::hex << "Header Value: 0x" << receiveValueHeader << std::dec << std::endl;
    receiveValueData=GetIntFromBinaryString(SIZE_WORD,data);
    //std::cout << std::hex << "Read Value: 0x" << receiveValueData << std::dec << std::endl;
    *AValue = receiveValueData;
    return true;
}

std::string TDAQBoard::GetFirmwareName() {
    char buffer[100];
    uint32_t readValue;
    ReadRegister(fIDFirmware, &readValue);

    sprintf(buffer, "%x %d/%d/%d", readValue, fIDFirmware.at(0).readValue, fIDFirmware.at(1).readValue, fIDFirmware.at(2).readValue);
    return buffer;
}


void TDAQBoard::ReadFirmwareVersion() {
    uint32_t readValue;
    ReadRegister(fIDFirmware, &readValue);
    fFirmwareVersion = readValue;
}


bool TDAQBoard::WriteRegister(std::vector <SFieldReg>& reg){
    uint32_t command[2];
    bool err;
    uint32_t value;//-1;

    err=GetRegValue(reg,&value);
    if(err==false) return false; // || value==-1) return false;
    command[0] = reg.at(0).addr;
    command[1] = value;
    //std::cout << "[FPGA] ADDRESS: " << std::hex <<  command[0] << " VALUE " << command[1] << std::dec << std::endl;

    #ifdef CPDEBUG
        //std::cout << "Write_1 [FPGA] ADDRESS: " << std::hex <<  command[0] << " VALUE " << command[1] << std::dec << std::endl;
        //std::cout <<"Press Enter to proceed _ " << std::endl;
        //std::cin.get();
    #endif

//Send Instruction Word
    err=SendWord(command[0]);
    if(err==false) return false;
// Send Data Word
    err=SendWord(command[1]);
    if(err==false) return false;
// Read ack Word
    err=ReadAck();
    if(err==false) return false;
    return true;
}

bool TDAQBoard::WriteRegister(int module, int addr_reg,int value){
    int addr = 0;
    bool err;
    addr = addr_reg + (module<< SIZE_ADDR_REG ) + (0 << (SIZE_ADDR_REG + SIZE_ADDR_MODULE));
    err = SendWord(addr);
    if (!err) return false;
    err = SendWord(value);
    if (!err) return false;
    err = ReadAck();
    if (!err) return false;
    //std::cout  << "Write ADC Register: " << std::hex << addr << " Value " << value << std::endl; 
    return true;
    }

int TDAQBoard::GetBoardAddress() {
    uint32_t ReadValue;
    bool err = ReadRegister(fIDReg, &ReadValue);
    if (err) return (~ReadValue) & 0x0f;
    return -1;
}


bool TDAQBoard::GetLDOStatus(int &AOverflow) {
    uint32_t ReadValue;
    bool     err, reg0, reg1, reg2;

    err  = ReadRegister (fADCRead0, &ReadValue);
    reg0 = ((ReadValue & 0x1000000) != 0);
    err  = ReadRegister (fADCRead1, &ReadValue);
    reg1 = ((ReadValue & 0x1000000) != 0);
    err  = ReadRegister (fADCRead2, &ReadValue);
    reg2 = ((ReadValue & 0x1000000) != 0);

    err = ReadRegister((MODULE_ADC << SIZE_ADDR_REG) + ADC_OVERFLOW, &ReadValue);

    AOverflow = (int) ReadValue;

    if (! (reg0 & reg1 & reg2))
        std::cout << "GetLDOStatus, LDO status = " << reg0 << ", " << reg1 << ", " << reg2 << std::endl;
    return ( reg0& reg1 & reg2);
}


void TDAQBoard::DecodeOverflow  (int AOverflow) {
    if (AOverflow & 0x1) {
        std::cout << "Overflow in digital current" << std::endl;
    }
    if (AOverflow & 0x2) {
        std::cout << "Overflow in digital I/O current" << std::endl;
    }
    if (AOverflow & 0x4) {
        std::cout << "Overflow in analogue current" << std::endl;
    }
}


uint32_t TDAQBoard::ReadADC(std::vector <SFieldReg>& reg, int id){
    uint32_t readValue;
    bool err;
    err=ReadRegister(reg, &readValue);
    if (err== false) return -1;
    return reg.at(id).readValue;

}


void TDAQBoard::ReadAllADCs()
{
    std::cout << std::dec;
    std::cout << "Read ADC: NTC              = " << GetTemperature() - 273.15 << " deg C" << std::endl;
    //    std::cout << "Read ADC: MONV             = " << ReadMonV() << " ADC counts" << std::endl;
    //    std::cout << "Read ADC: MONI             = " << ReadMonI() << " ADC counts" << std::endl;
    std::cout << "Read ADC: I(1.8 V Digital) = " << ReadDigitalI() << " mA" << std::endl;
    std::cout << "Read ADC: I(1.8 V Output)  = " << ReadOutputI() << " mA" << std::endl;
    std::cout << "Read ADC: I(1.8 V Analog)  = " << ReadAnalogI() << " mA" << std::endl;
}


uint32_t TDAQBoard::ReadMonI() {
    return ReadADC(fADCRead1,0);
}


uint32_t TDAQBoard::ReadMonV() {
    return ReadADC(fADCRead0,1);
}

float TDAQBoard::ReadDigitalI() {
    return ADCToCurrent(ReadADC(fADCRead1,1));
}

float TDAQBoard::ReadOutputI() {
    return ADCToCurrent(ReadADC(fADCRead2,0));
}

float TDAQBoard::ReadAnalogI() {
    return ADCToCurrent(ReadADC(fADCRead2,1));
}

float TDAQBoard::GetTemperature() {
    uint32_t Reading = ReadADC(fADCRead0,0);
    //printf("NTC ADC: 0x%08X\n",Reading);
    return ADCToTemperature (Reading);
}


float TDAQBoard::ADCToTemperature (int AValue) {
    float    Temperature, R;
    float    AVDD = 1.8;
    float    R2   = 5100;
    float    B    = 3900;
    float    T0   = 273.15 + 25;
    float    R0   = 10000;

    float Voltage = (float) AValue;
    Voltage       *= 3.3;
    Voltage       /= (1.8 * 4096);

    R           = (AVDD/Voltage) * R2 - R2;   // Voltage divider between NTC and R2
    Temperature = B / (log (R/R0) + B/T0);

    return Temperature;
}


float TDAQBoard::ADCToCurrent (int AValue)
{
    float Result = (float) AValue * 3.3 / 4096.;   // reference voltage 3.3 V, full range 4096
    Result /= 0.1;    // 0.1 Ohm resistor
    Result *= 10;     // / 100 (gain) * 1000 (conversion to mA);
    return Result;
}


int TDAQBoard::CurrentToADC (int ACurrent)
{
    float Result = (float) ACurrent / 100. * 4096. / 3.3;
    //std::cout << "Current to ADC, Result = " << Result << std::endl;
    return (int) Result;
}


bool TDAQBoard::ResetBoardFPGA (int ADuration)
{
    bool err;
    err = WriteRegister(MODULE_SOFTRESET, SOFTRESET_DURATION, ADuration);
    if (!err) return false;
    return WriteRegister(MODULE_SOFTRESET, SOFTRESET_FPGA_RESET, 13);
}

bool TDAQBoard::ResetBoardFX3 (int ADuration)
{
    bool err;
    err = WriteRegister(MODULE_SOFTRESET, SOFTRESET_DURATION, ADuration);
    if (!err) return false;
    return WriteRegister(MODULE_SOFTRESET, SOFTRESET_FX3_RESET, 13);
}


void TDAQBoard::DecodeADCData (unsigned char *data_buf, TADCData &ADCData) {
    int Data[6];
    for (int i = 0; i < 6; i++) {
        Data[i] = GetIntFromBinaryStringReversed(4, data_buf + i*4);
    }
    ADCData.TimeStamp  = ((uint64_t) Data[1] & 0xffffff) | ( ((uint64_t) Data[2] & 0xffffff) << 24 );

    ADCData.LDOOn      = (bool) (Data[0] & 0x40);

    ADCData.Temp   = ADCToTemperature(Data[3] & 0x000fff);  //  Temperature
    ADCData.MonV   = (Data[3] & 0xfff000) >> 12;  //  MonV
    ADCData.MonI   = Data[4] & 0x000fff;  //  MonI
    ADCData.IDig   = ADCToCurrent((Data[4] & 0xfff000) >> 12);  //  I Digital
    ADCData.IDigIO = ADCToCurrent(Data[5] & 0x000fff);  //  I DigIO
    ADCData.IAna   = ADCToCurrent((Data[5] & 0xfff000) >> 12);  //  I I Analog
}
