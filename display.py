#!/usr/bin/python
# ----------------------------
# --- OLED Display Functions
#----------------------------
from oled.device import ssd1306, sh1106
from oled.render import canvas
from PIL import ImageDraw, Image, ImageFont
from time import sleep
import RPi.GPIO as GPIO
import iodef
from threading import *


main_menu = {
    0:"Send New Msg",
    1:"View Received",
    2:"View Sent",
    3:"Add Friend",
    4:"View Outbound",
    5:"Initialize Keys",
    6:"System Reset",
}

pretext_msgs = [
    "Where are you?",
    "Where/When do you want to meet?",
    "I am ",
    "Meet you at ",
    "I'll be there in ",
    "I'm hungry, anyone want to grab some food?",
    "Let's grab some beers",
    "I'm at Bally/Paris",
    "I'm in SkyTalks",
    "I'm in 101 Presentation",
    "I'm in hotel room, down time."
]

class Display(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.event = Event()
        self.reset()
        self.device = sh1106(port=1, address=0x3C)
        self.font = ImageFont.load_default()
        self.msg = ""

        #Modes
        # 0 -- Lock Screen
        # 1 -- Message Composition
        self.mode = 0 

        self.row_index = 0
        self.col_index = 0
        self.char_space = 6
        self.char_size = 4
        self.row_height = 12

        self.keyboard = "abcdefghijklmnopqrstuvwxyz1234567890!?$%.-"
        print "Initializing OLED Display Thread."

    def run(self):
        print "Startings OLED Display Thread."
        self.event.wait(1)
        while not self.event.is_set():
            if self.mode == 0:                      # Idle Display (Blank)
                with canvas(self.device) as draw:
                    pass               
            if self.mode == 1:                      # Lock Screen
                with canvas(self.device) as draw:
                    logo = Image.open('/home/pi/dsc.png')
                    draw.bitmap((0, 20), logo, fill=1)
                    draw.text((0, 52), '5', font=self.font, fill=255)
                    draw.text((105, 52), 'SYNC', font=self.font, fill=255)
                    draw.text((6, 10), 'dirt   simple  comms', font=self.font, fill=255)
                    draw.text((35, 52), 'insert key', font=self.font, fill=255)

            elif self.mode == 2:                    # Message Composition Screen
                self.row = 51 + (self.row_index * self.row_height)
                self.col = self.char_space * self.col_index
                with canvas(self.device) as draw:
                    draw.text((0, 0), self.msg, font=self.font, fill=255)
                    draw.line((0, 39, 127, 39), fill=255)
                    #draw.text((0, 40), 'abcdefghijklmnopqrstu', font=self.font, fill=255)
                    #draw.text((0, 52), 'vwxyz1234567890!?$%.-', font=self.font, fill=255)
                    draw.text((0, 40), self.keyboard[:21], font=self.font, fill=255)
                    draw.text((0, 52), self.keyboard[21:], font=self.font, fill=255)
                    if self.row_index >= 0:
                        draw.text((0, 28), ' SEND  CLEAR  CANCEL', font=self.font, fill=255)
                        draw.line((self.col, self.row, self.char_size+self.col, self.row), fill=255)
                    else:
                        if self.col_index == 0:
                            draw.text((0, 28), '<SEND> CLEAR  CANCEL ', font=self.font, fill=255)
                        elif self.col_index == 1:
                            draw.text((0, 28), ' SEND <CLEAR> CANCEL ', font=self.font, fill=255)
                        elif self.col_index == 2:
                            draw.text((0, 28), ' SEND  CLEAR <CANCEL>', font=self.font, fill=255)
            elif self.mode == 3: # Main Menu
                with canvas(self.device) as draw:
                    draw.line((121,3,124,0), fill=255)                                         
                    draw.line((124,0,127,3), fill=255)                                         
                    draw.text((20, 4), 'Send New Msg', font=self.font, fill=255)
                    draw.text((20, 16), 'View Received', font=self.font, fill=255)
                    draw.text((20, 28), 'View Sent', font=self.font, fill=255)
                    draw.text((20, 40), 'View Outbound', font=self.font, fill=255)
                    draw.text((20, 52), 'Initialize keys', font=self.font, fill=255)
                    draw.line((121,60,124,63), fill=255)                                         
                    draw.line((124,63,127,60), fill=255)                              

                    draw.text((0, 4 + (12* self.row_index)), '->', font=self.font, fill=255)
                                   
            self.event.wait(0.05)
        with canvas(self.device) as draw:
            pass        

    def stop(self):
        print "Stopping OLED Display Thread."
        self.event.set()

    def reset(self):    
        GPIO.output(iodef.PIN_OLED_RESET, False)
        sleep(1)
        GPIO.output(iodef.PIN_OLED_RESET, True)

    def idle(self):
        if self.mode == 1:
            self.mode = 0

    def lock_screen(self):
        self.mode = 1


    def main_menu(self):
        self.row_index = 0
        self.mode = 3

    def create_msg(self, msg):
        if self.mode != 2 and self.mode != 0:
            self.msg = msg
            self.mode = 2
            self.row_index = 0
            self.col_index = 0
            return True
        return False

    def key_right(self):
        if self.mode == 0:
            self.mode = 1
        elif self.mode == 2:
            self.col_index += 1
            if self.row_index == -1:
                if self.col_index > 2:
                    self.col_index = 2
            elif self.col_index > 20:
                self.col_index = 0                
                if self.row_index == 0:
                    self.row_index = 1
                else:
                    self.row_index = 0

    def key_left(self):
        if self.mode == 0:
            self.mode = 1
        elif self.mode == 2:
            self.col_index -= 1
            if self.row_index == -1:
                if self.col_index < 0:
                    self.col_index = 0
            elif self.col_index < 0:
                self.col_index = 20
                if self.row_index == 1:
                    self.row_index = 0
                else:
                    self.row_index = 1

    def key_up(self):
        if self.mode == 0:
            self.mode = 1
        elif self.mode == 2:
            if self.row_index == 1:
                self.row_index = 0
            else:
                self.row_index = -1
                self.col_index = 0
        elif self.mode == 3:
            self.row_index -= 1
            if self.row_index < 0:
                self.row_index = 4

    def key_down(self):
        if self.mode == 0:
            self.mode = 1
        elif self.mode == 2:
            self.row_index += 1
            if self.row_index > 1:
                self.row_index = 1
        elif self.mode == 3:
            self.row_index += 1
            if self.row_index > 4:
                self.row_index = 0

    def key_enter(self):
        if self.mode == 0:
            self.mode = 1
        elif self.mode == 2:
            if self.row_index >= 0:
                index = (self.row_index * 21) + self.col_index
                self.msg = self.msg + self.keyboard[index:index+1]
                print self.msg
            else:
                if self.col_index == 0:
                    print "Encrypt/Send Msg: " + self.msg
                elif self.col_index == 1:
                    self.msg = ""
                elif self.col_index == 2:
                    self.msg = ""
                    self.mode = 1
 

    def key_back(self):
        if self.mode == 0:
            self.mode = 1
        elif self.mode == 2:
            self.msg = self.msg[:-1]
