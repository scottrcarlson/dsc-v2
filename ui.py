#!/usr/bin/python
# ----------------------------
# --- DSC2 UI THREAD
#----------------------------
from time import sleep
import RPi.GPIO as GPIO
import iodef
from threading import *
from yubikey import Yubikey
#from display import Display
from oled.device import ssd1306, sh1106
from oled.render import canvas
from PIL import ImageDraw, Image, ImageFont
import os

#DISPLAY MODES
m_IDLE = 0
m_LOCK = 1
m_AUTH = 2
m_COMPOSE = 3
m_MAIN_MENU = 4

main_menu = {
    0:"Send New Msg",
    1:"View Msgs",
    2:"Add a Friend",
    3:"Network Stats",
    4:"Initialize Keys",
    5:"System Reset",
    6:"Shutdown System"
}

compose_menu = {
    0:"Pretext Msg",
    1:"Empty Msg"
}

recipient_menu = {      #This will be generated based on friend list (keys exchanged)
    0:"Everyone",
    1:"Person_1",
    1:"Person_2",
    1:"Person_3",
    1:"Person_4"
}

view_msg_thread_menu = {
    0:"(*)Everyone",
    1:"Doris",
    2:"(*)Boris",
}

pretext_menu = {
    0:"Where are you?",
    1:"Where/When do you want to meet?",
    2:"I am ",
    3:"Meet you at ",
    4:"I'll be there in ",
    5:"I'm hungry, anyone want to grab some food?",
    6:"Let's grab some beers",
    7:"I'm at Bally/Paris",
    8:"I'm in SkyTalks",
    9:"I'm in 101 Presentation",
    10:"I'm in hotel room, down time."
}

test_broadcast_thread_msg = [
    "Doris 2016.08.07 13:00:",
    "Hello World",
    "Boris 2016.08.07 13:02",
    "Hello World!",
    "Bob 2016.08.07 13.05",
    "yo!"
]

keyboard = "abcdefghijklmnopqrstuvwxyz1234567890!?$%.-"



