import abc
import logging

from datetime import datetime, timedelta
from importlib import import_module
from typing import Iterable

from importlib.metadata import distribution, PackageNotFoundError
try:
    distribution('volttron-core')
    from volttron.client.logs import setup_logging
    from volttron.utils import get_aware_utc_now
except PackageNotFoundError:
    from volttron.platform.agent.utils import setup_logging, get_aware_utc_now

from rt_control.ess import EnergyStorageSystem
from rt_control.use_cases import UseCase
from rt_control.util import camel_to_snake

setup_logging()
_log = logging.getLogger(__name__)


class ControlMode:
    def __init__(self, controller, ess: EnergyStorageSystem, use_cases: Iterable[UseCase], priority: int = 0, *_, **__):
        self.config = {}
        self.controller = controller
        self.ess: EnergyStorageSystem = ess
        self.priority: int = priority
        self.use_cases = use_cases
        self.wip: list = [] # TODO: Does this grow forever? That would be bad....

    @abc.abstractmethod
    def control(self, schedule_period, start_time, sp_progress) -> float:
        pass

    def previous_wip(self):
        wip_length = len(self.wip)
        previous_idx = wip_length - 1 if wip_length > 1 else 1
        return self.wip[previous_idx]

    @classmethod
    def factory(cls, controller, ess, use_cases, config):
        class_name = config.pop('class_name')
        module = config.pop('module_name', 'rt_control.modes.' + camel_to_snake(class_name))
        _log.info(f'Configuring class: {class_name} from module: {module}')
        module = import_module(module)
        mode_class = getattr(module, class_name)
        if 'ESControlMode' in str(mode_class.__mro__):
            if controller.cee_app_path:
                config['ctrl_eval_engine_app_path'] = controller.cee_app_path
            if controller.julia_path:
                config['julia_path'] = controller.julia_path
        mode = mode_class(controller=controller, ess=ess, use_cases=use_cases, **config)
        mode.config = config
        return mode


class MesaMode(ControlMode):
    def __init__(self, time_window: datetime = None, ramp_time: timedelta = None, reversion_timeout: timedelta = None,
                 *args, **kwargs):
        # TODO: The ramp rates are in units of a tenth of a percent per second
        #  -- i.e. divide by 1000 in constructor to get and store multiplier.
        super(MesaMode, self).__init__(*args, **kwargs)
        self.ramp_time: timedelta = ramp_time
        self.reversion_timeout: timedelta = reversion_timeout
        self.time_window: datetime = time_window

    @abc.abstractmethod
    def control(self, schedule_period, start_time, sp_progress) -> float:
        pass


class RampParams:
    def __init__(self, ramp_up_time_constant: float = None, ramp_down_time_constant: float = None,
                 discharge_ramp_up_rate: float = 1000, discharge_ramp_down_rate: float = 1000,
                 charge_ramp_up_rate: float = 1000, charge_ramp_down_rate: float = 1000):
        self.charge_ramp_down_rate: float = charge_ramp_down_rate
        self.charge_ramp_up_rate: float = charge_ramp_up_rate
        self.discharge_ramp_down_rate: float = discharge_ramp_down_rate
        self.discharge_ramp_up_rate: float = discharge_ramp_up_rate
        self.ramp_down_time_constant: float = ramp_down_time_constant
        self.ramp_up_time_constant: float = ramp_up_time_constant

    def apply_ramps(self, ess: EnergyStorageSystem, current_power: float, target_power: float):
        # TODO: Ramp rates being in kW/s, they should be multiplied by the resolution,
        #  but how does this work with longer resolutions, as it will just jump?
        # TODO: Assuming ramp rate is percentage per second of p_max or p_min.
        #  The actual units in DNP3 spec are just percent per second.
        #  Should this be percent of requested jump in power per second instead?
        if target_power > current_power and target_power >= 0:
            # TODO: This assumes percent per second refers to percent of max/min power.
            allowed_power_change = min(target_power - current_power,
                                       self.discharge_ramp_up_rate / 1000 * ess.maximum_power)
        elif current_power > target_power >= 0:
            allowed_power_change = min(target_power - current_power,
                                       self.discharge_ramp_down_rate / 1000 * ess.maximum_power)
        elif current_power < target_power < 0:
            allowed_power_change = max(target_power - current_power, self.charge_ramp_up_rate / 1000 * ess.minimum_power)
        elif target_power < current_power and target_power < 0:
            allowed_power_change = max(target_power - current_power, self.charge_ramp_down_rate / 1000 * ess.minimum_power)
        else:
            allowed_power_change = 0.0
        return current_power + allowed_power_change

    def apply_time_constants(self, current_power: float, target_power: float):
        # Using time constants, not ramps.
        # timeSinceStart = currentTime - startTime
        # timeUntilEnd = endTime - currentTime
        allowed_power_change = 0.0
        return current_power + allowed_power_change

class Vertex:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    def dump(self):
        return self.x, self.y
