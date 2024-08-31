from rt_control.modes.es_control_mode import ESControlMode

from julia.api import LibJulia
api = LibJulia.load(julia='/home/volttron/PyJuliaTesting/julia-1.10.4/bin/julia')
api.init_julia(['--project=/home/volttron/PyJuliaTesting/ctrl-eval-engine-app'])
from julia.CtrlEvalEngine.EnergyStorageRTControl import AMAController


# TODO: AMAController should probably be implemented directly from the python code
#  instead of wrapping the python-wrapped julia code again.
class ChargeDischargeStorage(ESControlMode):
    def _get_julia_mode_struct(self):
        return AMAController()
