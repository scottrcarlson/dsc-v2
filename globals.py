#!/usr/bin/python
# --------------------------------------- 
# --- Dirt Simple Comms GLobals         
#----------------------------------------

class Globals(object):
    def __init__(self):
        self.transmit_ok = False    # True when TDMA slot is active for this node
        self.beacon_ready = False   # True when new beacon has been generated and is ready for TX
        self.beacon_msg = ""       
        self.repeat_msg_list = ["Hello","Hello2","Hello3"]
        self.repeat_msg_index = 0
        self.radio_verbose = False
        
