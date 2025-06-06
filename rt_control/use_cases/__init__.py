import abc
import logging

from typing import Callable
from importlib import import_module

from importlib.metadata import distribution, PackageNotFoundError
try:
    distribution('volttron-core')
    from volttron.client.logs import setup_logging
except PackageNotFoundError:
    from volttron.platform.agent.utils import setup_logging

from rt_control.util import camel_to_snake

setup_logging()
_log = logging.getLogger(__name__)


class UseCase:
    def __init__(self, controller, **kwargs):
        self.controller = controller
        self.states = {}

    def _ingest_state(self, key: str, point_name: str, default: any = 0.0) -> Callable:
        self.states[key] = default
        def func(_, __, ___, topic, _____, message):
            _log.debug(f'Getting point: {point_name} from topic: {topic} with message: {message}')
            if isinstance(message, list):
                message = message[0]
            value = message.get(point_name)
            if value is not None and value != self.states[key]:
                self.states[key] = value
        return func

    @classmethod
    def factory(cls, controller, config):
        class_name = config.pop('class_name')
        module = config.pop('module_name', 'rt_control.use_cases.' + camel_to_snake(class_name))
        _log.info(f'Configuring class: {class_name} from module: {module}')
        module = import_module(module)
        mode_class = getattr(module, class_name)
        mode = mode_class(controller=controller, **config)
        return mode

    @abc.abstractmethod
    def to_julia(self, cee):
        # cee should contain the CtrlEvalEngine module.
        pass

from rt_control.use_cases.generation_following import GenerationFollowing
from rt_control.use_cases.load_following import LoadFollowing
from rt_control.use_cases.peak_limiting import PeakLimiting