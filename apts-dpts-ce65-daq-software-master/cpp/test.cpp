//
//  main.cpp
//
//  Created by Mauro Aresti and Carlo Puggioni on 10/06/2021.
//  Copyright (c) 2021 Mauro Aresti and Carlo Puggioni. All rights reserved.

#include <iostream>
#include <libusb-1.0/libusb.h>
#include "USB.h"
#include "TDaqboard.h"
#include "TTestsetup.h"
#include "stdio.h"
#include <stdio.h>      /* printf */
#include <time.h>       /* time_t, struct tm, time, localtime, asctime */
#include <unistd.h>
#include <stdlib.h>
#include <cstring>
#include <signal.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <sys/stat.h>
#include <string>
#include <math.h>

#define RESET   "\033[0m"
#define BLACK   "\033[1;30m"
#define RED     "\033[1;31m"
#define GREEN   "\033[1;32m"
#define YELLOW  "\033[0;33m"
#define BLUE    "\033[1;34m"
#define MAGENTA "\033[1;35m"
#define CYAN    "\033[1;36m"
#define WHITE   "\033[1;37m"

using namespace std;

// Catch CTRL-C Signal
static bool SigInt = false;

void ReceivedSignal(int sig){
  printf(RED);
  printf("\nReceived CTRL-C signal!\nStop Running\n");
  printf(RESET);
  
  SigInt=true;
  return;
}

struct sigaction act;

//#define IREF0 4000
//#define IREF1 4000
//#define IREF2 4000

// Global Variables
//--------------------------------------------------------------------------------------------- 

TTestSetup *fTS = new TTestSetup ();     // Object Test Setup

int  myArgc;
char myArgv[11][50];
int  maxArgs = 10;

//Endpoints
static const int ENDPOINT_READ_ADC  =2; // 2 
static const int ENDPOINT_READ_DATA =3; // 3

// Schema Instruction Word
static const int SIZE_WORD        = 4; // byte

// Functions
	
//
//---------------------------------------------------------------------------------------------    
int CreateTestSetup(){
    std::cout << "Creating test setup " << std::endl;
    std::cout << "Searching for DAQ boards " << std::endl;
    fTS->FindDAQBoards();
    std::cout << "Found " << fTS->GetNDAQBoards() << " DAQ boards." << std::endl;
    return fTS->GetNDAQBoards();
    }  
//
//---------------------------------------------------------------------------------------------
void printUsage() {
    std::cout << "Start program with one of the following options, parameters in [] optional: " << std::endl << std::endl;
    std::cout << "FIRMWARE		- Read Firmware version" << std::endl;
    std::cout << "WRITEADC1REG	- Write ADC1 Register [ADDRESS,VALUE]" << std::endl; 
    std::cout << "WRITEREG		- Write FPGA Register [MODULE,ADDRESS,VALUE] Hexadecimal format" << std::endl;
    std::cout << "READREG		- Read FPGA Register [MODULE,ADDRESS]" << std::endl;
    std::cout << "READOUT_CE65		- Start Readout [MODULE,ADDRESS,VALUE,SOURCE[ADC/CHIP], MAX LENGTH(Word)]" << std::endl;
    std::cout << "READOUT_APTS		- Start Readout [MODULE,ADDRESS,VALUE,SOURCE[ADC/CHIP], MAX LENGTH(Word)]" << std::endl;
    std::cout << "READOUT_DPTS		- Start Readout [MODULE,ADDRESS,VALUE,SOURCE[ADC/CHIP], MAX LENGTH(Word)]" << std::endl;
    std::cout << std::endl;
}
//
//---------------------------------------------------------------------------------------------  
void ReadReg(int module, int addr_reg){
    uint32_t value=fTS->GetDAQBoard(0)->ReadRegister(module,addr_reg); 
     std::cout  << "Read Register: Module " << std::dec << module << std::hex << " Register " << addr_reg   << " Value " << value << std::endl;
    }
