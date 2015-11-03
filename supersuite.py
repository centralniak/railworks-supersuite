#!/usr/bin/env python

import os
import time
import winsound

import psutil

import g13
import raildriver


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

    def update(self, new):
        self.old = self.new.copy()
        self.new = new


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
    raildriver_state_machine = None
    state_machine_log = None

    def __init__(self):
        self.g13 = g13.LogitechLCD(g13.LCD_TYPE_MONO)
        self.raildriver = raildriver.RailDriver('C://Program Files (x86)//Steam//steamapps//common//RailWorks//plugins//RailDriver.dll')
        self.raildriver_state_machine = StateMachine()

        self.display = Display(self.g13)

        self.startup()

    def close_state_machine_log(self):
        if self.state_machine_log:
            self.state_machine_log.close()
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

    def launch_macroworks_and_wait(self):
        print 'Launching MacroWorks...'
        os.startfile('C://Program Files (x86)//PI Engineering//MacroWorks 3.1//MacroWorks 3 Launch.exe')
        time.sleep(10)

    def launch_railworks(self):
        print 'Launching Railworks...'
        os.system('"C://Program Files (x86)//Steam//steamapps//common//RailWorks//RailWorks.exe" -SetFOV=75')
        time.sleep(10)  # so that the process list can update

    def launch_tracking_and_wait(self):
        print 'Launching FaceTrackNoIR'
        os.startfile('C://Program Files (x86)//FreeTrack//FaceTrackNoIR.exe')
        time.sleep(5)

    def main(self):
        loop = 0

        try:
            while self.is_railworks_running():
                loop += 1
                self.update_g13()
                if not loop % 10:  # more intensive operations should be done only every 10 loops
                    self.update_state_machine()

                    if '!LocoName' in self.raildriver_state_machine.changed_keys:
                        self.open_state_machine_log()
                        Sound.beep_rise()

                time.sleep(self.interval)
        except KeyboardInterrupt:
            self.shutdown()
        else:
            self.shutdown()

    def open_state_machine_log(self):
        if self.state_machine_log:
            self.close_state_machine_log()
        self.state_machine_log = open('state_machine_{}.log'.format(time.time()), 'a')

    def shutdown(self):
        print 'Shutting down because Railworks is done...'
        self.g13.lcd_shutdown()
        self.close_state_machine_log()

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

    def update_state_machine(self):
        new_sm = {name: self.raildriver.get_controller_value(idx) for idx, name in self.raildriver.get_controller_list()}
        new_sm['!LocoName'] = self.raildriver.get_loco_name()[2] if self.raildriver.get_loco_name() else None
        self.raildriver_state_machine.update(new_sm)
        if self.state_machine_log:
            self.state_machine_log.writelines(['{}: {}\n'.format(k, v) for k, v in new_sm.items()])


if __name__ == '__main__':
    Runner().main()
