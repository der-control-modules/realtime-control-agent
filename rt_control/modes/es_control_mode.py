import abc
import logging

from datetime import timedelta

from importlib.metadata import version
if int(version('volttron').split('.')[0]) >= 10:
    from volttron.utils import setup_logging, get_aware_utc_now
else:
    from volttron.platform.agent.utils import setup_logging, get_aware_utc_now

from rt_control.modes import ControlMode
from rt_control.util import FixedIntervalTimeSeries

from julia.api import LibJulia
api = LibJulia.load(julia='/home/volttron/PyJuliaTesting/julia-1.10.4/bin/julia')
api.init_julia(['--project=/home/volttron/PyJuliaTesting/ctrl-eval-engine-app'])
from julia import CtrlEvalEngine, Dates
from julia.CtrlEvalEngine import SchedulePeriod, VariableIntervalTimeSeries
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
        use_cases = self._get_julia_use_cases_vector(start_time)

        # TODO: Move this to agent with conditional import?
        controller = CtrlEvalEngine.EnergyStorageRTControl.MesaController([mode], Dates.Minute(5))
        # TODO: Should this be calling the controller or mode control function?
        output = CtrlEvalEngine.control(ess, controller, schedule_period, use_cases, start_time, sp_progress)
        return output.value[0]  # TODO: Is there really a use for returning a FixedIntervalTimeSeries as in ESControl?

    def _get_julia_use_cases_vector(self, now):
        # TODO: This is hard coded for testing. Replace this with something useful.
        use_cases_characteristics = {
            "Energy Arbitrage": {
                "inputs": {
                    "actualEnergyPrice": {
                        "type": "file_upload",
                        "optionSelected": "Custom",
                        "wholesaleMarket": {
                            "iso": "ERCOT",
                            "zone": "HB_BUSAVG",
                            "years": ["2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023"]
                        },
                        "file": {"0": {}},
                        "fileName": "template_energy_arbitrage.csv",
                        "fileKey": "template_energy_arbitrage.csv",
                        "error": None
                    },
                    "forecastEnergyPrice": {
                        "type": "file_upload",
                        "optionSelected": "None"
                    }
                },
                "data": {
                    "actualEnergyPrice": {
                        "Time": ["2018-01-01T00:00", "2018-01-01T01:00"],
                        "EnergyPrice_per_MWh": [147.07]
                    }
                }
            }
        }
        setting = CtrlEvalEngine.SimSetting(now, now + timedelta(hours=1), 20)
        return CtrlEvalEngine.get_use_cases(use_cases_characteristics, setting)

    @abc.abstractmethod
    def _get_julia_mode_struct(self):
        pass
