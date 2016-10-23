#!/usr/bin/env python
import time
from threading import *
import Queue

TEST_MSG = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"

class Message(Thread):
    def __init__(self, crypto, config):
        Thread.__init__(self)
        self.event = Event()
        
        self.auth = False

        self.cleartext_msg_thread = []
        self.msg_thread = []
        self.repeat_msg_list = []
        self.repeat_msg_index = 0
        self.repeat_msg_segment = 0

        self.msg_seg_list = []
        self.radio_inbound_queue = Queue.Queue() #Should we set a buffer size??

        self.config = config
        self.crypto = crypto
        
        self.friends = []

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
                if not self.check_for_seg_dup(msg):
                    self.add_msg_to_seg_list(msg)

            self.check_for_complete_msgs()
            
            if self.auth:
                self.decrypt_msg_thread(self.friends[0]) #demo labs hack
            self.event.wait(1)

    def stop(self):
        print "Stopping Message Thread."
        self.event.set()

    def get_msg_thread(self):
        #look up by alias to return the associate msg thread
        return self.cleartext_msg_thread

    def decrypt_msg_thread(self, alias):
        #pass alias, and decrypt thread make available for viewing
        print "clearmsg: ", len(self.cleartext_msg_thread)
        print "cmsg: ", len(self.msg_thread)
        if len(self.msg_thread) != (len(self.cleartext_msg_thread) / 3):
            print "Decrypting thread for viewing pleasure..."
            tmp_cleartext = []
            for cypher_msg in self.msg_thread:
               
                try:
                    clear_msg = self.crypto.decrypt_msg(cypher_msg, self.config.alias)
                    tmp_cleartext.append(alias + "  (ttd)")
                    tmp_cleartext.append("orig timestamp here")
                    tmp_cleartext.append(clear_msg)
                    del(clear_msg) # del from mem, is this good enough. research
                except:
                    print "Failed to decrypt"
            self.cleartext_msg_thread = tmp_cleartext
            #del(tmp_cleartext)

    def build_friend_list(self):
        print "Building Friend list"
        self.friends = self.crypto.get_friend_key_paths(self.config.alias)
        print "friend list: ", self.friends

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
                outbound_data = self.repeat_msg_list[self.repeat_msg_index][255:510]
                self.repeat_msg_segment += 1
            elif self.repeat_msg_segment == 2:
                #Grab Fingerprint from First 2 Segments
                seg1f = self.repeat_msg_list[self.repeat_msg_index][:100]
                seg2f = self.repeat_msg_list[self.repeat_msg_index][255:355]
                outbound_data = self.repeat_msg_list[self.repeat_msg_index][510:]
                #print "WHAT: ", outbound_data
                #print "WHAT: ", seg1f
                #print "WHAT: ", seg2f
                outbound_data += seg1f + seg2f
                self.repeat_msg_segment += 1
            
            if self.repeat_msg_segment == 3:
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
        e_msg = self.crypto.encrypt_msg(msg, "boris")#self.config.alias)
        s_msg = self.crypto.sign_msg(e_msg, self.config.alias)
        self.repeat_msg_list.append(e_msg + s_msg)
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
        print "Check for dups"
        #Check for duplicates in the repeat msg list, every encrypted msg is unique, no dups allowed!
        
        for m in self.repeat_msg_list:
            self.event.wait(0.1)
            if msg == m:
                return True
        for m in self.msg_thread:
            self.event.wait(0.1)
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
        seg1f = ""  #Part of Encrypted Packet (Fingerprint)
        seg2f = ""  #Part of Signature Packet (Fingerprint)
        seg1_found = False
        seg2_found = False
        seg1 = ""   #Actual Msg Segment
        seg2 = ""   #Actual Msg Segment 
        
        for mf in self.msg_seg_list:
            if len(mf) == 212:
                seg1f = mf[12:112]
                seg2f = mf[112:212]
                print "Found Finger Print."
                #print seg1f
                #print seg2f
                #print "Searching for remaining segments."
            for m in self.msg_seg_list:
                if len(m) == 255:
                    if m[:100] == seg1f:
                        seg1_found = True
                        seg1 = m
                        print "Msg Segment 1 Found!"
                        #print seg1
                    elif m[:100] == seg2f:
                        seg2_found = True
                        seg2 = m
                        print "Msg Segment 2 Found!"
                        #print seg2
                if seg1_found and seg2_found:
                    print "Complete Msg Found!"
                    msg = str(seg1 + seg2[:6])
                    sig = str(seg2[6:] + mf[:12])
                    # Iterate through public signature keysets
                    #clean thi us
                    alias_list = []
                    for a in self.friends:
                        alias_list.append(a)
                    alias_list.append(self.config.alias)
                    for alias in alias_list:
                        if self.crypto.verify_msg(msg, sig, alias):
                            is_for_me = False
                            print "Msg Source: ", alias
                            if self.auth:
                                try:
                                    clear_msg = self.crypto.decrypt_msg(msg, self.config.alias)
                                    print "Msg Recv: ", clear_msg
                                    clear_msg = "" # del from mem, is this good enough. research
                                    is_for_me = True
                                except:
                                    print "Failed to decrypt"
                            
                            msg_complete = seg1 + seg2 + mf[:12]
                            if not self.check_for_dup(msg_complete) and not self.check_for_dup(msg):
                                print "not a dup ********************"
                                if is_for_me:
                                    self.msg_thread.append(msg)
                                else:
                                    self.msg_thread.append(msg) # demo labs hack
                                    self.add_msg_to_repeat_list(msg_complete)
                            else:
                                print "Duplicate Found, msg dropped."
                            break
                        else:
                            print "Msg Not From: ", alias

                    try:
                        self.msg_seg_list.remove(mf)
                        self.msg_seg_list.remove(seg1)
                        self.msg_seg_list.remove(seg2)
                    except:
                        print "WHY, FIXME YOU ASS"
                    break
