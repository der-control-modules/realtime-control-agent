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

    # Modes are organized into category subpackages. When a config entry does not
    # specify an explicit module_name, the factory searches these in order for a module
    # named after the snake_cased class_name.
    _MODE_SUBPACKAGES = ('active', 'reactive', 'emergency', 'novel')

    @classmethod
    def factory(cls, controller, ess, use_cases, config):
        class_name = config.pop('class_name')
        module_name = config.pop('module_name', None)
        module = None
        if module_name:
            module = import_module(module_name)
        else:
            snake = camel_to_snake(class_name)
            # Search each category subpackage, then fall back to the modes root for
            # backward compatibility with any flat modules.
            candidates = [f'rt_control.modes.{pkg}.{snake}' for pkg in cls._MODE_SUBPACKAGES]
            candidates.append(f'rt_control.modes.{snake}')
            for candidate in candidates:
                try:
                    module = import_module(candidate)
                    if hasattr(module, class_name):
                        break
                except ModuleNotFoundError:
                    continue
            if module is None or not hasattr(module, class_name):
                raise ModuleNotFoundError(
                    f'Could not locate mode class {class_name!r} in any of: {candidates}')
        _log.info(f'Configuring class: {class_name} from module: {module.__name__}')
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

    def _get_julia_mode_struct(self):
        # Subclasses that support a Julia fallback (use_julia=True) override this to
        # build their pyjulia mode struct. Base modes have no Julia equivalent.
        raise NotImplementedError(f'{type(self).__name__} has no Julia fallback implementation.')

    def _julia_control(self, schedule_period, start_time, sp_progress):
        # Shared pyjulia fallback: mirrors ESControlMode.control (es_control_mode.py).
        # Imports julia lazily so native modes load without a Julia runtime.
        from julia import CtrlEvalEngine, Dates
        from julia.CtrlEvalEngine import SchedulePeriod, VariableIntervalTimeSeries
        from julia.CtrlEvalEngine.EnergyStorageSimulators import MockSimulator, MockES_Specs, MockES_States
        sp_progress = VariableIntervalTimeSeries([start_time], [])
        ess = MockSimulator(MockES_Specs(*self.ess.specs.dump()), MockES_States(*self.ess.states.dump()))
        mode = self._get_julia_mode_struct()
        schedule_period = SchedulePeriod(*schedule_period.dump())
        use_cases = [u.to_julia() for u in self.use_cases]
        controller = CtrlEvalEngine.EnergyStorageRTControl.MesaController([mode], Dates.Minute(5))
        output = CtrlEvalEngine.control(ess, controller, schedule_period, use_cases, start_time, sp_progress)
        return output.value[0]


class ReactiveMesaMode(MesaMode):
    """Base for MESA reactive-power modes (Constant VAr, Fixed Power Factor,
    Volt-VAr, Watt-VAr). These contribute reactive power (kVAR) rather than active
    power, so control() is inert on the active axis and control_reactive() returns
    the mode's reactive-power contribution. The agent accumulates control_reactive()
    across reactive modes into a separate Q command.
    """
    def control(self, schedule_period, start_time, sp_progress) -> float:
        return 0.0

    @abc.abstractmethod
    def control_reactive(self, schedule_period, start_time, sp_progress) -> float:
        pass


class EmergencyMesaMode(MesaMode):
    """Base for MESA emergency ride-through modes (voltage/frequency ride-through).

    These do not contribute power; they gate the final summed output. After the
    controller sums active/reactive power across all normal modes, it calls gate()
    on each emergency mode (in priority order) to apply trip / momentary-cessation
    overrides, per IEEE 1547 ride-through semantics.
    """
    def control(self, schedule_period, start_time, sp_progress) -> float:
        return 0.0

    @abc.abstractmethod
    def gate(self, active_power: float, reactive_power: float, start_time) -> tuple:
        """Return the (active_power, reactive_power) tuple after applying any
        trip or momentary-cessation override. Pass values through unchanged when
        the measured signal is within normal (ride-through) bounds."""
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


class VertexCurve:
    """Piecewise-linear curve defined by (x, y) vertices.

    Accepts either Vertex instances or (x, y) tuples/lists so it can be built
    directly from JSON config (e.g. [[v0, y0], [v1, y1], ...]). interpolate(x)
    performs a piecewise-linear lookup, clamping to the endpoint y-values for x
    outside the defined range.
    """
    def __init__(self, vertices):
        self.vertices = sorted(
            [v if isinstance(v, Vertex) else Vertex(*v) for v in vertices],
            key=lambda v: v.x)

    def interpolate(self, x: float) -> float:
        if not self.vertices:
            return 0.0
        if x <= self.vertices[0].x:
            return self.vertices[0].y
        if x >= self.vertices[-1].x:
            return self.vertices[-1].y
        for left, right in zip(self.vertices, self.vertices[1:]):
            if left.x <= x <= right.x:
                if right.x == left.x:
                    return left.y
                fraction = (x - left.x) / (right.x - left.x)
                return left.y + fraction * (right.y - left.y)
        return self.vertices[-1].y  # Unreachable given the endpoint guards above.

    def dump(self):
        return [v.dump() for v in self.vertices]
