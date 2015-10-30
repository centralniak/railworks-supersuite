#!/usr/bin/env python

import os
import time

import g13
import raildriver


class Display(object):

    g13 = None

    def __init__(self, g13):
        self.g13 = g13

    def update(self, context):
        self.g13.lcd_set_text(0, context['loco_text'])
        self.g13.lcd_set_text(2, context['time_text'])


class Runner(object):

    interval = 1

    g13 = None
    raildriver = None

    def __init__(self):
        self.g13 = g13.LogitechLCD(g13.LCD_TYPE_MONO)
        self.raildriver = raildriver.RailDriver('C://Program Files (x86)//Steam//steamapps//common//RailWorks//plugins//RailDriver.dll')

        self.display = Display(self.g13)

        self.startup()

    def launch_macroworks_and_wait(self):
        print 'Launching MacroWorks...'
        os.startfile('C://Program Files (x86)//PI Engineering//MacroWorks 3.1//MacroWorks 3 Launch.exe')
        time.sleep(5)

    def launch_railworks(self):
        print 'Launching Railworks...'
        os.system('"C://Program Files (x86)//Steam//steamapps//common//RailWorks//RailWorks.exe" -SetFOV=75')

    def launch_tracking_and_wait(self):
        print 'Launching FaceTrackNoIR'
        os.startfile('C://Program Files (x86)//FreeTrack//FaceTrackNoIR.exe')
        time.sleep(10)

    def main(self):
        try:
            while True:
                self.update_g13()
                time.sleep(self.interval)
        except KeyboardInterrupt:
            self.g13.lcd_shutdown()

    def startup(self):
        self.launch_tracking_and_wait()
        self.launch_macroworks_and_wait()
        self.launch_railworks()
        self.g13.lcd_init()

    def update_g13(self):
        loco = self.raildriver.get_loco_name()
        time = self.raildriver.get_current_time()

        context = {
            'loco_text': 'Welcome to {loco[2]}'.format(**locals()) if loco else '',
            'time_text': '{:^26}'.format('{time:%H:%M:%S}'.format(**locals())) if time else '',
        }

        self.display.update(context)


if __name__ == '__main__':
    Runner().main()
