import sys
import os
import platform
import time
import ctypes
from array import *
from ctypes import *
from __builtin__ import exit

#Function to get most common result
from collections import Counter
def mostCommon(lst):
    data = Counter(lst)
    return data.most_common(1)[0][0]

# ----------------

#Implement PyBrain Neural Netowks
from pybrain.tools.shortcuts import buildNetwork
from pybrain.datasets import SupervisedDataSet
from pybrain.supervised.trainers import BackpropTrainer

#Network with 5 Inputs, 10 Neurons, and 1 Output
net = buildNetwork(5, 10, 1, bias=True)
#Create Dataset with 5 Values and 1 Output
ds = SupervisedDataSet(5, 1)

# ----------------

#Load Appropriate Libraries
try:
    if sys.platform.startswith('win32'):
        libEDK = cdll.LoadLibrary("../../bin/win32/edk.dll")
    elif sys.platform.startswith('linux'):
        srcDir = os.getcwd()
	if platform.machine().startswith('arm'):
            libPath = srcDir + "/../../bin/armhf/libedk.so"
	else:
            libPath = srcDir + "/../../bin/linux64/libedk.so"
        libEDK = CDLL(libPath)
    else:
        raise Exception('System not supported.')
except Exception as e:
    print 'Error: cannot load EDK lib:', e
    exit()

# ----------------
#EPOC+ Initailizers
IEE_EmoEngineEventCreate = libEDK.IEE_EmoEngineEventCreate
IEE_EmoEngineEventCreate.restype = c_void_p
eEvent = IEE_EmoEngineEventCreate()

IEE_EmoEngineEventGetEmoState = libEDK.IEE_EmoEngineEventGetEmoState
IEE_EmoEngineEventGetEmoState.argtypes = [c_void_p, c_void_p]
IEE_EmoEngineEventGetEmoState.restype = c_int

IEE_EmoStateCreate = libEDK.IEE_EmoStateCreate
IEE_EmoStateCreate.restype = c_void_p
eState = IEE_EmoStateCreate()

userID = c_uint(0)
user   = pointer(userID)
ready  = 0
state  = c_int(0)

alphaValue     = c_double(0)
low_betaValue  = c_double(0)
high_betaValue = c_double(0)
gammaValue     = c_double(0)
thetaValue     = c_double(0)

alpha     = pointer(alphaValue)
low_beta  = pointer(low_betaValue)
high_beta = pointer(high_betaValue)
gamma     = pointer(gammaValue)
theta     = pointer(thetaValue)

channelList = array('I',[3, 7, 9, 12, 16])   # IED_AF3, IED_AF4, IED_T7, IED_T8, IED_Pz 

# ----------------

#Check for System Startup Success
if libEDK.IEE_EngineConnect("Emotiv Systems-5") != 0:
        print "Emotiv Engine start up failed."
        exit();

#Function to Train Dataset
def train(target,timeRemain):
    global ready
    while (timeRemain>0):
        state = libEDK.IEE_EngineGetNextEvent(eEvent)
        
        if state == 0:
            eventType = libEDK.IEE_EmoEngineEventGetType(eEvent)
            libEDK.IEE_EmoEngineEventGetUserId(eEvent, user)
            if eventType == 16:  # libEDK.IEE_Event_enum.IEE_UserAdded
                ready = 1
                libEDK.IEE_FFTSetWindowingType(userID, 1);  # 1: libEDK.IEE_WindowingTypes_enum.IEE_HAMMING
                print "User added"
                            
            if ready == 1:
                for i in channelList: 
                    result = c_int(0)
                    result = libEDK.IEE_GetAverageBandPowers(userID, i, theta, alpha, low_beta, high_beta, gamma)
                    if result == 0:    #EDK_OK
                        ds.addSample((thetaValue.value, alphaValue.value, low_betaValue.value, high_betaValue.value, gammaValue.value), (target,))
                        print"\r"+str(int(timeRemain))+ " second(s) remaining...",
                        timeRemain = timeRemain - 0.5
        elif state != 0x0600:
            print "Internal error in Emotiv Engine ! "
        time.sleep(0.5)

#Print out certain queries over a certain amount of time 
def query(timeRemain):
    global ready
    print("Hmmmm...")
    results = []
    while (timeRemain>0):
        state = libEDK.IEE_EngineGetNextEvent(eEvent)
        
        if state == 0:
            eventType = libEDK.IEE_EmoEngineEventGetType(eEvent)
            libEDK.IEE_EmoEngineEventGetUserId(eEvent, user)
            if eventType == 16:  # libEDK.IEE_Event_enum.IEE_UserAdded
                ready = 1
                libEDK.IEE_FFTSetWindowingType(userID, 1);  # 1: libEDK.IEE_WindowingTypes_enum.IEE_HAMMING
                print "User added"
                            
            if ready == 1:
                for i in channelList: 
                    result = c_int(0)
                    result = libEDK.IEE_GetAverageBandPowers(userID, i, theta, alpha, low_beta, high_beta, gamma)
                    if result == 0:    #EDK_OK
                        val = (net.activate([thetaValue.value, alphaValue.value, low_betaValue.value, high_betaValue.value, gammaValue.value]))
                        results.append(int(round(val)))
                        timeRemain = timeRemain - 0.5
        elif state != 0x0600:
            print "Internal error in Emotiv Engine ! "
        time.sleep(0.5)
    guess = mostCommon(results)
    print("I'm guessing... "+str(guess)+"!")    

#Train Dataset to Network
def trainData():
    print(str(len(ds))+" data points have been entered!")
    trainer = BackpropTrainer(net, ds)
    print("Training with Given Data...")
    trainer.train()
    print("Done!")

#Clears data stored in DataSet
def clearData():
     ds.clear()

#Disconnect Headset
def disconnect():
    libEDK.IEE_EngineDisconnect()
    libEDK.IEE_EmoStateFree(eState)
    libEDK.IEE_EmoEngineEventFree(eEvent)

# ----------------
