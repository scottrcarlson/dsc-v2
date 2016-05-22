#!/usr/bin/python
# --------------------------------------- 
# --- Dirt Simple Comms DSC2 MAIN Thread
#----------------------------------------
import signal 
from time import sleep 
from radio import Radio
from yubikey import Yubikey
import iodef
from display import Display
from ui import UI
from gps import Gps

version = "v0.1.1" 
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

    iodef.init()

    radio = Radio("/dev/serial0",0)    
    radio.start()

    #gps = Gps()
    #gps.start()

    ui = UI()
    ui.start()    

    while isRunning:
        sleep(1)