//
//--------------------------------------------------------------------------------------------
void WriteReg(int module, int addr_reg, int value){
    fTS->GetDAQBoard(0)->WriteRegister(module,addr_reg,value); 
     std::cout  << "Write Register: Module " << std::dec << module << std::hex << " Register " << addr_reg   << " Value " << value << std::endl;
    }
//
//---------------------------------------------------------------------------------------------  
void ReadFPGAFirmware(){
     uint32_t value=fTS->GetDAQBoard(0)->ReadRegister(6,2); 
     std::cout  << "FIRMWARE: " << std::hex << " Value " << value << std::endl;
    }

//CE65 READOUT
//---------------------------------------------------------------------------------------------  
void StartReadoutCE65(int module, int addr_reg, int value, char * source, int maxLength){
  // catch CTRL-Z signal  
  act.sa_handler = ReceivedSignal;
  sigaction(SIGINT,&act,NULL); // ^C SIGINT ^\ SIGTSTP ^Z SIGQUIT 
 
  maxLength = maxLength*SIZE_WORD;
  unsigned char data_buf[maxLength];
  unsigned char data_word[4]; // HEX data
  int data_out; // data out 16 bit per word
  bool DBG= false; // print DEBUG info 
  bool WRT= true; // WRITE file data
  bool STP_ACQ = false; // control acquisition 

  int PixelNum=2048; 
  int FrameNum = 15; // total frame 
  
  char strcmd[80]; //="gawk -f ./prntdt.awk Data/210727_14_CE65.csv" 

  char strtimeframe[20]; // timestamp frame
  
  char strtime[30]; // outfile name
  time_t now = time(NULL); // time stamp
  strftime(strtime, 30, "../Data/%y%m%d_%H%M_CE65.csv", localtime(&now));
  FILE *outfile = fopen(strtime,"w");
  
  long int tot_byte = 0; 


   printf("\n----------------------------{ CE65 DAC setting Start }--------------------\n");

   float V_REF = 2.50; // internal reference measured on the board
   // some command register for DACs U28 U29
   unsigned int CHN_CMD = 0b0011; 
   unsigned int REF_CMD = 0b1000;
   unsigned int CHN_ADD[8] = { 0b0000,
			       0b0001,
			       0b0010,
			       0b0011,
			       0b0100,
			       0b0101,
			       0b0110,
			       0b0111 };
   unsigned int command = 0; // command for DACs
   
   command = ( 0x0 << (32-4)) + (REF_CMD << (32-8)) + (0x0 << (32-12)) + 1; //compose command 

   fTS->GetDAQBoard(0)->WriteRegister(4, stoul("0x01",0,16), command);// DAC U28 Vref internal 2.5 Volts
   usleep(100);
   fTS->GetDAQBoard(0)->WriteRegister(5, stoul("0x01",0,16), command);// DAC U29 Vref internal 2.5 Volts
   usleep(100);
   
   float U28_DAC[8] = {0.0, 0.2, 0.4, 0.6, 0.7, 0.8, 0.9, 1.0}; // V_out for DAC U28 channel A-H
   for(int i=0;i<8;i++)
     {
       unsigned int V_DAC_Step = (unsigned int) pow(2,16)*U28_DAC[i]/(2.0*V_REF) ; // V_out Step
       command = (0x0 << (32-4)) + (CHN_CMD << (32-8)) + (CHN_ADD[i] << (32-12)) + (V_DAC_Step << (32-28) );
       fTS->GetDAQBoard(0)->WriteRegister(4, stoul("0x01",0,16), command);// set DAC channel 
       usleep(100);
     }

   float U29_DAC[8] = {0.0, 0.2, 0.4, 0.6, 0.7, 0.8, 0.9, 1.0}; // V_out for DAC U29 channel A-H
   for(int i=0;i<8;i++)
     {
       unsigned int V_DAC_Step = (unsigned int) pow(2,16)*U28_DAC[i]/(2.0*V_REF) ; // V_out Step
       command = (0x0 << (32-4)) + (CHN_CMD << (32-8)) + (CHN_ADD[i] << (32-12)) + (V_DAC_Step << (32-28) );
       fTS->GetDAQBoard(0)->WriteRegister(5, stoul("0x01",0,16), command);// set DAC channel 
       usleep(100);
     }

  printf("\n----------------------------{ CE65 DAC setting End}--------------------\n");
  
  printf("\n----------------------------{ CE65 setting Start }--------------------\n");
  
  fTS->GetDAQBoard(0)->DumpDeviceInfo();
  
  fTS->GetDAQBoard(0)->WriteRegister(10, stoul("0x00",0,16), PixelNum);// Set number of pixels
  usleep(100);
  fTS->GetDAQBoard(0)->WriteRegister(2, stoul("0x00",0,16), 1);// Frame before Trigger max 31
  usleep(100);
  fTS->GetDAQBoard(0)->WriteRegister(10, stoul("0xFA",0,16), FrameNum);// Frame after Trigger  
  usleep(100);
  fTS->GetDAQBoard(0)->WriteRegister(2, stoul("0x01",0,16), 1);// 1 packed end active  0 packed end not active 
  usleep(100);
  fTS->GetDAQBoard(0)->WriteRegister(2, stoul("0x87",0,16), 1);// 1 test data pattern  0 actual data from CE65 chip
  usleep(100);
  fTS->GetDAQBoard(0)->WriteRegister(module, addr_reg, value); // value = 0 Trigger Acq, value == 1 Continue Acq
  usleep(100);
  fTS->GetDAQBoard(0)->WriteRegister(10, stoul("0xAC",0,16), 1);// Start Acq
  usleep(100);
  if (DBG) printf("[%d %lx %d] Start Acq\n\n",10, stoul("0xAC",0,16), 1);
 
   printf("\n----------------------------{ CE65 setting End}--------------------\n");
  
 if (DBG) printf("-------------------------------------------------------------\n\n\n\n\n\n");

 //=========================== TRIGGER LOOP =======================================
 int trig_num = 0;
 int good_value = 0;
 int good_lenght = 2056; // 4014 for 2048 pixels
 int ii = 0;
 int c =0;
 int framenum = 0;
 
 while(!SigInt  && (trig_num <= FrameNum )) // loop  
{  
 long length = 0;
 int count = 0;

  if (STP_ACQ)
    {
    fTS->GetDAQBoard(0)->WriteRegister(10, stoul("0xAC",0,16), 1);   // Start Acq
    STP_ACQ=false;
    printf("\n================================= New Acquisition ================================\n"); 
    }

  length = fTS->GetDAQBoard(0)->ReceiveData(ENDPOINT_READ_DATA, data_buf, maxLength);

  
  if(trig_num == 0) printf("\n Trigger Detected!\n================================= Start Acquisition ================================ \n\n"); 

  
  if(length <= 0)
    {
    printf("metod ReceiveData ERROR!!!");
    }
  else //else 1
    {
    trig_num++;
    if(length == 65536) good_value++;
    printf(GREEN);
    int k = 2*PixelNum+8;
   
    
    for (int i=0; i< length; i++) // for i #1
      {
	
	//time_t now = time(NULL); // time stamp
	//strftime(strtimeframe, 30, "%Y-%m-%d %H:%M:%S", localtime(&now));
	tot_byte++;
	
	
	if ( WRT && (i>0)  && ((i+1)%2 == 0) ) fprintf(outfile,"%02X%02X ",data_buf[i],data_buf[i-1]);

	if( (i>1) & (data_buf[i-1] == 0xAE ) & (data_buf[i] == 0xAE) & (!value))
	  {
	    printf(RESET);
	    printf("\n================================= Stop Acquisition ================================= \n Detected Word: 0xAEAE\n\n");
	    STP_ACQ = true;	
	    break;
	  }
       
	ii++;
	
	if ( (ii)%4104 == 0 ) printf("frame: %d\n",ii/4104);
	if (WRT && ( (ii)%4104 == 0) ) fprintf(outfile,"\n------------------------ %5d -------------------------------------\n",ii/4104);
      }// for i #1

    printf("============= Received: %ld bytes per frame, Total bytes: %ld =============\n",length, tot_byte);
    
    printf(RESET);
    
      if(SigInt){ //trig_num == 100 )  { //
	printf("\nStop ACQ!\n");
	fclose(outfile);
	exit(1);
      }

    } // else 1

} // while(1)

 if (false)
   {
     if (value == 1) fTS->GetDAQBoard(0)->WriteRegister(10, stoul("0xAC",0,16), 0);
     else if (value == 0) printf("END");
     
     int l=0,m=0;
     printf("\n[");
     while( (l=fTS->GetDAQBoard(0)->ReceiveData(ENDPOINT_READ_DATA, data_buf, maxLength)) > 0 )
       {
	 printf("%d-%d ... ",m++,l);
       }
     printf("]\n");
   }
 /*
	fflush(outfile);
	usleep(100);
	fclose(outfile);
 */
 printf(WHITE);
 printf("\n Data file saved: %s \n\n",strtime);
 fflush(outfile);
 fclose(outfile);
 
 sprintf(strcmd,"gawk -f ../prntdt.awk %s ",strtime);
 system(strcmd);
 printf("\n");
 //system("cat ../Data/200220_20_CE65.csv");
 //system("cmatrix");
 printf(RESET);
}

