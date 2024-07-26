import logging

from importlib.metadata import version
if int(version('volttron').split('.')[0]) >= 10:
    from volttron.utils import setup_logging
else:
    from volttron.platform.agent.utils import setup_logging

from rt_control.ess import EnergyStorageSystem

setup_logging()
_log = logging.getLogger(__name__)


class SebBESS(EnergyStorageSystem):
    def __init__(self, controller, config):
        super(SebBESS, self).__init__(controller, config)
        _log.debug('######### IS SEB BESS CONSTRUCTOR')
        self.actuator_vip = self.actuator_vip if self.actuator_vip else 'bess.control'

    @EnergyStorageSystem.power.setter
    def power(self, value: float):
        watts_value = round(value * 1000, self.rounding_precision)
        actuation_method = 'charge' if watts_value < 0.0 else 'discharge' if watts_value > 0.0 else 'off'
        _log.debug(f'IN SEB POWER SETTER, with ACTUATOR_VIP: {self.actuator_vip},'
                   f' ACTUATION_METHOD: {self.actuation_method}, watts_value: {watts_value}')
        kwargs = {'point': 'real'} if actuation_method in ['charge', 'discharge'] else {}
        self.controller.vip.rpc.call(self.actuator_vip, actuation_method, watts_value, **kwargs).get()
