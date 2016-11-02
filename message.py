#!/usr/bin/env python
import time
from threading import *
import Queue
import hashlib
import logging
# Message thread is responsible for producing and consuming inbound/outbound radio packets via Queues.
# Perodically fill outbound queue with packets on the repeat list
# Process inbound queue to re-asemble packet segments into a complete message (3 matching segments)
#   Validate the cryptographic signature of the complete message, throw awawy message on verification failure.
#   If the signature is verified, add message to repeat list.
#       The message is further processed to:
#       extract beacons
#           Beacon signature verifies the sender
#           Beacon contains a MD5 hash of the sender's repeat list
#               The MD5 hashes are tracked via dictionary for all Nodes
#               If all hashes are equal, then everyone has everything.
#                   Confidence is increased while all hashes are equal
#                   if confidence is > some number, we will clear the repeat list
#                       and go into "quiet mode", which prevents all
#                       radio traffic except beacons for two tdma cycles
#                   Quiet Mode can also be initiated via a peer when:
#                       1. confidence > 1
#                       2?. All Hashes are equal except a node with quiet hash
#                       2?. All hashes are equal except a node with zero hash
#       OR
#       attempt to decrypt the message
#       if successful, then we know the message is for you.
class Message(Thread):
    def __init__(self, crypto, config):
        Thread.__init__(self)
        self.event = Event()
        self.log = logging.getLogger(self.__class__.__name__)
        #handler = logging.StreamHandler()
        #formatter = logging.Formatter(
        #        '%(name)-12s| %(levelname)-8s| %(message)s')
        #handler.setFormatter(formatter)
        #self.log.addHandler(handler)
        #self.log.setLevel(logging.DEBUG)

        self.auth = False
        self.sig_auth = False

        self.cleartext_msg_thread = {}
        self.msg_thread = {}
        self.repeat_msg_list = []

        self.beacon_segment = 0
        self.beacons = []
        self.beacon_quiet_hash = {}
        self.beacon_quiet_confidence = {}

        self.repeat_msg_index = 0
        self.repeat_msg_segment = 0

        self.msg_seg_list = []
        self.radio_inbound_queue = Queue.Queue() #Should we set a buffer size??
        self.radio_outbound_queue = Queue.Queue()
        self.radio_beacon_queue = Queue.Queue()

        self.config = config
        self.crypto = crypto

        self.friends = []

        self.compose_msg = ""
        self.compose_to = ""

        self.is_radio_tx = False
        self.quiet_mode = False

        self.quiet_cmd = 'shhh!'
        self.last_repeat_hash = ''
        self.normal_cmd = 'ok'
        self.beacon_cmd = 'dsc2.bitbucket.org'
        self.network_equal = True

        self.prev_msg_thread_size = {}
        self.log.info("Initialized Message Thread.")

    def run(self):
        tmda_frame_size = (self.config.tdma_total_slots * (self.config.tx_time + self.config.tx_deadband))
        beacon_interval = tmda_frame_size
        quiet_interval = tmda_frame_size
        quiet_frames = 1 #Number of frames to prevent inbound/outbound traffic except beacons
        quiet_cnt = 0
        beacon_timeout = time.time()
        quiet_timeout = time.time()
        self.build_friend_list();
        seg_life_cnt = 0
        latchCheck = True
        self.event.wait(1)
        while not self.event.is_set():
            self.fill_outbound_queue()
            try:
                msg = self.radio_inbound_queue.get_nowait()
            except Queue.Empty:
                if not latchCheck:
                    latchCheck = True
                    self.check_for_complete_msgs()
            else:
                #print "Inbound Packet Processed."
                latchCheck = False
                self.add_msg_to_seg_list(msg)
            timestamp = time.time()
            if timestamp - quiet_timeout > quiet_interval:
                quiet_timeout = time.time()
                if self.quiet_mode:
                    if quiet_cnt < quiet_frames:
                        quiet_cnt += 1
                    else:
                        self.msg_seg_list[:] = []
                        self.radio_inbound_queue.queue.clear()
                        self.quiet_mode = False
                        self.last_repeat_hash = ''
                        self.log.debug( "Quiet Mode Disabled.")
                else:
                    quiet_cnt = 0
            if self.is_radio_tx and len(self.msg_seg_list) > 0: #too aggressive look at this again
                #print 'Clearing Seg List.'
                self.msg_seg_list[:] = []


            self.event.wait(0.05)

    def stop(self):
        self.log.info( "Stopping Message Thread.")
        self.event.set()

    def get_msg_thread(self,friend):
        #look up by alias to return the associate msg thread
        if friend in self.cleartext_msg_thread:
            return self.cleartext_msg_thread[friend]
        else:
            return None

    def decrypt_msg_thread(self, friend):
        #pass friends alias, and decrypt thread make available for viewing
        if friend in self.msg_thread:

            if friend not in self.cleartext_msg_thread: #Initialize
                self.cleartext_msg_thread[friend] = []
            if friend not in self.prev_msg_thread_size: #Initialize
                self.prev_msg_thread_size[friend] = 0

                self.log.debug( "Decrypting Msg Thread for Viewing.")
            if len(self.msg_thread[friend]) != self.prev_msg_thread_size[friend]:
                self.prev_msg_thread_size[friend] = len(self.msg_thread[friend])
            #self.log.info( "Decrypting thread for viewing pleasure..."
                tmp_cleartext = []
                for cypher_msg in self.msg_thread[friend]:
                    try:
                        msg_arrived = float(cypher_msg.split('|',1)[0])
                        cypher_data = cypher_msg.split('|',1)[1]
                        clear_msg = self.crypto.decrypt_msg(cypher_data, self.config.alias)
                        clear_msg_segs = clear_msg.split('|')
                        msg_timestamp = time.mktime(time.strptime(clear_msg_segs[0], "%Y-%m-%d %H:%M:%S"))
                        tmp_cleartext.append(friend + " " + str(round(msg_arrived - msg_timestamp,0)) + "s")
                        #tmp_cleartext.append(clear_msg_segs[0]) # Timestamp
                        clear_text = clear_msg_segs[1]
                        while len(clear_text) > 20:
                            tmp_cleartext.append(clear_text[:20]) # Actual Msg
                            clear_text = clear_text[20:]
                        tmp_cleartext.append(clear_text)
                        del(clear_msg_segs) # ???
                        del(clear_msg) # del from mem, is this good enough. research
                    except Exception, e:
                        self.log.error( "Failed to decrypt: ", exc_info=True)
                self.log.debug( "Rebuilding Msg Thread: Complete.")
                self.cleartext_msg_thread[friend] = tmp_cleartext
        else:
            pass
            #print "Msg thread is empty:", friend

    def build_friend_list(self):
        self.log.debug( "Building Friend list")
        self.friends = self.crypto.get_friend_key_paths(self.config.alias)
        empty_hash = hashlib.md5("".join(str(x) for x in sorted(self.repeat_msg_list))).hexdigest()
        for friend in self.friends:
            self.beacon_quiet_hash[friend] = empty_hash
            self.beacon_quiet_confidence[friend] = 0
            self.log.debug( "friend: " +  friend)

    def is_msg_avail_to_repeat(self):
        if len(self.repeat_msg_list) > 0 or len(self.beacons) > 0:
            return True
        else:
            return False

    def fill_outbound_queue(self):
        if self.radio_outbound_queue.qsize() == 0:
            if not self.quiet_mode:
                for msg in self.repeat_msg_list:
                    self.radio_outbound_queue.put_nowait(msg[:255])
                    self.radio_outbound_queue.put_nowait(msg[255:510])
                    seg1f = msg[:100]
                    seg2f = msg[255:355]
                    self.radio_outbound_queue.put_nowait(msg[510:] + seg1f + seg2f)

    def generate_beacon(self):
        if self.sig_auth: #Need sig_auth to sign beacons
            self.radio_beacon_queue.queue.clear()
            if self.quiet_mode:
                net_cmd = hashlib.md5(self.quiet_cmd).hexdigest()
                hash_repeat_list = self.last_repeat_hash
            else:
                net_cmd = hashlib.md5(self.normal_cmd).hexdigest()
                hash_repeat_list = hashlib.md5("".join(str(x) for x in sorted(self.repeat_msg_list))).hexdigest()
            beacon_msg = self.beacon_cmd + net_cmd + hash_repeat_list + ''.ljust(197-len(self.beacon_cmd)) #Needs to be 261 bytes total
            s_msg = self.crypto.sign_msg(beacon_msg, self.config.alias)
            beacon_msg += s_msg
            self.radio_beacon_queue.put_nowait(beacon_msg[:255])
            self.radio_beacon_queue.put_nowait(beacon_msg[255:510])
            seg1f = beacon_msg[:100]
            seg2f = beacon_msg[255:355]
            self.radio_beacon_queue.put_nowait(beacon_msg[510:] + seg1f + seg2f)
            #if self.quiet_mode:
            #    for i in range(0,2):
            #        self.radio_beacon_queue.put_nowait(beacon_msg[510:] + seg1f + seg2f)
            #    print "Beacon Queue Size: ", self.radio_beacon_queue.qsize()
            #else:
            #    self.radio_beacon_queue.put_nowait(beacon_msg[510:] + seg1f + seg2f)

    def process_composed_msg(self, msg, friend):
        #Need to enforce hard limit for cleartext
        #19 Bytes for timestamp (can save a few bytes with formatting)
        #214-19=195 msg size limit
        #print "Processing new outbound message."
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
            self.log.debug( "Duplicate Message Received via Radio. Dropped")
            return False

    def add_msg_to_seg_list(self,msg):
        #lots of things to do here...
        if not self.check_for_seg_dup(msg):
            self.msg_seg_list.append(msg)
            #print "New Unique Seqment Received ."
            #print msg
        else:
            self.log.debug( "Duplicate Segment Received via Radio. Dropped")

    def check_for_dup(self,msg):
        #print "Check for dups"
        #Check for duplicates in the repeat msg list, every encrypted msg is unique, no dups allowed!
        for m in self.repeat_msg_list:
            self.event.wait(0.1)
            if msg == m:
                return True
        return False

    def check_for_dup_msg_thread(self, msg, friend):
        if friend in self.msg_thread:
            for m in self.msg_thread[friend]:
                self.event.wait(0.1)
                if msg == m:
                    return True
        return False

    def check_for_seg_dup(self,msg):
        #Check for duplicates in the repeat msg list, every encrypted msg is unique, no dups allowed!
        for m in self.msg_seg_list:
            if m[0] == self.msg_seg_list[0]:
                return True
        #print "ADDING SEG."
        return False

    def check_for_complete_msgs(self):
        seg1f = ""  #Part of Encrypted Packet (Fingerprint)
        seg2f = ""  #Part of Signature Packet (Fingerprint)
        seg1_found = False
        seg2_found = False
        seg1 = ""   #Actual Msg Segment
        seg2 = ""   #Actual Msg Segment
        is_for_me = False
        rf_snr = 0
        rf_rssi = 0
        for mseg in self.msg_seg_list:
            mf = mseg[0]
            if len(mf) == 212:
                seg1f = mf[12:112]
                seg2f = mf[112:212]
                rf_data = mseg[1]
                rf_rssi = rf_data.split('|')[0]
                rf_snr = rf_data.split('|')[1]
                #print "Found Finger Print."
                #print "Searching for remaining segments."
                for mseg2 in self.msg_seg_list:
                    m = mseg2[0]
                    if len(m) == 255:
                        if m[:100] == seg1f:
                            seg1_found = True
                            seg1 = m
                            origseg1 = mseg2 #Used to Remove from list.. This whole routine is looking hacky
                            #print "Msg Segment 1 Found!"
                            #print seg1
                        elif m[:100] == seg2f:
                            seg2_found = True
                            seg2 = m
                            origseg2 = mseg2 #Used to Remove from list.. This whole routine is looking hacky
                            #print "Msg Segment 2 Found!"
                            #print seg2
                    if seg1_found and seg2_found:
                        seg1_found = False
                        seg2_found = False
                        #print "Complete Msg Found!"
                        msg = str(seg1 + seg2[:6])
                        sig = str(seg2[6:] + mf[:12])

                        # Iterate through public signature keysets
                        #alias_list = []
                        #for a in self.friends:
                        #    alias_list.append(a)
                        #alias_list.append(self.config.alias)

                        if self.crypto.verify_msg(msg, sig, self.config.alias):
                            #A Msg that Originated from here has been Repeated Back
                            #Allow Network to Mend if Queues are in different states
                            #Also, we never repeat beacons from other nodes,
                            #therefore, we will never need to check if this
                            #condition has is beacon!
                            msg_complete = msg_complete = seg1 + seg2 + mf[:12]
                            if not self.quiet_mode:
                                if self.add_msg_to_repeat_list(msg_complete):
                                    self.log.debug( "Unique msg added to repeat list [ HEALING ].")
                        else:
                            valid_cnt = 0
                            for friend in self.friends:
                                self.event.wait(0.2)
                                #print "Checking is msg from: ", alias
                                if self.crypto.verify_msg(msg, sig, friend):
                                    valid_cnt += 1
                                    if self.process_msg(msg,friend, rf_rssi, rf_snr):
                                        if not self.quiet_mode:
                                            msg_complete = seg1 + seg2 + mf[:12]
                                            if self.add_msg_to_repeat_list(msg_complete):
                                                self.log.debug( "Unique Msg added to repeat list.")
                                                if not self.check_for_dup_msg_thread(msg, friend):
                                                    try:
                                                        if not self.crypto.decrypt_msg(msg, self.config.alias) == '':
                                                            #Its fself.check_for_dup_msg_threador you, Added to Msg Thread
                                                            if friend in self.msg_thread:
                                                                self.msg_thread[friend].append(str(time.time())+'|'+msg)
                                                            else:
                                                                self.msg_thread[friend] = [str(time.time())+'|'+msg]
                                                            self.log.debug( "Unique Msg is for you.")
                                                    except Exception, e:
                                                        self.log.error( "Msg failed to decypt. Not for you. :", exc_info=True)
                                    else:
                                        pass
                                        #Beacon Recvd
                                    break
                            if valid_cnt == 0:
                                self.log.debug( "Unique msg rejected [Failed to verify sig]")
                        try:
                            self.msg_seg_list.remove(mseg)
                            self.msg_seg_list.remove(origseg1)
                            self.msg_seg_list.remove(origseg2)
                        except:
                            pass
                        break

    def process_msg(self, msg, friend, rf_rssi, rf_snr):
        if self.beacon_cmd in msg:
            cmd_hash = msg[len(self.beacon_cmd):(32 + len(self.beacon_cmd))]
            beacon_hash = msg[(len(self.beacon_cmd) + 32):(64 + len(self.beacon_cmd))]
            self.log.debug("----------------- Beacon ------------------")
            self.log.debug( "Beacon Recvd [" + friend + '] RSSI/SNR:[' + rf_rssi + ']/[' + rf_snr + '] MD5:' + beacon_hash)
            hash_repeat_list = hashlib.md5("".join(str(x) for x in sorted(self.repeat_msg_list))).hexdigest()
            self.beacon_quiet_hash[friend] = beacon_hash
            if not self.quiet_mode:
                if self.beacon_quiet_hash[friend] == hash_repeat_list and cmd_hash == hashlib.md5(self.quiet_cmd).hexdigest():
                    if hash_repeat_list != hashlib.md5('').hexdigest():
                        self.quiet_mode = True
                        self.network_equal = True
                        for node in self.beacon_quiet_confidence:
                            self.beacon_quiet_confidence[node] = 0
                        self.repeat_msg_list[:] = []
                        self.msg_seg_list[:] = []
                        self.last_repeat_hash = hash_repeat_list
                        self.log.debug( "Network Equal. Quiet Mode Activated by Peer.")
                elif self.beacon_quiet_hash[friend] == hash_repeat_list and hash_repeat_list != hashlib.md5('').hexdigest():
                    self.beacon_quiet_confidence[friend] += 1
                    self.log.debug( "Network Equal Confidence Increased with ["+friend+"]: " + str(self.beacon_quiet_confidence[friend]))
                    consensus = 0
                    for node in self.beacon_quiet_confidence:
                        if self.beacon_quiet_confidence[node] >= 2:
                            consensus += 1
                    if consensus == len(self.beacon_quiet_confidence):
                        self.quiet_mode = True
                        self.network_equal = True
                        for node in self.beacon_quiet_confidence:
                            self.beacon_quiet_confidence[node] = 0
                        self.repeat_msg_list[:] = []
                        self.msg_seg_list[:] = []
                        self.last_repeat_hash = hash_repeat_list
                        self.log.debug( "Network Equal. Quiet Mode Activated")
                elif self.beacon_quiet_hash[friend] != hash_repeat_list:
                    self.beacon_quiet_confidence[friend] = 0
                    self.network_equal = False
                    self.log.debug( "Network NOT Equal. No Confidence with ["+friend+"]: " + str(self.beacon_quiet_confidence[friend]))
                elif hash_repeat_list == hashlib.md5('').hexdigest():
                    tally_empty = 0
                    for node in self.beacon_quiet_hash:
                        if self.beacon_quiet_hash[node] == hashlib.md5('').hexdigest():
                            tally_empty += 1
                    if tally_empty == len(self.beacon_quiet_hash):
                        self.network_equal = True
                        self.log.debug( "Network Equal [empty].")
            else:
                self.log.debug( "Network Equal. Quiet Mode Active.")
            self.log.debug( "Inbound Q/Seg List/Repeat List: " + '[' + str(self.radio_inbound_queue.qsize()) + ']/[' + str(len(self.msg_seg_list)) + ']/['+ str(len(self.repeat_msg_list))+']')
            return False
        else:
            return True