//APTS READOUT
//---------------------------------------------------------------------------------------------  
void StartReadoutAPTS(int module, int addr_reg, int value, char * source, int maxLength){
  maxLength = maxLength*SIZE_WORD;
  unsigned char data_buf[maxLength];
  unsigned char data_word[4]; // HEX data
  int data_out; 
  bool DBG= false; // print DEBUG info 
  bool WRT= true; // WRITE file data
  
  char strtime[30]; // outfile name
  time_t now = time(NULL); // time stamp
  strftime(strtime, 30, "../../Data/%y%m%d_%H_APTS.csv", localtime(&now));
  FILE *outfile = fopen(strtime,"a");

  //printf("\n--------------------{APTS}--------------------\n");
  
  fTS->GetDAQBoard(0)->DumpDeviceInfo();
  fTS->GetDAQBoard(0)->WriteRegister(module, addr_reg, value);   // call function
  if (DBG) printf("------------------------------------\n");
  if (DBG) printf("+=======================================+\n");
  if (DBG) printf("| Module: %02d AddrReg: %03d (%02X) Value: %d |\n",module,addr_reg,addr_reg,value);
  if (DBG) printf("+=======================================+\n");
  usleep(100);
  if (DBG) printf("------------------------------------\n\n\n\n\n\n");

  int addr = 0;
  int length=0;
  int count=-2; // number of word
  long long int count_matrix = 1; // number of sample (Matrix)
  int count_word = 0;
  
  if (strcmp (source, "CHIP") == 0) length = fTS->GetDAQBoard(0)->ReceiveData(ENDPOINT_READ_DATA, data_buf, maxLength);
  else if (strcmp (source, "ADC") == 0) length = fTS->GetDAQBoard(0)->ReceiveData(ENDPOINT_READ_ADC, data_buf, maxLength);
  else printUsage();

  if (DBG) std::cout << "Received " << length << " bytes." <<std::endl;

  if(length <= 0){
    printf("metod ReceiveData ERROR!!!");
  }
  else{
	
    long long ts1=0.0;
    long long ts2=0.0;
    long long ts3=0.0;
    long long eve=0.0;

    printf("\n\n\n{+} APTS \n");
    
    for (int i=0; i< length; i++){
      //if (DBG) printf("\n--------------------------------------> %d < \n",i);
      //printf("%02X",data_buf[i]);
      //printf("%s",data_buf[i]);
      if ((i+1) % 4 == 0){    
	
	if(i<=length){

	  if (count==-2){ // header:timestamp 48bit (first 24 bit)    		
	    //>0 remove
	    data_word[2]=data_buf[i-2]; // FE07 -> 07FE
	    if (DBG) printf("[%02X",data_word[2]);
	    data_word[3]=data_buf[i-3];
	    if (DBG) printf("%02X | ",data_word[3]);
	    //if (DBG) printf(" %5d | ",(unsigned char)data_word[2]*256+(unsigned char)data_word[3]);
	    data_word[0]=data_buf[i-0];
	    if (DBG) printf("%02X",data_word[0]);
	    data_word[1]=data_buf[i-1];
	    if (DBG) printf("%02X ]",data_word[1]);
	    //if (DBG)printf(" %5d]",(unsigned char)data_word[0]*256+(unsigned char)data_word[1]);
	    if(DBG) printf(" { %02X %02X %02X %02X } ",data_word[0],data_word[1],
			   data_word[2],data_word[3]);		
	    ts1 = (unsigned char)data_word[0]*pow(2,40)+ (unsigned char)data_word[1]*pow(2,32);
	    ts2 = (unsigned char)data_word[2]*pow(2,24)+ (unsigned char)data_word[3]*pow(2,16);
	    if (DBG) printf("\n-------------------------->>> %021lld <<< ts first 16 bit\n",ts1);
	    if (DBG) printf("\n-------------------------->>> %021lld <<< ts last  16 bit\n",ts2);
	    if (DBG) printf("\n-------------------------->>> %021lld <<< ts first 24 bit\n",ts1+ts2);
	    //>0
	    count++;
	    count_word++;
	    //printf(" (%d) ",count);
	  }
	  else if (count==-1){ // header:timestamp 48bit (last 24 bit)    
		
	    //>1 remove
	    data_word[2]=data_buf[i-2]; // FE07 -> 07FE
	    if (DBG) printf("[%02X",data_word[2]);
	    data_word[3]=data_buf[i-3];
	    if (DBG) printf("%02X | ",data_word[3]);
	    //if (DBG) printf(" %5d | ",(unsigned char)data_word[2]*256 + (unsigned char)data_word[3]);
	    data_word[0]=data_buf[i-0];
	    if (DBG) printf("%02X",data_word[0]);
	    data_word[1]=data_buf[i-1];
	    if (DBG) printf("%02X ]",data_word[1]);
	    //if (DBG) printf(" %5d]",(unsigned char)data_word[0]*256+(unsigned char)data_word[1]);
	     if(DBG) printf(" { %02X %02X %02X %02X } ",data_word[0],data_word[1],
			    data_word[2],data_word[3]);
	    ts3 = (unsigned char)data_word[2]*pow(2,8)+ (unsigned char)data_word[3];
	    eve = (unsigned char)data_word[0]*pow(2,8) + (unsigned char)data_word[1];
	    if (DBG) printf("\n-------------------- ------>>> %021lld <<< ts last 16 bit\n",ts3);
	    if (DBG) printf("\n-------------------------->>> %021lld <<< ts 48 bit\n",ts1+ts2+ts3);
	    if (DBG) printf("\n-------------------------->>> %021lld <<< eve 16 bit\n",eve);
	    //>1
	    count++;
	    count_word++;
	    //printf(" (%d) ",count);
	    if (WRT) fprintf(outfile,"%021lld,%021lld,",ts1+ts2+ts3,eve);
	    if (WRT) fprintf(outfile,"%021lld",count_matrix);
	    
	    printf("======================================\n");
	    printf("Time   Stamp : %021lld | \n",ts1+ts2+ts3);
	    printf("Matrix Number: %021lld | \n",count_matrix);
	    printf("Event  Number: %021lld | \n",eve);
	    printf("======================================\n");
	    printf("[ HEX  |  HEX ] (word)               |\n");
	    printf("{=====================================\n");
	  }
	      
	  else {
	    
	    data_word[2]=data_buf[i-2]; // FE07 -> 07FE
	    printf("[ %02X",data_word[2]);
	    
	    data_word[3]=data_buf[i-3];
	    printf("%02X | ",data_word[3]);

	    //printf(" %5d | ",(unsigned char)data_word[2]*256+ (unsigned char)data_word[3]);
	    
	    if (WRT) fprintf(outfile,",%02X%02X",data_word[2],data_word[3]);
	    
	    data_word[0]=data_buf[i-0];
	    printf("%02X",data_word[0]);
	   
	    data_word[1]=data_buf[i-1];
	    printf("%02X ]",data_word[1]);

	    if(DBG) printf(" { %02X %02X %02X %02X } ",data_word[0],data_word[1],data_word[2],data_word[3]);
	    
	    //printf(" %5d ]",(unsigned char)data_word[0]*256+(unsigned char)data_word[1]);
	    
	    if (WRT) fprintf(outfile,",%02X%02X",data_word[0],data_word[1]);   
	    
	    //data_out = (unsigned char) strtoul(data_word, NULL, 16);
	    //printf("(%s)",data_word);

	    // Matrix 4x4 pixels (8 words) + 2 words of Header + 1 word of trailer    
	    if (count == 8) {
	      count = -2; // reset word number 
	      count_matrix++; // increment number of sample / matrix
	      count_word++;
	      
	      printf("\n}=====================================\n");
	      if (WRT) fprintf(outfile,"\n");
	      //printf("\n----------------------------------",count);
	    }
	    else {
	      printf("  (%d)\n",count);
	      count++;
	      count_word++;
	     
	    }
	}
       }
      }
      //if ((i+1) % 4 == 0) printf("\n");
      //if ((i+1) % 4*4 == 0) printf("------------------------------------\n");
      
      if(i+1 == length){
	//printf("====================================\n");
	//printf("[ HEX  |  HEX ] (word)              |\n");
	//printf("=====================================");
      }
    }
    
    printf ("\n Number of word requests: %d \n Number of word received: %d\n",
	    maxLength/4 ,count_word);
    printf("{-}\n");
    printf("%lld\n",count_matrix-1);
    //if (WRT) fprintf(outfile,"\n");
  }
  fflush(outfile);
  usleep(100);
  fclose(outfile);
}

