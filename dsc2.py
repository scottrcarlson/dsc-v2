#!/usr/bin/python
# --------------------------------------- 
# --- Dirt Simple Comms DSC2 MAIN Thread
#----------------------------------------
import signal 
import time
from time import sleep 
from radio import Radio
from yubikey import Yubikey
from display import Display
from ui import UI
from gps import Gps
import iodef
import globals
from message import Message

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
    message.stop()
    global isRunning
    isRunning = False
    print "Exiting DSCv2..."
    sleep(2)
            
if __name__ == "__main__":
    print '+----------------------------+'
    print "+ Dirt Simple Comms 2 " + version + ' +'
    print '+----------------------------+'
        
    for sig in (signal.SIGABRT, signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, signal_handler)


    globals = globals.Globals()
    iodef.init()

    message = Message(globals)
    message.start()

    radio = Radio("/dev/serial0",globals, message)    
    radio.start()

    #Spawn if we have GPS unit
    #gps = Gps()
    #gps.start()

    ui = UI(message)
    ui.start()    

    while isRunning:
        sleep(1)
