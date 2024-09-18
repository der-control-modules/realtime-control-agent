import abc
import logging

from importlib.metadata import version
if int(version('volttron').split('.')[0]) >= 10:
    from volttron.utils import setup_logging
else:
    from volttron.platform.agent.utils import setup_logging

from rt_control.modes import ControlMode
from rt_control.util import FixedIntervalTimeSeries

from julia.api import LibJulia
api = LibJulia.load(julia='/home/volttron/PyJuliaTesting/julia-1.10.4/bin/julia')
api.init_julia(['--project=/home/volttron/PyJuliaTesting/ctrl-eval-engine-app'])
from julia import CtrlEvalEngine, Dates
# noinspection PyUnresolvedReferences
from julia.CtrlEvalEngine import SchedulePeriod, VariableIntervalTimeSeries
# noinspection PyUnresolvedReferences
from julia.CtrlEvalEngine.EnergyStorageSimulators import MockSimulator, MockES_Specs, MockES_States

setup_logging()
_log = logging.getLogger(__name__)

class ESControlMode(ControlMode):
    def __init__(self, *args, **kwargs):
        super(ESControlMode, self).__init__(*args, **kwargs)

    def control(self, schedule_period, start_time, sp_progress) -> FixedIntervalTimeSeries:
        # TODO: Should this really be the start_time? Should it be created on each control call?
        sp_progress = VariableIntervalTimeSeries([start_time], []) # TODO: Should this be an instance variable?
        ess = MockSimulator(MockES_Specs(*self.ess.specs.dump()), MockES_States(*self.ess.states.dump()))
        mode = self._get_julia_mode_struct()
        schedule_period = SchedulePeriod(*schedule_period.dump())
        use_cases = [u.to_julia() for u in self.use_cases]

        # TODO: Move this to agent with conditional import?
        controller = CtrlEvalEngine.EnergyStorageRTControl.MesaController([mode], Dates.Minute(5))
        # TODO: Should this be calling the controller or mode control function?
        output = CtrlEvalEngine.control(ess, controller, schedule_period, use_cases, start_time, sp_progress)
        return output.value[0]  # TODO: Is there really a use for returning a FixedIntervalTimeSeries as in ESControl?

    @abc.abstractmethod
    def _get_julia_mode_struct(self):
        pass
