from rt_control.modes.es_control_mode import ESControlMode

from julia.api import LibJulia
api = LibJulia.load(julia='/home/volttron/PyJuliaTesting/julia-1.10.4/bin/julia')
api.init_julia(['--project=/home/volttron/PyJuliaTesting/ctrl-eval-engine-app'])
from julia.CtrlEvalEngine.EnergyStorageRTControl import PIDController


class PID(ESControlMode):
    def __init__(self, resolution, kp, ti, td, *args, **kwargs):
        super(PID, self).__init__(*args, **kwargs)
        self.resolution = resolution
        self.kp = kp
        self.ti = ti
        self.td = td

    def _get_julia_mode_struct(self):
        return PIDController(self.resolution, self.kp, self.ti, self.td)
