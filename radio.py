#!/usr/bin/env python

# usage:
#  python rxr_rx.py /dev/ttyUSB0

from ll_ifc import ModuleConnection, OPCODES
import sys, time, binascii, struct, os
import RPi.GPIO as GPIO
import datetime
from threading import * 
import iodef
from time import sleep

class Radio(Thread):
    def __init__(self,serial_device, verbose):
        Thread.__init__(self)
        self.event = Event()

        self.serial_device = serial_device
        self.verbose = verbose
        self.ignore_radio_irq = False

        self.total_recv = 0
        self.total_sent = 0
        self.total_exceptions = 0
        self.prev_total_sent = 0
        self.prev_total_recv = 0
        self.prev_total_exceptions = 0

        self.is_check_outbound = False
        self.is_check_inbound = True
        self.update_stats = True
        self.mc = ModuleConnection(self.serial_device)

        self.reset_radio()
        GPIO.add_event_detect(iodef.PIN_RADIO_IRQ, GPIO.RISING, callback=self.check_irq, bouncetime=100)

        with open("dsc2_addr.txt") as faddr:
            self.address = faddr.read()
            print "Some Address from a file:", self.address


        print "Initialized Radio Thread."


    def run(self):
        self.event.wait(1)
        while not self.event.is_set():
            
            self.event.wait(0.05)

            if self.is_check_inbound:# and not is_check_outbound:
                self.process_inbound_msg()
            else:
                self.process_outbound_msg()

            if self.total_sent != self.prev_total_sent or self.total_recv != self.prev_total_recv or self.total_exceptions != self.prev_total_exceptions:
                self.prev_total_sent = self.total_sent
                self.prev_total_recv = self.total_recv
                self.prev_total_exceptions = self.total_exceptions
                print "== Sent: [",self.total_sent,"]  Recvd:[",self.total_recv,"] Radio Exceptions:[",self.total_exceptions,"] =="

                
    def stop(self):
        print "Stopping Radio Thread."
        self.event.set()


    def signal_quality(self,rssi):
        if rssi > -60:
                quality = "GOOD"
        elif rssi > -75:
                quality = "OK"
        elif rssi > -95:
                quality = "POOR"
        else:
                quality = "BAD"
        return quality

    def process_inbound_msg(self):
        global total_recv
        global total_exceptions
        global is_check_inbound
        try:
            received_data = self.mc._send_command(OPCODES['PKT_RECV_CONT'])
            sleep(0.01)
        except Exception, e:
            if self.verbose > 0:
                print "EXCEPTION PKT_RECV_CONT: ", e
        else:
            if len(received_data) > 0:
                self.update_stats = True
                addr_to = chr(received_data[3])
                addr_from = chr(received_data[4])
                msg = received_data[5:]
                self.total_recv += 1

                (rssi, ) = struct.unpack_from('<h', bytes(received_data[:2]))
                snr = received_data[2] / 4.0

                if self.verbose > 1:
                    print "[START]--------------------------"
                    print "RSSI:", rssi, "SnR:", snr
                    print "Signal Quality:",signal_quality(rssi)
                    print "Msg: ", msg
                    print "----------------------------[END]"
                sleep(0.025)

        finally:
            self.is_check_inbound = False

            try:
                self.mc.clear_irq_flags()
                sleep(0.01)

            except Exception, e:
                if self.verbose > 0:
                    print "EXCEPTION: CLEAR_IRQ_FLAGS: ", e


    def process_outbound_msg(self):
        if os.path.isfile("outbound.txt"):
            with open("outbound.txt",'r') as f:
                outbound_data = f.read()
                self.is_check_outbound = True
                try:
                    r = self.mc._send_command(OPCODES['PKT_SEND_QUEUE'], outbound_data)
                    sleep(0.015)
                    self.is_check_outbound = False
                except Exception, e:
                    if self.verbose > 0:
                        print "EXCEPTION PKT_SEND_QUEUE: ", e
                    self.total_exceptions += 1
                    self.is_check_outbound = False
                    self.reset_radio()

                    sleep(0.025)
                self.update_stats = True
            os.remove("outbound.txt")


    def check_irq(self,channel):
        if not self.ignore_radio_irq:
            if self.is_check_outbound:
                sleep(0.05)
            try:
                irq_flags = self.mc.get_irq_flags()

            except Exception, e:
                if self.verbose > 0:
                    print "EXCEPTION GET_IRQ_FLAGS: ", e
                self.total_exceptions += 1

            else:
                if self.verbose > 1:
                    print "IRQ FIRED: ", irq_flags

                if "RX_DONE" in irq_flags:
                    self.is_check_inbound = True

                if "TX_DONE" in irq_flags:
                    self.set_radio_recv_mode()
                    self.is_check_outbound = False
                    self.total_sent += 1
    
                if "RESET" in irq_flags:
                    pass

    def reset_radio(self):
        self.ignore_radio_irq = True
        GPIO.output(iodef.PIN_RADIO_RESET, False)
        sleep(0.1)
        GPIO.output(iodef.PIN_RADIO_RESET, True)
        sleep(1)
        try:
            self.mc.clear_irq_flags()
        except Exception, e:
            if self.verbose > 0:
                print "EXCEPTION: CLEAR_IRQ_FLAGS: ", e
        self.ignore_radio_irq = False

    def set_radio_recv_mode(self):
        sleep(0.01)
        try:
            received_data = self.mc._send_command(OPCODES['PKT_RECV_CONT'])
        except Exception, e:
            if self.verbose > 0:
                print "EXCEPTION PKT_RECV_CONT: ", e
        else:
            if self.verbose > 1:
                print "Radio in Recv Mode"
        sleep(0.01)
        try:
            self.mc.clear_irq_flags()

        except Exception, e:
            if self.verbose > 0:
                print "EXCEPTION: CLEAR_IRQ_FLAGS: ", e

