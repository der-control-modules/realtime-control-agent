import logging

from importlib.metadata import version

if int(version('volttron').split('.')[0]) >= 10:
    from volttron.utils import setup_logging
else:
    from volttron.platform.agent.utils import setup_logging
from rt_control.ess import EnergyStorageSystem

setup_logging()
_log = logging.getLogger(__name__)

class FakeESS(EnergyStorageSystem):
    def __init__(self, controller, config):
        super(FakeESS, self).__init__(controller, config)
        _log.debug('######### IN Fake ESS CONSTRUCTOR')

    @EnergyStorageSystem.power_command.setter
    def power_command(self, value: float):
        _log.debug(f'Actuating command of: {value}')
        # Store the power command as the power and power_command.
        self.states.power = value
        self.states.power_command = value
