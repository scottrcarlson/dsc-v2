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
from message import Message
from config import Config
from crypto import Crypto
import subprocess

version = ""
isRunning = True            #Main Thread Control Bit

radio = None
yubikey = None
display = None
ui = None

def signal_handler(signal, frame): #nicely shut things down
    print "[ " + str(signal) + " ] DSC2 received shutdown signal."
    print "Exiting DSCv2..."
    radio.stop()
    #gps.stop()
    ui.stop()
    message.stop()
    display.stop()
    global isRunning
    isRunning = False

def get_hg_rev():
    pipe = subprocess.Popen(
        ["hg", "log", "-l", "1", "--template", "{rev}", '/home/dsc/dsc2'], # node is also available
        stdout=subprocess.PIPE
        )
    return pipe.stdout.read()

if __name__ == "__main__":
    print '+----------------------------+'
    print "+ Dirt Simple Comms 2 " + version + ' +'
    print '+----------------------------+'

    for sig in (signal.SIGABRT, signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, signal_handler)

    version = "r" + get_hg_rev()
    iodef.init()

    config = Config()
    crypto = Crypto(config)

    message = Message(crypto, config)
    message.start()

    radio = Radio("/dev/serial0",config, message)
    radio.start()

    #add some logic here to spawn if we have GPS unit
    #gps = Gps()
    #gps.start()

    display = Display(message, version, config)
    display.start()

    ui = UI(display,message, crypto, config)
    ui.start()

    while isRunning:
        sleep(1)