class UI(Thread):
    def __init__(self, message):
        Thread.__init__(self)
        self.event = Event()

        GPIO.add_event_detect(iodef.PIN_KEY_UP, GPIO.FALLING, callback=self.key_up, bouncetime=40)
        GPIO.add_event_detect(iodef.PIN_KEY_DOWN, GPIO.FALLING, callback=self.key_down, bouncetime=40)
        GPIO.add_event_detect(iodef.PIN_KEY_LEFT, GPIO.FALLING, callback=self.key_left, bouncetime=40)
        GPIO.add_event_detect(iodef.PIN_KEY_RIGHT, GPIO.FALLING, callback=self.key_right, bouncetime=40)
        GPIO.add_event_detect(iodef.PIN_KEY_ENTER, GPIO.FALLING, callback=self.key_enter, bouncetime=40)
        GPIO.add_event_detect(iodef.PIN_KEY_BACK, GPIO.RISING, callback=self.key_back, bouncetime=40)

        self.message = message
        self.yubikey = Yubikey(self.yubikey_status, self.yubikey_auth)
        self.yubikey.start()

        #self.display = Display()
        #self.display.start()

        self.btn_count = 0
        self.is_idle = False


        self.reset()
        # TODO: gracefully handle exception when OLED absent
        self.device = sh1106(port=1, address=0x3C)
        self.font = ImageFont.load_default()
        self.msg = ""

        #Modes
        # 0 -- Lock Screen
        # 1 -- Message Composition
        self.mode = m_IDLE
 
        self.row_index = 0
        self.col_index = 0
        self.char_space = 6
        self.char_size = 4
        self.row_height = 12
        self.screen_row_size = 5
        self.viz_min = 0
        self.viz_max = self.screen_row_size

        self.lock()
        print "Initialized UI Thread."
    
    def run(self):
        self.event.wait(1)
        while not self.event.is_set():
            #print "Handling UI Stuff"
            
            # Rework Idle Screen.. Can't be blocking!!
            #self.event.wait(5)
            #if self.is_idle:
            #    self.idle()
            #    self.is_idle = False
            #else:
            #    self.is_idle = True


            #------[IDLE]--------------------------------------------------------------------------
            if self.mode == m_IDLE:
                with canvas(self.device) as draw:
                    pass
            #------[LOCK SCREEN]-------------------------------------------------------------------       
            if self.mode == m_LOCK:
                with canvas(self.device) as draw:
                    logo = Image.open('/home/pi/dsc.png')
                    draw.bitmap((0, 20), logo, fill=1)
                    draw.text((0, 52), '5', font=self.font, fill=255)
                    #draw.text((105, 52), 'SYNC', font=self.font, fill=255)
                    draw.text((6, 10), 'dirt   simple  comms', font=self.font, fill=255)
                    draw.text((35, 52), 'insert key', font=self.font, fill=255)
            #------[AUTH SCREEN]-------------------------------------------------------------------       
            if self.mode == m_AUTH:
                with canvas(self.device) as draw:
                    logo = Image.open('/home/pi/dsc.png')
                    draw.bitmap((0, 20), logo, fill=1)
                    draw.text((0, 52), '5', font=self.font, fill=255)
                    #draw.text((105, 52), 'SYNC', font=self.font, fill=255)
                    draw.text((6, 10), 'dirt   simple  comms', font=self.font, fill=255)
                    draw.text((25, 52), 'enter password', font=self.font, fill=255)

          #------[MSG COMPOSITION]----------------------------------------------------------------
            elif self.mode == m_COMPOSE:
                self.row = 51 + (self.row_index * self.row_height)
                self.col = self.char_space * self.col_index
                with canvas(self.device) as draw:
                    draw.text((0, 0), self.msg, font=self.font, fill=255)
                    draw.line((0, 39, 127, 39), fill=255)
                    #draw.text((0, 40), 'abcdefghijklmnopqrstu', font=self.font, fill=255)
                    #draw.text((0, 52), 'vwxyz1234567890!?$%.-', font=self.font, fill=255)
                    draw.text((0, 40), keyboard[:21], font=self.font, fill=255)
                    draw.text((0, 52), keyboard[21:], font=self.font, fill=255)
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

          #------[MAIN MENU]----------------------------------------------------------------------
            elif self.mode == m_MAIN_MENU:
                with canvas(self.device) as draw:
                    draw.line((121,3,124,0), fill=255)
                    draw.line((124,0,127,3), fill=255)
                    if (self.row_index < self.viz_min):
                        self.viz_max -= self.viz_min - self.row_index
                        self.viz_min = self.row_index
                    if (self.row_index >= self.viz_max):
                        self.viz_max = self.row_index + 1
                        self.viz_min = self.viz_max - self.screen_row_size
                    #print "Row Index: ", self.row_index, " Viz_Min:", self.viz_min, " Viz_Max:", self.viz_max
                    for i in range(self.viz_min,self.viz_max):
                        draw.text((20, 4+( (i-self.viz_min) * self.row_height) ), main_menu[i], font=self.font, fill=255)
                    #draw.text((20, 16), main_menu[1], font=self.font, fill=255)
                    #draw.text((20, 28), main_menu[2], font=self.font, fill=255)
                    #draw.text((20, 40), main_menu[3], font=self.font, fill=255)
                    #draw.text((20, 52), main_menu[4], font=self.font, fill=255)
                    #draw.text((20, 4), 'Send New Msg', font=self.font, fill=255)
                    #draw.text((20, 16), 'View Received', font=self.font, fill=255)
                    #draw.text((20, 28), 'View Sent', font=self.font, fill=255)
                    #draw.text((20, 40), 'View Outbound', font=self.font, fill=255)
                    #draw.text((20, 52), 'Initialize keys', font=self.font, fill=255)
                    draw.line((121,60,124,63), fill=255)
                    draw.line((124,63,127,60), fill=255)

                    draw.text((0, 4 + (12* (self.row_index - self.viz_min))), '->', font=self.font, fill=255)
            self.event.wait(0.05)
        
        with canvas(self.device) as draw:
            pass

    def stop(self):
        print "Stopping UI Thread."
        self.yubikey.stop()
        #self.display.stop()
        self.event.wait(2)
        self.event.set()

    def reset(self):
        GPIO.output(iodef.PIN_OLED_RESET, False)
        sleep(1)
        GPIO.output(iodef.PIN_OLED_RESET, True)

    def idle(self):
        if self.mode == m_LOCK:
            self.mode = m_IDLE

    def lock(self):  #Key removed, clear any relevant data
        self.msg = ""
        self.mode = m_LOCK

    def auth(self):
        self.mode = m_AUTH

    def main_menu(self):
        self.row_index = 0
        self.mode = m_MAIN_MENU

    def create_msg(self, msg):
        if self.mode != m_COMPOSE and self.mode != m_IDLE:
            self.msg = msg
            self.mode = m_COMPOSE
            self.row_index = 0
            self.col_index = 0
            return True
        return False


    def key_up(self, channel):
        self.is_idle = False
        print "Pressed UP Key."
        #self.display.key_up()        
        if self.mode == m_IDLE:
            self.mode = m_LOCK
        elif self.mode == m_COMPOSE:
            if self.row_index == 1:
                self.row_index = 0
            else:
                self.row_index = -1
                self.col_index = 0
        elif self.mode == m_MAIN_MENU:
            self.row_index -= 1
            if self.row_index < 0:
                self.row_index = 0


    def key_down(self, channel):
        self.is_idle = False
        print "Pressed DOWN Key."
        #self.display.key_down()
        if self.mode == m_IDLE:
            self.mode = m_LOCK
        elif self.mode == m_COMPOSE:
            self.row_index += 1
            if self.row_index > 1:
                self.row_index = 1
        elif self.mode == m_MAIN_MENU:
            self.row_index += 1
            if self.row_index >= len(main_menu):
                self.row_index = len(main_menu) -1


    def key_left(self, channel):
        self.is_idle = False
        print "Pressed LEFT Key."
        #self.display.key_left()
        if self.mode == m_IDLE:
            self.mode = m_LOCK
        elif self.mode == m_COMPOSE:
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


    def key_right(self, channel):
        self.is_idle = False
        print "Pressed RIGHT Key."
        if self.mode == m_IDLE:
            self.mode = m_LOCK
        elif self.mode == m_COMPOSE:
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

        #self.display.key_right()

    def key_enter(self, channel):
        self.is_idle = False
        #self.btn_count = 0
        print "Pressed ENTER Key."
        #self.display.key_enter()
        if self.mode == m_IDLE:
            self.mode = m_LOCK
        elif self.mode == m_COMPOSE:
            if self.row_index >= 0:
                index = (self.row_index * 21) + self.col_index
                self.msg = self.msg + keyboard[index:index+1]
                #print self.msg
            else:
                if self.col_index == 0:
                    self.message.new_composed_msg(self.msg)
                elif self.col_index == 1:
                    self.msg = ""
                elif self.col_index == 2:
                    self.msg = ""
                    self.main_menu()
        elif self.mode == m_MAIN_MENU:
            print "MainMenu Selected: ", main_menu[self.row_index]
            if self.row_index == 0:
                self.row_index = 0
                self.col_index = 0
                self.mode = m_COMPOSE
            elif self.row_index == 6:
                print "Shutting down..."
                os.system("sudo shutdown -h now")


    def key_back(self, channel):
        self.is_idle = False
        self.btn_count += 1
        print "Pressed BACK Key: ", self.btn_count
        #self.display.key_back()
        if self.mode == m_IDLE:
            self.mode = m_LOCK
        elif self.mode == m_COMPOSE:
            self.msg = self.msg[:-1]


    def yubikey_status(self,is_present):
        if is_present:
            print "Yubikey Inserted"
            self.auth()
        else:
            #Perform System Wipe (Lock keys, wipe any user data from memory)
            self.lock()
            print "Yubikey Removed"

    def yubikey_auth(self, signing_key_passcode, decrypting_key_passcode):
        #Check password (i.e. attempt to unlock key chain)
        #If pass, then unlock the screen, else show error? or silence??
        self.main_menu()
