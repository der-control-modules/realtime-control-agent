from rt_control.modes.es_control_mode import ESControlMode

from julia.api import LibJulia
api = LibJulia.load(julia='/home/volttron/PyJuliaTesting/julia-1.10.4/bin/julia')
api.init_julia(['--project=/home/volttron/PyJuliaTesting/ctrl-eval-engine-app'])
from julia.CtrlEvalEngine.EnergyStorageRTControl import AGCMode, MesaModeParams, RampParams


class AGC(ESControlMode):
    # TODO: Implement Ramp and Mesa Mode Params arguments.
    def __init__(self, minimum_usable_soc: float, maximum_usable_soc: float, *args, **kwargs):
        super(AGC, self).__init__(*args, **kwargs)
        self.minimum_usable_soc: float = minimum_usable_soc
        self.maximum_usable_soc: float = maximum_usable_soc

    def _get_julia_mode_struct(self):
        # The only required parameter is the priority.
        mesa_mode_params = MesaModeParams(self.priority)
        # Ramp will be the p_max if the values are 1000.0.
        ramp_params = RampParams(1000.0, 1000.0, 1000.0, 1000.0)
        return AGCMode(mesa_mode_params, True, ramp_params, self.minimum_usable_soc, self.maximum_usable_soc)
