from rt_control.ess import EnergyStorageSystem


class SebBESS(EnergyStorageSystem):
    def __init__(self, controller, config):
        super(SebBESS, self).__init__(controller, config)
        self.actuator_vip = self.actuator_vip if self.actuator_vip else 'bess.control'
        self.actuation_method = self.actuation_method if self.actuation_method else 'actuate_bess'

    @power.setter
    def power(self, value: float):
        self.controller.vip.rpc.call(self.actuator_vip, self.actuation_method, value, point='real')
