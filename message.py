#!/usr/bin/env python
import time
from threading import *
import Queue
import hashlib

TEST_MSG = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"

class Message(Thread):
    def __init__(self, crypto, config):
        Thread.__init__(self)
        self.event = Event()

        self.auth = False
        self.sig_auth = False

        self.cleartext_msg_thread = []
        self.msg_thread = []
        self.repeat_msg_list = []

        self.beacon_segment = 0
        self.beacons = []
        self.beacon_quiet_hash = {}
        self.beacon_quiet_confidence = 0

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
        beacon_interval = self.config.tdma_total_slots * (self.config.tx_time + self.config.tx_deadband)
        print "Beacon Interval: ", beacon_interval, " sec"
        beacon_timeout = time.time()
        seg_life_cnt = 0

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
                for friend in self.friends:
                    self.decrypt_msg_thread(friend)

            if time.time() - beacon_timeout > beacon_interval:
                beacon_timeout = time.time()
                self.generate_beacons()
                if len(self.msg_seg_list) > 10:
                    seg_life_cnt += 1
                    if seg_life_cnt > 1:
                        print "Clearing Orphaned Msg Segments."
                        self.msg_seg_list[:] = []   #Imposing some form of /lifespan. TODO make better

            self.event.wait(1)

    def stop(self):
        print "Stopping Message Thread."
        self.event.set()

    def get_msg_thread(self):
        #look up by alias to return the associate msg thread
        return self.cleartext_msg_thread

    def decrypt_msg_thread(self, alias):
        #pass alias, and decrypt thread make available for viewing
        if len(self.msg_thread) != (len(self.cleartext_msg_thread) / 3):
            #print "Decrypting thread for viewing pleasure..."
            tmp_cleartext = []
            print "Rebuilding Msg Thread: Started."
            for cypher_msg in self.msg_thread:
                try:
                    clear_msg = self.crypto.decrypt_msg(cypher_msg, self.config.alias)
                    clear_msg_segs = clear_msg.split('|')
                    msg_timestamp = time.mktime(time.strptime(clear_msg_segs[0], "%Y-%m-%d %H:%M:%S"))
                    tmp_cleartext.append(alias + " " + str(round(time.time() - msg_timestamp,0)) + "s")
                    tmp_cleartext.append(clear_msg_segs[0]) # Timestamp
                    tmp_cleartext.append(clear_msg_segs[1]) # Actual Msg
                    del(clear_msg_segs) # ???
                    del(clear_msg) # del from mem, is this good enough. research
                except Exception as e:
                    print "Failed to decrypt: ", e
            print "Rebuilding Msg Thread: Complete."
            self.cleartext_msg_thread = tmp_cleartext
            #del(tmp_cleartext)

    def build_friend_list(self):
        print "Building Friend list"
        self.friends = self.crypto.get_friend_key_paths(self.config.alias)
        print "friend list: ", self.friends

    def is_msg_avail_to_repeat(self):
        if len(self.repeat_msg_list) > 0 or len(self.beacons) > 0:
            return True
        else:
            return False

    def get_next_msg_for_repeat(self):
        outbound_data = ''
        seg1f = ''
        seg2f = ''

        if len(self.beacons) > 0:
            if self.beacon_segment == 0:
                outbound_data = self.beacons[0][:255]
                self.beacon_segment += 1
            elif self.beacon_segment == 1:
                outbound_data = self.beacons[0][255:510]
                self.beacon_segment += 1
            elif self.beacon_segment == 2:
                #Grab Fingerprint from First 2 Segments
                seg1f = self.beacons[0][:100]
                seg2f = self.beacons[0][255:355]
                outbound_data = self.beacons[0][510:]
                outbound_data += seg1f + seg2f
                self.beacon_segment = 0
                del self.beacons[0]
        else:
            msg_list_len = len(self.repeat_msg_list)

            if msg_list_len > 0:
                if self.repeat_msg_index >= msg_list_len:
                    self.repeat_msg_index = 0
                    self.repeat_msg_segment = 0

                print "Sending Msg Index: ", self.repeat_msg_index, " Seg: ", self.repeat_msg_segment, " List Size: ", msg_list_len, " Msg Thread Size: ", len(self.msg_thread)
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
                    outbound_data += seg1f + seg2f
                    self.repeat_msg_segment =0
                    self.repeat_msg_index += 1


        return outbound_data

    def generate_beacons(self):
        if self.sig_auth:
            self.beacons[:] = []
            print "generating beacon. "
            hash_repeat_list = hashlib.md5("".join(str(x) for x in sorted(self.repeat_msg_list))).hexdigest()
            beacon_msg = 'hello' + hash_repeat_list + ''.ljust(224) #Needs to be 261 bytes total
            s_msg = self.crypto.sign_msg(beacon_msg, self.config.alias)
            self.beacons.append(beacon_msg + s_msg)

    def process_composed_msg(self, msg, friend):
        #Need to enforce hard limit for cleartext
        #19 Bytes for timestamp (can save a few bytes with formatting)
        #214-19=195 msg size limit
        print "Processing new outbound message."
        #Encrypt / Sign and add to the list
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        e_msg = self.crypto.encrypt_msg(timestamp+'|'+msg, friend)
        s_msg = self.crypto.sign_msg(e_msg, self.config.alias)
        self.repeat_msg_list.append(e_msg + s_msg)

        total_msg = e_msg + s_msg
        return True # TODO Lets capture keyczar error and report back false

    def add_msg_to_repeat_list(self,msg):
        #lots of things to do here...
        if not self.check_for_dup(msg):
            self.repeat_msg_list.append(msg)
            return True
            #print "New Unique Message Received via Radio."
            #print msg
        else:
            print "Duplicate Message Received via Radio. Dropped"
            return False

    def add_msg_to_seg_list(self,msg):
        #lots of things to do here...
        if not self.check_for_seg_dup(msg):
            self.msg_seg_list.append(msg)
            #print "New Unique Seqment Received ."
            #print msg
        else:
            print "Duplicate Segment Received via Radio. Dropped"

    def check_for_dup(self,msg):
        #print "Check for dups"
        #Check for duplicates in the repeat msg list, every encrypted msg is unique, no dups allowed!
        for m in self.repeat_msg_list:
            self.event.wait(0.1)
            if msg == m:
                return True
        return False

    def check_for_dup_msg_thread(self, msg):
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
        is_for_me = False

        for mf in self.msg_seg_list:
            if len(mf) == 212:
                seg1f = mf[12:112]
                seg2f = mf[112:212]
                #print "Found Finger Print."
                #print seg1f
                #print seg2f
                #print "Searching for remaining segments."
            for m in self.msg_seg_list:
                if len(m) == 255:
                    if m[:100] == seg1f:
                        seg1_found = True
                        seg1 = m
                        #print "Msg Segment 1 Found!"
                        #print seg1
                    elif m[:100] == seg2f:
                        seg2_found = True
                        seg2 = m
                        #print "Msg Segment 2 Found!"
                        #print seg2
                if seg1_found and seg2_found:
                    #print "Complete Msg Found!"
                    msg = str(seg1 + seg2[:6])
                    sig = str(seg2[6:] + mf[:12])
                    # Iterate through public signature keysets
                    alias_list = []
                    for a in self.friends:
                        alias_list.append(a)
                    alias_list.append(self.config.alias)

                    if self.crypto.verify_msg(msg, sig, self.config.alias):
                        #A Msg that Originated from here has been Repeated Back
                        #Allow Network to Mend if Queses are in different states
                        #Still working out Beacon Hash (All Parties have everything)
                        # moment) There are a couple of edge cases that we've found
                        # with just two nodes, we may find more as we increase
                        # network size.

                        #Also, we never repeat beacons from other nodes,
                        #therefore, we will never need to check if this
                        #condition has is beacon!
                        msg_complete = msg_complete = seg1 + seg2 + mf[:12]
                        if self.add_msg_to_repeat_list(msg_complete):
                            print "Unique Msg Added to Repeat List [ Healing ]."
                    else:
                        for friend in self.friends:
                            self.event.wait(0.25)
                            #print "Checking is msg from: ", alias
                            if self.crypto.verify_msg(msg, sig, friend):
                                if self.process_msg(msg,friend):
                                    msg_complete = seg1 + seg2 + mf[:12]
                                    if self.add_msg_to_repeat_list(msg_complete):
                                        print "Unique Msg Added to Repeat List."
                                        if not self.check_for_dup_msg_thread(msg):
                                            self.msg_thread.append(msg)
                                break
                    try:
                        self.msg_seg_list.remove(mf)
                        self.msg_seg_list.remove(seg1)
                        self.msg_seg_list.remove(seg2)
                    except:
                        pass
                    break

    def process_msg(self,msg,alias):
        if 'hello' in msg:
            beacon_timestamp = "Not Available"
            beacon_hash = msg[5:37]
            print "Beacon Hash Recvd from (" + alias + '): ' + beacon_hash
            hash_repeat_list = hashlib.md5("".join(str(x) for x in sorted(self.repeat_msg_list))).hexdigest()
            self.beacon_quiet_hash[alias] = beacon_hash
            self.beacon_quiet_hash[self.config.alias] = hash_repeat_list
            consensus_cnt = 0
            for key, value in self.beacon_quiet_hash.iteritems():
                if value == hashlib.md5('').hexdigest():
                    if self.beacon_quiet_confidence > 1:
                        print "== Peer Quiet Network =="
                        self.repeat_msg_list[:] = []
                        self.beacon_quiet_confidence = 0
                elif value == hash_repeat_list:
                    consensus_cnt += 1

            if (consensus_cnt == len(self.beacon_quiet_hash)):
                self.beacon_quiet_confidence += 1
                print "Current Confidence:", self.beacon_quiet_confidence
                if self.beacon_quiet_confidence >= 5: #arbitrary, needs further consideration
                    self.beacon_quiet_confidence = 0
                    print "== Initiate Quiet Network =="
                    self.repeat_msg_list[:] = []
            else:
                self.beacon_quiet_confidence = 0
            print 'Beacon Hashes: ', self.beacon_quiet_hash
            print "Repeat Msg Queue Size: ", len(self.repeat_msg_list)
            print "Repeat Msg Segment Queue Size: ", len(self.msg_seg_list)
            return False
        else:
            return True
