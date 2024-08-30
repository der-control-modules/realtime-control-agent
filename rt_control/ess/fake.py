import logging

if int(version('volttron').split('.')[0]) >= 10:
    from volttron.utils import setup_logging
else:
    from volttron.platform.agent.utils import setup_logging
from rt_control.ess import EnergyStorageSystem

setup_logging()
_log = logging.getLogger(__name__)

class FakeESS(EnergyStorageSystem):
    @EnergyStorageSystem.power_command.setter
    def power_command(self, value: float):
        _log.debug(f'Actuating command of: {value}')
        self.states.power = value  # Sets the value without
