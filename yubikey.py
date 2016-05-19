#!/usr/bin/python
# ----------------------------
# --- Yubkikey Helper Classes
#----------------------------

from threading import *
import pyudev, gobject
from pyudev.glib import GUDevMonitorObserver

MIT_YUBIKEY_VENDOR_ID = 0x1050
MIT_YUBIKEY_PRODUCT_ID = 0x0010

class Yubikey(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.event = Event()
        print "Initializing Yubikey Thread Thread."
        self.mainloop = None

    def run(self):
        print "Startings Yubikey Thread Thread."
        context = pyudev.Context()
        monitor = pyudev.Monitor.from_netlink(context)
        observer = GUDevMonitorObserver(monitor)
        observer.connect('device-added', self.device_added_callback)
        observer.connect('device-removed', self.device_removed_callback)
        monitor.enable_receiving()

        #self.mainloop = gobject.MainLoop()
        #self.mainloop.run()
        self.event.wait(1)

        while not self.event.is_set():
            print "Handling Yubikey Stuff"

            self.event.wait(15)

    def device_added_callback(self,*args):
        try:
            if int(args[1].attributes.asstring('idVendor'), 16) == MIT_YUBIKEY_VENDOR_ID and int(args[1].attributes.asstring('idProduct'), 16) == MIT_YUBIKEY_PRODUCT_ID == MIT_YUBIKEY_PRODUCT_ID:
                print "yubikey inserted"
        except:
            pass

    def device_removed_callback(self,*args):
        if "event" in args[1].sys_path:
            print "usb device removed"


    def stop(self):
        print "Stopping Yubikey Thread."
        #self.mainloop.quit()
        self.event.set()
