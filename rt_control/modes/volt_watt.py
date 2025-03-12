from datetime import timedelta
from typing import List, Tuple, Union

from rt_control.modes.es_control_mode import ESControlMode


class VoltWatt(ESControlMode):
    # TODO: Implement Mesa Mode Params arguments.
    def __init__(self, reference_voltage_offset: float, volt_watt_curve: List[Tuple[float, float]],
                 gradient: float, filter_time: Union[float, timedelta],
                 lower_deadband: float, upper_deadband: float, *args, **kwargs):
        super(VoltWatt, self).__init__(*args, **kwargs)
        self.reference_voltage_offset: float = reference_voltage_offset
        self.volt_watt_curve: List[Tuple[float, float]] = volt_watt_curve
        self.gradient: float = gradient
        self.filter_time: Union[float, timedelta] = timedelta(seconds=filter_time)\
            if not isinstance(filter_time, timedelta) else filter_time
        self.lower_deadband: float = lower_deadband
        self.upper_deadband: float = upper_deadband

    def _get_julia_mode_struct(self):
        # The only required parameter is the priority.
        es_rtc = self.CEE.EnergyStorageRTControl
        return es_rtc.VoltWattMode(es_rtc.MesaModeParams(self.priority), self.reference_voltage_offset,
                            es_rtc.VertexCurve([es_rtc.Vertex(*v) for v in self.volt_watt_curve]),
                            self.gradient, self.filter_time, self.lower_deadband, self.upper_deadband)
