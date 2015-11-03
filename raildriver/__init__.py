import ctypes
import datetime


class RailDriver(object):
    """
    RailDriver.dll interface. To be eventually moved out to a separate project.
    """

    _restypes = {
        'GetControllerList': ctypes.c_char_p,
        'GetLocoName': ctypes.c_char_p,
        'GetControllerValue': ctypes.c_float,
    }

    dll = None

    def __init__(self, dll_location):
        self.dll = ctypes.cdll.LoadLibrary(dll_location)
        self._set_dll_restypes()

    # @TODO: try to read the location of the dll from Windows registry

    def _set_dll_restypes(self):
        for function_name, restype in self._restypes.items():
            getattr(self.dll, function_name).restype = restype

    def get_loco_name(self):
        ret_str = self.dll.GetLocoName()
        if not ret_str:
            return
        vendor, package, full_name = ret_str.split('.:.')
        return vendor, package, full_name

    def get_controller_list(self):
        ret_str = self.dll.GetControllerList()
        return enumerate(ret_str.split('::'))

    def get_controller_value(self, idx):
        ret_float = self.dll.GetControllerValue(idx, 0)
        return ret_float

    def get_current_time(self):
        # time is stored in controller values 406 to 408
        hms = [int(self.dll.GetControllerValue(i, 0)) for i in range(406, 409)]
        return datetime.time(*hms)
