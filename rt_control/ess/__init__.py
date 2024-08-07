import logging

from gevent import Timeout
from importlib import import_module
from importlib.metadata import version
from typing import Callable

if int(version('volttron').split('.')[0]) >= 10:
    from volttron.utils import setup_logging
else:
    from volttron.platform.agent.utils import setup_logging

from rt_control.util import camel_to_snake

setup_logging()
_log = logging.getLogger(__name__)


class ESSSpecs:
    def __init__(self, power_capacity_kw: float = 0.0, energy_capacity_kwh: float = 0.0):
        self.power_capacity_kw: float = power_capacity_kw
        self.energy_capacity_kwh: float = energy_capacity_kwh
        # self.tset_degree_c::Float64 =
        # self.C0::Float64 = # self-discharge coefficient
        # self.C0Hot::Float64 = # self-discharge coefficient adjustment when ambient temperature is higher than Tset
        # self.C0Cold::Float64 = # self-discharge coefficient adjustment when ambient temperature is lower than Tset
        # self.C_p::Float64 = # discharging efficiency
        # self.C_n::Float64 = # charging efficiency
        # self.H_p::Float64 = # discharging efficiency degradation coef
        # self.H_n::Float64 =  # charging efficiency degradation coef
        # self.D::NTuple{3, Float64}  = # degradation coefficients

class ESSStates:
    def __init__(self):
        self.soc: float = 0.0
        self.d: float = 0.0
        self.power: float = 0.0
        self.power_command: float = 0.0


class EnergyStorageSystem:
    def __init__(self, controller, config):
        self.controller = controller
        self.specs = ESSSpecs(config.get('power_capacity_kw', 0.0), config.get('energy_capacity_kwh', 0.0))
        self.states = ESSStates()

        self.bess_topic = config.get('bess_topic')
        self.soc_point = config.get('soc_point')
        self.power_reading_point = config.get('power_reading_point')

        self.power_command_point = config.get('power_command_point')
        self.power_command_topic = config.get('power_command_topic', self.bess_topic)

        self.actuator_vip = config.get('actuator_vip')
        self.actuation_method = config.get('actuation_method')
        self.actuation_kwargs = config.get('actuation_kwargs', {})
        self.rounding_precision = config.get('rounding_precision', 2)
        if self.bess_topic:
            if self.soc_point:
                self.controller.vip.pubsub.subscribe('pubsub', self.bess_topic,
                                                self._ingest_state(key='soc', point_name=self.soc_point))
            if self.power_reading_point:
                self.controller.vip.pubsub.subscribe('pubsub', self.bess_topic,
                                                self._ingest_state(key='power', point_name=self.power_reading_point))
            if self.power_command_point:
                self.controller.vip.pubsub.subscribe('pubsub', self.bess_topic,
                                                self._ingest_state(key='power_command', point_name=self.power_command_point))

    def _ingest_state(self, key: str, point_name: str) -> Callable:
        def func(_, __, ___, ____, _____, message):
            if isinstance(message, list):
                message = message[0]
            value =  message.get(point_name, getattr(self.states, key))
            setattr(self.states, key, value)
        return func

    @property
    def minimum_energy(self) -> float:
        return 0.0

    @property
    def maximum_energy(self) -> float:
        return self.specs.energy_capacity_kwh if self.specs.energy_capacity_kwh else 0.0

    @property
    def minimum_power(self) -> float:
        return 0.0

    @property
    def maximum_power(self) ->float:
        return self.specs.power_capacity_kw if self.specs.power_capacity_kw else 0.0

    @property
    def energy_state(self) -> float:
        # if any(x is None for x in [self.soc, self.specs.energy_capacity_kwh]):
        #     return None
        return self.soc / 100 * self.specs.energy_capacity_kwh if self.soc and self.specs.energy_capacity_kwh else 0.0

    @property
    def soc(self) -> float:
        return self.states.soc if self.states.soc else 0.0

    @property
    def power(self) -> float:
        # if self.states.power is None:
        #     return None
        return self.states.power / 1000 if self.states.power else 0.0

    @property
    def power_command(self) -> float:
        return self.states.power_command / 1000 if self.states.power_command else 0.0

    @power_command.setter
    def power_command(self, value: float):
        value = round(value, self.rounding_precision)
        try:
            self.controller.vip.rpc.call(self.actuator_vip, self.actuation_method, self.power_command_topic,
                                         self.power_command_point, value).get(timeout=5)
        except (Exception, Timeout) as e:
            _log.warning(f'Failed to set point on ESS using actuator: {self.actuator_vip},'
                         f' method: {self.actuation_method}, power_command_topic: {power_command_topic},'
                         f' power_command_point: {self.power_command_point}. Got error: {e}')

    def stop(self):
        self.power_command = 0.0

    @classmethod
    def factory(cls, controller, config):
        class_name = config.pop('class_name', 'EnergyStorageSystem')
        if class_name == 'EnergyStorageSystem':
            module = 'rt_control.ess'
        else:
            module = config.pop('module_name', 'rt_control.ess.' + camel_to_snake(class_name))
        _log.info(f'Configuring class: {class_name} from module: {module}')
        module = import_module(module)
        mode_class = getattr(module, class_name)
        mode = mode_class(controller=controller, config=config)
        return mode
