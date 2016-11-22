#!/usr/bin/env python

import csv
import datetime
import os
import time
import winsound

import psutil
import pywinusb.hid
import raildriver

import g13


class Display(object):

    g13 = None

    def __init__(self, g13):
        self.g13 = g13

    def update(self, context):
        self.g13.lcd_set_text(0, context['loco_text'])
        self.g13.lcd_set_text(2, context['time_text'])


class StateMachine(object):

    old = {}
    new = {}

    @property
    def changed(self):
        return self.old != self.new

    @property
    def changed_keys(self):
        all_keys = set(self.old.keys() + self.new.keys())
        changed_keys = []
        for key in all_keys:
            if self.old.get(key) != self.new.get(key):
                changed_keys.append(key)
        return changed_keys

    def __getitem__(self, item):
        return self.new.get(item)

    def keys(self):
        return self.new.keys()

    def update(self, new):
        self.old = self.new.copy()
        self.new = new.copy()


class Sound(object):

    @staticmethod
    def beep_drop():
        for hz in [6000, 4000, 2000]:
            winsound.Beep(hz, 100)

    @staticmethod
    def beep_rise():
        for hz in [2000, 4000, 6000]:
            winsound.Beep(hz, 100)


class Runner(object):

    interval = 0.5

    g13 = None
    raildriver = None
    state_machine = None
    state_machine_log = None

    input_check_iterations = 0
    input_check_started = None

    def __init__(self):
        self.g13 = g13.LogitechLCD(g13.LCD_TYPE_MONO)
        self.raildriver = raildriver.RailDriver()
        self.state_machine = StateMachine()

        self.display = Display(self.g13)

        self.startup()

    def close_state_machine_log(self):
        self.state_machine_log = None

    def is_railworks_running(self):
        for process in psutil.process_iter():
            try:
                process_name = process.name()
            except psutil.NoSuchProcess:
                pass
            else:
                if process_name.lower() == 'railworks.exe':
                    return True
        return False

    def launch_dispatcher(self):
        print 'Generating work order...'
        os.chdir('C://Program Files (x86)//Steam//steamapps//common//RailWorks')
        os.startfile('C://Users//Piotr//OpenSource//railworks-dispatcher//venv//Scripts//python.exe C://Users//Piotr//OpenSource//railworks-dispatcher//dispatcher.py 1')
        time.sleep(15)

    def launch_dsd(self):
        print 'Launching railworks-dsd...'
        os.startfile('C://Users//Piotr//OpenSource//railworks-dsd//venv//Scripts//railworksdsd.exe')

    def launch_input_check(self):
        print 'Doing an input check on the DSD...'
        usb = pywinusb.hid.HidDeviceFilter(product_id=0x00ff, vendor_id=0x05f3).get_devices()[0]
        usb.open()

        def handler(data):
            self.input_check_iterations += 1
            print self.input_check_iterations, data

        usb.set_raw_data_handler(handler)
        self.input_check_started = datetime.datetime.now()

        while self.input_check_iterations < 10:
            if (datetime.datetime.now() - self.input_check_started).total_seconds() > 10:
                input('Not enough input received within 10 seconds. Quitting...')
                raise RuntimeError('Not enough input received within 10 seconds')
            time.sleep(.5)

        print 'Input check OK ({})'.format(self.input_check_iterations)

    def launch_macroworks_and_wait(self):
        print 'Launching MacroWorks...'
        os.startfile('C://Program Files (x86)//PI Engineering//MacroWorks 3.1//MacroWorks 3 Launch.exe')
        time.sleep(15)

    def launch_railworks(self):
        print 'Launching Railworks...'
        # os.system('"C://Program Files (x86)//Steam//steamapps//common//RailWorks//RailWorks.exe" -SetFOV=75')
        os.system('"C://Program Files (x86)//Steam//steamapps//common//RailWorks//RailWorks.exe"')
        time.sleep(10)  # so that the process list can update

    def launch_tracking_and_wait(self):
        print 'Launching FaceTrackNoIR...'
        os.startfile('C://Program Files (x86)//FreeTrack//FaceTrackNoIR.exe')
        time.sleep(5)

    def main(self):
        loop = 0

        try:
            while self.is_railworks_running():
                loop += 1
                self.update_g13()

                if not loop % 10:  # more intensive operations should be done only every 10 loops
                    if '!LocoName' in self.state_machine.changed_keys:
                        self.open_state_machine_log()
                        Sound.beep_rise()
                    self.update_state_machine()

                time.sleep(self.interval)
        except KeyboardInterrupt:
            self.shutdown()
        else:
            self.shutdown()

    def open_state_machine_log(self):
        safe_loconame = ''.join([c for c in self.raildriver.get_loco_name()[2] if c.isalpha() or c.isdigit()])
        filename = 'logs/state_machine_{}_{}.csv'.format(int(time.time()), safe_loconame)
        fieldnames = sorted(set(self.state_machine.keys() + ['!Time']))
        self.state_machine_log = csv.DictWriter(open(filename, 'wb'), fieldnames=fieldnames)
        self.state_machine_log.writeheader()

    def shutdown(self):
        print 'Shutting down because Railworks is done...'
        self.g13.lcd_shutdown()
        self.close_state_machine_log()
        self.shutdown_dsd()

    def shutdown_dsd(self):
        print 'Shutting down railworks-dsd...'
        for process in psutil.process_iter():
            try:
                process_name = process.name()
            except psutil.NoSuchProcess:
                pass
            else:
                if process_name.lower() == 'railworksdsd.exe':
                    process.kill()

    def startup(self):
        self.launch_input_check()
        self.launch_dsd()
        self.launch_tracking_and_wait()
        # self.launch_dispatcher()
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

    def update_state_machine(self):
        new_sm = {name: self.raildriver.get_current_controller_value(idx) for idx, name in self.raildriver.get_controller_list()}
        new_sm['!LocoName'] = self.raildriver.get_loco_name()[2] if self.raildriver.get_loco_name() else None
        self.state_machine.update(new_sm)
        if self.state_machine_log:
            del new_sm['!LocoName']
            new_sm['!Time'] = '{0:%H:%M:%S}'.format(self.raildriver.get_current_time())

            # @TODO: fix this properly
            try:
                self.state_machine_log.writerow(self.state_machine.new)
            except ValueError:
                self.open_state_machine_log()


if __name__ == '__main__':
    Runner().main()
