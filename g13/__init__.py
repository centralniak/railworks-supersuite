import ctypes
import os


LCD_TYPE_MONO = 0x00000001  # 26 x 4
LCD_TYPE_COLOR = 0x00000002


class LogitechLCD(object):

    dll = None

    lcd_height = None
    lcd_type = None
    lcd_width = None

    def __init__(self, lcd_type):
        dll_location = 'LogitechLcd.dll'
        self.dll = ctypes.cdll.LoadLibrary(dll_location)

        self.lcd_type = lcd_type
        if lcd_type == LCD_TYPE_MONO:
            self.lcd_height = 4
            self.lcd_width = 26

    def __enter__(self):
        self.lcd_init()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.lcd_shutdown()

    def lcd_init(self):
        self.dll.LogiLcdInit('g13', 0x00000001)

    def lcd_set_text(self, line_index, text):
        if self.lcd_type == LCD_TYPE_MONO:
            self.dll.LogiLcdMonoSetText(line_index, ctypes.c_wchar_p(text))
        else:
            raise NotImplementedError
        self.dll.LogiLcdUpdate()

    def lcd_shutdown(self):
        self.dll.LogiLcdShutdown()
