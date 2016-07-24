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

    def stop(self):
        print "Stopping Message Thread."
        self.event.set()

    def new_composed_msg(self, msg):
        print "Processing new message."
        #Encrypt / Sign and add to the list
        self.globals.repeat_msg_list.append(msg)

