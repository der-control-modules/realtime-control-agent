from rt_control.modes.es_control_mode import ESControlMode

from julia.api import LibJulia
api = LibJulia.load(julia='/home/volttron/PyJuliaTesting/julia-1.10.4/bin/julia')
api.init_julia(['--project=/home/volttron/PyJuliaTesting/ctrl-eval-engine-app'])
from julia.CtrlEvalEngine.EnergyStorageRTControl import ActivePowerLimitMode, MesaModeParams


class ActivePowerLimit(ESControlMode):
    # TODO: Implement Ramp and Mesa Mode Params arguments.
    def __init__(self, maximum_charge_percentage: float, maximum_discharge_percentage: float, *args, **kwargs):
        super(ActivePowerLimit, self).__init__(*args, **kwargs)
        self.maximum_charge_percentage: float = maximum_charge_percentage
        self.maximum_discharge_percentage: float = maximum_discharge_percentage

    def _get_julia_mode_struct(self):
        # The only required parameter is the priority.
        mesa_mode_params = MesaModeParams(self.priority)
        return ActivePowerLimitMode(mesa_mode_params, self.maximum_charge_percentage, self.maximum_discharge_percentage)
