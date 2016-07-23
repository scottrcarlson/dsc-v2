#!/usr/bin/python
# --------------------------------------- 
# --- Dirt Simple Comms DSC2 MAIN Thread
#----------------------------------------
import signal 
import time
from time import sleep 
from radio import Radio
from yubikey import Yubikey
import iodef
import globals
from display import Display
from ui import UI
from gps import Gps

version = "v0.2.0" 
isRunning = True            #Main Thread Control Bit 

radio = None
yubikey = None
display = None
ui = None

def signal_handler(signal, frame): #nicely shut things down
    print "[ " + str(signal) + " ] DSC2 received shutdown signal."
    radio.stop()
    #gps.stop()
    ui.stop()
    global isRunning
    isRunning = False
    print "Shutting down..."
    sleep(2)
            
if __name__ == "__main__":
    print '+----------------------------+'
    print "+ Dirt Simple Comms 2 " + version + ' +'
    print '+----------------------------+'
        
    for sig in (signal.SIGABRT, signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, signal_handler)


    globals = globals.Globals()
    iodef.init()

    radio = Radio("/dev/serial0",globals)    
    radio.start()

    #Spawn if we have GPS unit
    #gps = Gps()
    #gps.start()

    ui = UI()
    ui.start()    

    tx_time = 4
    tx_deadband = 1

    slot = 0
    total_slots = 3
    slot_width = tx_time + tx_deadband
    tdma_frame_width = slot_width * total_slots
    
    while isRunning:
        
        epoch = time.time()
        tdma_frames_since_epoch = int(epoch / tdma_frame_width)        
        #print "EPOCH: ", epoch
        #print "TDMA Frame Width: ", tdma_frame_width
        #print "TDMA Frames Since Epoch: ",tdma_frames_since_epoch
        
        slot_start = (slot * slot_width) + (tdma_frame_width * tdma_frames_since_epoch)
        slot_end = slot_start + slot_width

        if (epoch > slot_start and epoch < (slot_end - tx_deadband)):
            print "SLOT: ", slot, " Enable TX"
            globals.transmit_ok = True
        else:
            print "SLOT: ", slot, " Disable TX"
            globals.transmit_ok = False

        print "Transmit OK?: ", globals.transmit_ok

        #Check If Slot 0
        #slot0_start = (0 * slot_width) + (tdma_frame_width * tdma_frames_since_epoch)
        #slot0_end = slot0_start + slot_width
        #print "START Slot0: ", slot0_start, "  END Slot0: ", slot0_end

        #Check If Slot 1
        #slot1_start = (1 * slot_width) + (tdma_frame_width * tdma_frames_since_epoch)
        #slot1_end = slot1_start + slot_width
        #print "START Slot1: ", slot1_start, "  END Slot1: ", slot1_end

        #Check If Slot 2
        #slot2_start = (2 * slot_width) + (tdma_frame_width * tdma_frames_since_epoch)
        #slot2_end = slot2_start + slot_width
        #print "START Slot2: ", slot2_start, "  END Slot2: ", slot2_end
        
        #if (epoch > slot0_start and epoch < (slot0_end - tx_deadband)):
        #    print "Detected SLOT0 Enabled"
        #else:
        #    print "Detected SLOT0 Disabled"        

        #if (epoch > slot1_start and epoch < (slot1_end - tx_deadband)):
        #    print "Detected SLOT1 Enabled"
        #else:
        #    print "Detected SLOT1 Disabled"        

        #if (epoch > slot2_start and epoch < (slot2_end - tx_deadband)):
        #    print "Detected SLOT3 Enabled"
        #else:
        #    print "Detected SLOT3 Disabled"        

        sleep(0.5)
