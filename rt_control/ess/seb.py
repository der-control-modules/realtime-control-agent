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
        self.actuator_vip = self.actuator_vip if self.actuator_vip else 'bess.control'
        self.actuation_method = self.actuation_method if self.actuation_method else 'actuate_bess'

    @EnergyStorageSystem.power.setter
    def power(self, value: float):
        watts_value = value * 1000
        _log.debug(f'IN SEB POWER SETTER, with ACTUATOR_VIP: {self.actuator_vip},'
                   f' ACTUATION_METHOD: {self.actuation_method}, watts_value: {watts_value}')
        self.controller.vip.rpc.call(self.actuator_vip, self.actuation_method, watts_value, point='real')
