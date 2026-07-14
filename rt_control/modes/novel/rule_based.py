from rt_control.modes.es_control_mode import ESControlMode

from julia.api import LibJulia
api = LibJulia.load(julia='/home/volttron/PyJuliaTesting/julia-1.10.4/bin/julia')
api.init_julia(['--project=/home/volttron/PyJuliaTesting/ctrl-eval-engine-app'])
from julia.CtrlEvalEngine.EnergyStorageRTControl import RuleBasedController


class RuleBased(ESControlMode):
    def __init__(self, bound: float, *args, **kwargs):
        super(RuleBased, self).__init__(*args, **kwargs)
        self.bound:float = bound

    def _get_julia_mode_struct(self):
        return RuleBasedController(self.bound)
