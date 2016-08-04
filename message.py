#!/usr/bin/env python
import time
from threading import *
import Queue

TEST_MSG = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB123456789012"

class Message(Thread):
    def __init__(self, crypto):
        Thread.__init__(self)
        self.event = Event()

        self.repeat_msg_list = []
        self.repeat_msg_index = 0
        self.repeat_msg_segment = 0

        self.msg_seg_list = []
        self.radio_inbound_queue = Queue.Queue() #Should we set a buffer size??

        self.crypto = crypto
        
        self.compose_msg = ""
        self.compose_to = ""

        print "Initialized Message Thread."
    
    def run(self):
        self.event.wait(1)
        while not self.event.is_set():
            #Check Queued Msgs From Radio
            try:
                msg = self.radio_inbound_queue.get_nowait()
            except Queue.Empty:
                pass
                #print "Radio Inbound Queue Empty!"
            else:
                self.add_msg_to_seg_list(msg)

            self.check_for_complete_msgs()
            self.event.wait(1)

    def stop(self):
        print "Stopping Message Thread."
        self.event.set()

    def is_msg_avail_to_repeat(self):
        if len(self.repeat_msg_list) > 0:
            return True
        else:
            return False

    def get_next_msg_for_repeat(self):
        msg_list_len = len(self.repeat_msg_list)
        if msg_list_len > 0:
            if self.repeat_msg_index >= msg_list_len:
                self.repeat_msg_index = 0
                self.repeat_msg_segment = 0
            if self.repeat_msg_segment == 0:
                outbound_data = self.repeat_msg_list[self.repeat_msg_index][:255]
                self.repeat_msg_segment += 1
            elif self.repeat_msg_segment == 1:
                outbound_data = self.repeat_msg_list[self.repeat_msg_index][255:348]
                outbound_data += self.repeat_msg_list[self.repeat_msg_index][:150]
                self.repeat_msg_segment += 1
            if self.repeat_msg_segment == 2:
                self.repeat_msg_segment = 0
                self.repeat_msg_index += 1

            return outbound_data
        else:
            return ""

    def new_composed_msg(self, msg):
        #Need to enforce hard limit for cleartext
        #19 Bytes for timestamp (can save a few bytes with formatting)
        #214-19=195 msg size limit
        print "Processing new message."
        #Encrypt / Sign and add to the list
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        e_msg = self.crypto.encrypt_msg(msg, '/dscdata/keys/encr_decr_keypair_pub/')
        print "msg len", len(e_msg)
        s_msg = self.crypto.sign_msg(e_msg, self.crypto.keyset_password)
        print "msg len", len(s_msg)
        self.repeat_msg_list.append(s_msg)
        return True # TODO Lets capture keyczar error and report back false

    def add_msg_to_repeat_list(self,msg):
        #lots of things to do here...
        if not self.check_for_dup(msg):
            self.repeat_msg_list.append(msg)
            print "New Unique Message Received via Radio."
            #print msg
        else:
            print "Duplicate Message Received via Radio. Dropped"

    def add_msg_to_seg_list(self,msg):
        #lots of things to do here...
        if not self.check_for_seg_dup(msg):
            self.msg_seg_list.append(msg)
            print "New Unique Seqment Received ."
            #print msg
        else:
            print "Duplicate Segment Received via Radio. Dropped"
            
    def check_for_dup(self,msg):
        #Check for duplicates in the repeat msg list, every encrypted msg is unique, no dups allowed!
        for m in self.repeat_msg_list:
            if msg == m:
                return True
        return False

    def check_for_seg_dup(self,msg):
        #Check for duplicates in the repeat msg list, every encrypted msg is unique, no dups allowed!
        for m in self.msg_seg_list:
            if msg == m:
                return True
        return False
        
    def check_for_complete_msgs(self):
        segf = ""  #Part of Encrypted Packet (Fingerprint?)
        seg_found = False
        seg = ""   #Actual Msg Segment
        
        for mf in self.msg_seg_list:
            if len(mf) == 243:
                segf = mf[93:243]
                print "Found Finger Print."
                print "Searching for remaining segments."
            for m in self.msg_seg_list:
                if len(m) == 255:
                    if m[:150] == segf:
                        seg_found = True
                        seg = m
                        print "Msg Segment Found!"
                if seg_found:
                    print "Complete Msg Found!"
                    self.add_msg_to_repeat_list(seg+mf[:93])
                    self.msg_seg_list.remove(mf)
                    self.msg_seg_list.remove(seg)
                    break
