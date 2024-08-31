from datetime import timedelta
from typing import List, Tuple, Union

from rt_control.modes.es_control_mode import ESControlMode

from julia.api import LibJulia
api = LibJulia.load(julia='/home/volttron/PyJuliaTesting/julia-1.10.4/bin/julia')
api.init_julia(['--project=/home/volttron/PyJuliaTesting/ctrl-eval-engine-app'])
from julia.CtrlEvalEngine.EnergyStorageRTControl import (FrequencyWattMode, MesaModeParams, RampParams,
                                                         Vertex, VertexCurve)


class FrequencyWatt(ESControlMode):
    # TODO: Implement Ramp and Mesa Mode Params arguments.
    def __init__(self, use_curves: bool, frequency_watt_curve: List[Tuple[float, float]],
                 low_hysteresis_curve: List[Tuple[float, float]], high_hysteresis_curve: List[Tuple[float, float]],
                 start_delay: Union[timedelta, float], stop_delay: Union[timedelta, float],
                 minimum_soc: float, maximum_soc: float, use_hysteresis: bool, use_snapshot_power: bool,
                 high_starting_frequency: float, low_starting_frequency: float, high_stopping_frequency: float,
                 low_stopping_frequency: float, high_discharge_gradient: float, low_discharge_gradient: float,
                 high_charge_gradient: float, low_charge_gradient: float, high_return_gradient: float,
                 low_return_gradient: float, *args, **kwargs):
        super(FrequencyWatt, self).__init__(*args, **kwargs)
        self.use_curves: bool = use_curves
        self.frequency_watt_curve: List[Tuple[float, float]] = frequency_watt_curve
        self.low_hysteresis_curve: List[Tuple[float, float]] = low_hysteresis_curve
        self.high_hysteresis_curve: List[Tuple[float, float]] = high_hysteresis_curve
        self.start_delay: Union[timedelta, float] = start_delay
        self.stop_delay: Union[timedelta, float] = stop_delay
        self.minimum_soc: float = minimum_soc
        self.maximum_soc: float = maximum_soc
        self.use_hysteresis: bool = use_hysteresis
        self.use_snapshot_power: bool = use_snapshot_power
        self.high_starting_frequency: float = high_starting_frequency
        self.low_starting_frequency: float = low_starting_frequency
        self.high_stopping_frequency: float = high_stopping_frequency
        self.low_stopping_frequency: float = low_stopping_frequency
        self.high_discharge_gradient: float = high_discharge_gradient
        self.low_discharge_gradient: float = low_discharge_gradient
        self.high_charge_gradient: float = high_charge_gradient
        self.low_charge_gradient: float = low_charge_gradient
        self.high_return_gradient: float = high_return_gradient
        self.low_return_gradient: float = low_return_gradient

    def _get_julia_mode_struct(self):
        # The only required parameter is the priority.
        mesa_mode_params = MesaModeParams(self.priority)
        # Ramp will be the p_max if the values are 1000.0.
        ramp_params = RampParams(1000.0, 1000.0, 1000.0, 1000.0)
        return FrequencyWattMode(mesa_mode_params, self.use_curves,
                                 VertexCurve([Vertex(*v) for v in self.frequency_watt_curve]),
                                 VertexCurve([Vertex(*v) for v in self.low_hysteresis_curve]),
                                 VertexCurve([Vertex(*v) for v in self.high_hysteresis_curve]),
                                 self.start_delay, self.stop_delay, ramp_params, self.minimum_soc, self.maximum_soc,
                                 self.use_hysteresis, self.use_snapshot_power, self.high_starting_frequency,
                                 self.low_starting_frequency, self.high_stopping_frequency, self.low_stopping_frequency,
                                 self.high_discharge_gradient, self.low_discharge_gradient, self.high_charge_gradient,
                                 self.low_charge_gradient, self.high_return_gradient, self.low_return_gradient)
