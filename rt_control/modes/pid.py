from rt_control.modes.es_control_mode import ESControlMode

class PID(ESControlMode):
    def __init__(self, resolution, kp, ti, td, *args, **kwargs):
        super(PID, self).__init__(*args, **kwargs)
        self.resolution = resolution
        self.kp = kp
        self.ti = ti
        self.td = td

    def _get_julia_mode_struct(self):
        return self.CEE.EnergyStorageRTControl.PIDController(self.resolution, self.kp, self.ti, self.td)
