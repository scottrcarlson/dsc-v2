#!/usr/bin/env python

from threading import *

class Message(Thread):
    def __init__(self, globals):
        Thread.__init__(self)
        self.event = Event()

        self.globals = globals
        print "Initialized Message Thread."
    
    def run(self):
        self.event.wait(1)
        while not self.event.is_set():
            self.event.wait(1)

    def stop(self):
        print "Stopping Message Thread."
        self.event.set()

    def new_composed_msg(self, msg):
        print "Processing new message."
        #Encrypt / Sign and add to the list
        self.globals.repeat_msg_list.append(msg)

    def msg_received_from_radio(self,msg):
        #lots of things to do here...
        if not self.check_for_dup(msg):
            self.globals.repeat_msg_list.append(msg)
            print "New Unique Message Received via Radio."
        else:
            print "Duplicate Message Received via Radio. Dropped"
        

    def check_for_dup(self,msg):
        #Check for duplicates in the repeat msg list, every encrypted msg is unique, no dups allowed!
        for m in self.globals.repeat_msg_list:
            if msg == m:
                return True
        return False
        
