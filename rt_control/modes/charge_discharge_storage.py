from rt_control.modes.es_control_mode import ESControlMode
from typing import Union


class ChargeDischargeStorage(ESControlMode):
    # TODO: Implement Ramp and Mesa Mode Params arguments.
    def __init__(self, minimum_reserve_percent: float = 10.0, maximum_reserve_percent: float = 90.0,
                 active_power_target: Union[float, None] = None, *args, **kwargs):
        super(ChargeDischargeStorage, self).__init__(*args, **kwargs)
        self.minimum_reserve_percent: float = minimum_reserve_percent
        self.maximum_reserve_percent: float = maximum_reserve_percent
        # None for the target will enable schedule following.
        self.active_power_target: Union[float, None] = active_power_target

    def _get_julia_mode_struct(self):
        # The only required parameter is the priority.
        es_rtc = self.CEE.EnergyStorageRTControl
        mesa_mode_params = es_rtc.MesaModeParams(self.priority)
        # Ramp will be the p_max if the values are 1000.0.
        ramp_params = es_rtc.RampParams(1000.0, 1000.0, 1000.0, 1000.0)
        # The c_d_s_mode will follow the schedule if None is passed for the target value. It will otherwise be the last argument.
        return es_rtc.ChargeDischargeStorageMode(mesa_mode_params, True, ramp_params, self.minimum_reserve_percent,
                                          self.maximum_reserve_percent, self.active_power_target)
