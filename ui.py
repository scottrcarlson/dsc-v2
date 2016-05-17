#!/usr/bin/python
# ----------------------------
# --- DSC2 UI THREAD
#----------------------------
from time import sleep
import RPi.GPIO as GPIO
import iodef
from threading import *

class UI(Thread):
    def __init__(self,display):
        Thread.__init__(self)
        self.event = Event()
        GPIO.add_event_detect(iodef.PIN_KEY_UP, GPIO.FALLING, callback=self.key_up, bouncetime=150)
        GPIO.add_event_detect(iodef.PIN_KEY_DOWN, GPIO.FALLING, callback=self.key_down, bouncetime=150)
        GPIO.add_event_detect(iodef.PIN_KEY_LEFT, GPIO.FALLING, callback=self.key_left, bouncetime=150)
        GPIO.add_event_detect(iodef.PIN_KEY_RIGHT, GPIO.FALLING, callback=self.key_right, bouncetime=150)
        GPIO.add_event_detect(iodef.PIN_KEY_ENTER, GPIO.FALLING, callback=self.key_enter, bouncetime=150)
        GPIO.add_event_detect(iodef.PIN_KEY_BACK, GPIO.FALLING, callback=self.key_back, bouncetime=150)
        self.display = display
        self.idle = False
        print "Initializing UI Thread."

    def run(self):
        print "Startings UI Thread."
        self.event.wait(1)
        while not self.event.is_set():
            print "Handling UI Stuff"
            self.event.wait(15)
            if self.idle:
                self.display.idle()
                self.idle = False
            else:
                self.idle = True

    def stop(self):
        print "Stopping UI Thread."
        self.event.set()

    def key_up(self, channel):
        self.idle = False
        print "Pressed UP Key."
        self.display.key_up()        

    def key_down(self, channel):
        self.idle = False
        print "Pressed DOWN Key."
        self.display.key_down()

    def key_left(self, channel):
        self.idle = False
        print "Pressed LEFT Key."
        self.display.key_left()

    def key_right(self, channel):
        self.idle = False
        print "Pressed RIGHT Key."
        self.display.key_right()

    def key_enter(self, channel):
        self.idle = False
        print "Pressed ENTER Key."
        #if not self.display.create_msg("Test Pretext Msg"):
            #self.display.key_enter()
        self.display.main_menu()

    def key_back(self, channel):
        self.idle = False
        print "Pressed BACK Key."
        #self.display.lock_screen()
        self.display.key_back()