//DPTS READOUT
//---------------------------------------------------------------------------------------------  
void StartReadoutDPTS(int module, int addr_reg, int value, char * source, int maxLength){
  maxLength = maxLength*SIZE_WORD;
  unsigned char data_buf[maxLength];
  unsigned char data_word[4]; // HEX data
  int data_out; 
  bool DBG= true; // print DEBUG info 
  bool WRT= true; // WRITE file data
  
  char strtime[30]; // outfile name
  time_t now = time(NULL); // time stamp
  strftime(strtime, 30, "../../Data/%y%m%d_%H_DPTS.csv", localtime(&now));
  FILE *outfile = fopen(strtime,"a");

  fTS->GetDAQBoard(0)->DumpDeviceInfo();
  fTS->GetDAQBoard(0)->WriteRegister(module, addr_reg, value);   // call function 
  
  // printf("===================================");
  usleep(100);
  if (DBG) printf("------------------------------------\n\n\n\n\n\n");

  int addr = 0;
  int length=0;
  int count=-2; // number of word  
  if (strcmp (source, "CHIP") == 0) length = fTS->GetDAQBoard(0)->ReceiveData(ENDPOINT_READ_DATA, data_buf, maxLength);
  else if (strcmp (source, "ADC") == 0) length = fTS->GetDAQBoard(0)->ReceiveData(ENDPOINT_READ_ADC, data_buf, maxLength);
  else printUsage();

  if (DBG) std::cout << "Received " << length << " bytes." <<std::endl;

  if(length <= 0){
    printf("metod ReceiveData ERROR!!!");
  }
  else{ // main loop 
	
    long long ts1=0.0;
    long long ts2=0.0;
    long long ts3=0.0;
    long long eve=0.0;
	
    for (int i=0; i< length; i++){ // main loop on data received 
      //printf("%02X",data_buf[i]);
      //printf("%s",data_buf[i]);
      if ((i+1) % 4 == 0){    
	
	if(i<=length){

	  if (count==-2){ // header:timestamp 48bit (first 24 bit)    		
	    //>0 remove
	    data_word[2]=data_buf[i-2]; // FE07 -> 07FE
	    if (DBG) printf("[%02X",data_word[2]);
	    data_word[3]=data_buf[i-3];
	    if (DBG) printf("%02X",data_word[3]);
	    if (DBG) printf(" %5d | ",(unsigned char)data_word[2]*256+(unsigned char)data_word[3]);
	    data_word[0]=data_buf[i-0];
	    if (DBG) printf("%02X",data_word[0]);
	    data_word[1]=data_buf[i-1];
	    if (DBG) printf("%02X",data_word[1]);
	    if (DBG)printf(" %5d]",(unsigned char)data_word[0]*256+(unsigned char)data_word[1]);
		
	    ts1 = (unsigned char)data_word[2]*pow(2,40)+ (unsigned char)data_word[3]*pow(2,32);
	    ts2 = (unsigned char)data_word[0]*pow(2,24)+ (unsigned char)data_word[1]*pow(2,16);
	    if (DBG) printf("\n-------------------------->>> %021lld <<< ts first 16 bit\n",ts1);
	    if (DBG) printf("\n-------------------------->>> %021lld <<< ts last  16 bit\n",ts2);
	    if (DBG) printf("\n-------------------------->>> %021lld <<< ts first 24 bit\n",ts1+ts2);
	    //>0
	    count++;
	   
	    //printf(" (%d) ",count);
	  }
	  else if (count==-1){ // header:timestamp 48bit (last 24 bit) + event number (16 bit)    
		
	    //>1 remove
	    data_word[2]=data_buf[i-2]; // FE07 -> 07FE
	    if (DBG) printf("[%02X",data_word[2]);
	    data_word[3]=data_buf[i-3];
	    if (DBG) printf("%02X",data_word[3]);
	    if (DBG) printf(" %5d | ",(unsigned char)data_word[2]*256 + (unsigned char)data_word[3]);
	    data_word[0]=data_buf[i-0];
	    if (DBG) printf("%02X",data_word[0]);
	    data_word[1]=data_buf[i-1];
	    if (DBG) printf("%02X",data_word[1]);
	    if (DBG) printf(" %5d]",(unsigned char)data_word[0]*256+(unsigned char)data_word[1]);

	    ts3 = (unsigned char)data_word[2]*pow(2,8)+ (unsigned char)data_word[3];
	    eve = (unsigned char)data_word[0]*pow(2,8) + (unsigned char)data_word[1];
	    if (DBG) printf("\n-------------------------->>> %021lld <<< ts last 16 bit\n",ts3);
	    if (DBG) printf("\n-------------------------->>> %021lld <<< ts 48 bit\n",ts1+ts2+ts3);
	    if (DBG) printf("\n-------------------------->>> %021lld <<< eve 16 bit\n",eve);
	    //>1
	    count++;
	    
	    //printf(" (%d) ",count);
	    if (WRT) fprintf(outfile,"%021lld,%021lld",ts1+ts2+ts3,eve);
	    printf("{+} DPTS\n");
	    printf("=====================================\n");
	    printf("Time  Stamp : %021lld | \n",ts1+ts2+ts3);
	    printf("Event Number: %021lld | \n",eve);
	    printf("=====================================\n");
	    printf("[ HEX    DEC | HEX    DEC ]  (word) |\n");
	    printf("{====================================");
	  }
	      
	  else{
	    
	    data_word[2]=data_buf[i-2]; // FE07 -> 07FE
	    printf("[ %02X",data_word[2]);
	    
	    data_word[3]=data_buf[i-3];
	    printf("%02X",data_word[3]);

	    printf(" %5d | ",(unsigned char)data_word[2]*256+
		   (unsigned char)data_word[3]);
	    
	    if (WRT) fprintf(outfile,",%02X%02X",data_word[2],data_word[3]);
	    
	    data_word[0]=data_buf[i-0];
	    printf("%02X",data_word[0]);
	   
	    data_word[1]=data_buf[i-1];
	    printf("%02X",data_word[1]);
	    printf(" %5d ]",(unsigned char)data_word[0]*256+
		   (unsigned char)data_word[1]);
	    
	    if (WRT) fprintf(outfile,",%02X%02X",data_word[0],data_word[1]);   
	    
	    //data_out = (unsigned char) strtoul(data_word, NULL, 16);
	    //printf("(%s)",data_word);
	    count++;
	    printf("  (%d) ",count);
	  }
	}
	
      }
      if ((i+1) % 4 == 0) printf("\n");
      
      if(i+1 == length){
	printf("}====================================\n");
	printf("[ HEX    DEC | HEX    DEC ]  (word) |\n");
	printf("=====================================");
      }
    }
    
    printf ("\n Number of word requests: %d \n Number of word received: %d\n",maxLength/4 ,count);
    printf("{-}\n");
    if (WRT) fprintf(outfile,"\n");
  }
  fflush(outfile);
  usleep(100);
  fclose(outfile);
}


