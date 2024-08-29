from rt_control.modes.es_control_mode import ESControlMode

from julia.api import LibJulia
api = LibJulia.load(julia='/home/volttron/PyJuliaTesting/julia-1.10.4/bin/julia')
api.init_julia(['--project=/home/volttron/PyJuliaTesting/ctrl-eval-engine-app'])
from julia.CtrlEvalEngine.EnergyStorageRTControl import ChargeDischargeStorageMode, MesaModeParams, RampParams


class ChargeDischargeStorage(ESControlMode):
    def _get_julia_mode_struct(self):
        # The only required parameter is the priority.
        mesa_mode_params = MesaModeParams(self.priority)
        # Ramp will be the p_max if the values are 1000.0.
        ramp_params = RampParams(1000.0, 1000.0, 1000.0, 1000.0)
        # The c_d_s_mode will follow the schedule if None is passed for the target value. It will otherwise be the last argument.
        return ChargeDischargeStorageMode(mesa_mode_params, True, ramp_params, 10.0, 90.0, None)
