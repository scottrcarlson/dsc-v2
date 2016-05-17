#!/usr/bin/python
# ----------------------------
# --- DSC2 IO Handler
#----------------------------
import RPi.GPIO as GPIO

#Pin Definitions
PIN_RADIO_IRQ   = 7
PIN_RADIO_RESET = 11
PIN_OLED_RESET  = 40
PIN_KEY_ENTER   = 37
PIN_KEY_BACK    = 38
PIN_KEY_LEFT    = 33
PIN_KEY_RIGHT   = 35
PIN_KEY_UP      = 29
PIN_KEY_DOWN    = 36

def init():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BOARD)
    
    GPIO.setup(PIN_RADIO_IRQ, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(PIN_RADIO_RESET, GPIO.OUT)    
    GPIO.setup(PIN_OLED_RESET, GPIO.OUT)
    GPIO.setup(PIN_KEY_ENTER, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(PIN_KEY_BACK, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(PIN_KEY_UP, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(PIN_KEY_DOWN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(PIN_KEY_LEFT, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(PIN_KEY_RIGHT, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.output(PIN_OLED_RESET, True)