//
//---------------------------------------------------------------------------------------------
void DoTheTest() {
    if (strcmp (myArgv[0], "FIRMWARE") == 0) {
         if (myArgc == 1)ReadFPGAFirmware();
         else printUsage();
    }
    else if (strcmp (myArgv[0], "WRITEADC1REG") == 0) {
         if (myArgc == 3) fTS->GetDAQBoard(0)->WriteRegister(1, atoi(myArgv[1]), atoi(myArgv[2]));
         else printUsage();
    }
    else if (strcmp (myArgv[0], "WRITEREG") == 0) {
    	 std::string modulo (myArgv[1]);
    	 std::string indirizzo (myArgv[2]);
    	 std::string valore (myArgv[3]);
         if (myArgc == 4) fTS->GetDAQBoard(0)->WriteRegister(atoi(myArgv[1]),stoul(indirizzo, 0, 16),stoul(valore, 0, 16));
         else printUsage();
    }
    else if (strcmp (myArgv[0], "READREG") == 0) {
         if (myArgc == 3) ReadReg(atoi(myArgv[1]), atoi(myArgv[2]));
         else printUsage();
    }
    else if (strcmp (myArgv[0], "READOUT_CE65") == 0) {
    	 std::string modulo (myArgv[1]);
    	 std::string indirizzo (myArgv[2]);
    	 std::string valore (myArgv[3]);
         if (myArgc == 6) StartReadoutCE65(atoi(myArgv[1]),stoul(indirizzo, 0, 16),stoul(valore, 0, 16),myArgv[4],atoi(myArgv[5])); //
         else printUsage();     
    }
    else if (strcmp (myArgv[0], "READOUT_APTS") == 0) {
    	 std::string modulo (myArgv[1]);
    	 std::string indirizzo (myArgv[2]);
    	 std::string valore (myArgv[3]);
         if (myArgc == 6) StartReadoutAPTS(atoi(myArgv[1]),stoul(indirizzo, 0, 16),stoul(valore, 0, 10),myArgv[4],atoi(myArgv[5]));
         else printUsage();     
    }
    else if (strcmp (myArgv[0], "READOUT_DPTS") == 0) {
    	 std::string modulo (myArgv[1]);
    	 std::string indirizzo (myArgv[2]);
    	 std::string valore (myArgv[3]);
         if (myArgc == 6) StartReadoutDPTS(atoi(myArgv[1]),stoul(indirizzo, 0, 16),stoul(valore, 0, 16),myArgv[4],atoi(myArgv[5]));
         else printUsage();     
    }
    else printUsage(); 
}
//
//--------------------------------------------------------------------------------------------- 
int main(int argc, const char * argv[])
{
    myArgc = argc - 1;
    for (int i = 0; (i < argc-1) && (i < maxArgs); i ++) {
        sprintf(myArgv[i], "%s", argv[i+1]);
    }
	std::cout << "Start Test " << myArgv[0] << std::endl;
	if (CreateTestSetup() > 0){	
	    if (myArgc > 0) DoTheTest();
	    else printUsage();
	}   
   fTS->cleanExit();
   return 0;
}
