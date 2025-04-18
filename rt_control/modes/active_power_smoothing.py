from datetime import timedelta
from typing import Union

from rt_control.modes.es_control_mode import ESControlMode


class ActivePowerSmoothing(ESControlMode):
    # TODO: Implement Ramp and Mesa Mode Params arguments.
    def __init__(self, smoothing_gradient: float, lower_smoothing_limit: float, upper_smoothing_limit: float,
                 smoothing_filter_time: Union[float, timedelta], *args, **kwargs):
        super(ActivePowerSmoothing, self).__init__(*args, **kwargs)
        self.smoothing_gradient: float = smoothing_gradient
        self.lower_smoothing_limit: float = lower_smoothing_limit
        self.upper_smoothing_limit: float = upper_smoothing_limit
        self.smoothing_filter_time: timedelta = timedelta(seconds=smoothing_filter_time)\
            if not isinstance(smoothing_filter_time, timedelta) else smoothing_filter_time

    def _get_julia_mode_struct(self):
        # The only required parameter is the priority.
        es_rtc = self.CEE.EnergyStorageRTControl
        mesa_mode_params = es_rtc.MesaModeParams(self.priority)
        # Ramp will be the p_max if the values are 1000.0.
        ramp_params = es_rtc.RampParams(1000.0, 1000.0, 1000.0, 1000.0)
        return es_rtc.ActivePowerSmoothingMode(mesa_mode_params, self.smoothing_gradient, self.lower_smoothing_limit,
                                               self.upper_smoothing_limit, self.smoothing_filter_time, ramp_params)
