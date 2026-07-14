"""Shared pytest fixtures and import stubs for rt_control mode tests.

The rt_control package imports `volttron` (and `gevent`) at module load, and several
modes have a lazy `julia` fallback. Neither is installed in the plain test environment,
so this conftest installs lightweight sys.modules stubs BEFORE rt_control is imported.
`julia` is deliberately left unstubbed so tests prove the native (non-Julia) paths run.
"""
import sys
import types
from datetime import datetime, timedelta, timezone

import pytest

# --- Stub volttron (v10 + legacy paths) and gevent so rt_control imports cleanly ---
if 'volttron' not in sys.modules:
    volttron = types.ModuleType('volttron')
    volttron.__version__ = '10.0.0'
    utils = types.ModuleType('volttron.utils')
    utils.setup_logging = lambda *a, **k: None
    utils.get_aware_utc_now = lambda: datetime.now(timezone.utc)
    utils.parse_timestamp_string = lambda s: datetime.fromisoformat(s)
    utils.load_config = lambda *a, **k: {}
    utils.vip_main = lambda *a, **k: None
    scheduling = types.ModuleType('volttron.utils.scheduling')
    scheduling.periodic = lambda *a, **k: None
    client = types.ModuleType('volttron.client')
    client_vip = types.ModuleType('volttron.client.vip')
    client_agent = types.ModuleType('volttron.client.vip.agent')
    client_agent.Agent = object
    client_agent.Core = type('Core', (), {'receiver': staticmethod(lambda *a, **k: (lambda f: f))})
    client_agent.RPC = type('RPC', (), {'export': staticmethod(lambda *a, **k: (lambda f: f))})
    for _name, _mod in [('volttron', volttron), ('volttron.utils', utils),
                        ('volttron.utils.scheduling', scheduling), ('volttron.client', client),
                        ('volttron.client.vip', client_vip), ('volttron.client.vip.agent', client_agent)]:
        sys.modules[_name] = _mod

if 'gevent' not in sys.modules:
    gevent = types.ModuleType('gevent')
    gevent.Timeout = type('Timeout', (Exception,), {})
    sys.modules['gevent'] = gevent

# importlib.metadata.version('volttron') is called at module load throughout rt_control.
import importlib.metadata as _md  # noqa: E402
_orig_version = _md.version
_md.version = lambda name: '10.0.0' if name == 'volttron' else _orig_version(name)


class FakeESS:
    """Minimal EnergyStorageSystem stand-in exposing the properties modes read."""
    def __init__(self, maximum_power=100.0, reactive_capacity=0.0, energy_state=50.0,
                 power_command=0.0):
        self._max_p = maximum_power
        self._reactive_capacity = reactive_capacity
        self.energy_state = energy_state
        self._power_command = power_command

    @property
    def maximum_power(self):
        return self._max_p

    @property
    def minimum_power(self):
        return 0.0

    @property
    def maximum_reactive_power(self):
        return self._reactive_capacity if self._reactive_capacity else self._max_p

    @property
    def minimum_reactive_power(self):
        return -self.maximum_reactive_power

    @property
    def power_command(self):
        return self._power_command


class FakeController:
    """Mirrors RTControlAgent.apply_energy_limits (agent.py) for isolated mode tests."""
    def __init__(self, ess, resolution_seconds=1):
        self.ess = ess
        self.resolution = timedelta(seconds=resolution_seconds)

    def apply_energy_limits(self, power, duration, min_reserve=None, max_reserve=None):
        if self.ess.energy_state is None:
            return 0.0
        min_energy = min_reserve / 100 * self.ess.maximum_power if min_reserve is not None else self.ess.minimum_power
        max_energy = max_reserve / 100 * self.ess.maximum_power if max_reserve is not None else self.ess.maximum_power
        proposed = self.ess.energy_state + (power * duration.seconds)
        if proposed > max_energy:
            return (max_energy - self.ess.energy_state) / duration.seconds
        if proposed < min_energy:
            return (min_energy - self.ess.energy_state) / duration.seconds
        return power


class FakeVoltageControl:
    """Duck-typed VoltageControl: isinstance() checks use the real class, so subclass it."""
    pass


@pytest.fixture
def ess():
    return FakeESS(maximum_power=100.0, reactive_capacity=60.0)


@pytest.fixture
def controller(ess):
    return FakeController(ess)


@pytest.fixture
def now():
    return datetime.now(timezone.utc)


def make_voltage_control(metered_voltage, reference_voltage=240.0):
    """Build a real VoltageControl instance without running its pub/sub __init__."""
    from rt_control.use_cases.voltage_control import VoltageControl
    vc = VoltageControl.__new__(VoltageControl)
    vc.states = {'metered_voltage': metered_voltage}
    vc.reference_voltage = reference_voltage
    return vc


def make_peak_limiting(realtime_power):
    from rt_control.use_cases.peak_limiting import PeakLimiting
    pl = PeakLimiting.__new__(PeakLimiting)
    pl.states = {'realtime_power': realtime_power}
    return pl


def make_load_following(realtime_power):
    from rt_control.use_cases.load_following import LoadFollowing
    lf = LoadFollowing.__new__(LoadFollowing)
    lf.states = {'realtime_power': realtime_power}
    return lf


def make_generation_following(realtime_power):
    from rt_control.use_cases.generation_following import GenerationFollowing
    gf = GenerationFollowing.__new__(GenerationFollowing)
    gf.states = {'realtime_power': realtime_power}
    return gf


def make_frequency_response(metered_frequency, nominal_frequency=60.0):
    from rt_control.use_cases.frequency_response import FrequencyResponse
    fr = FrequencyResponse.__new__(FrequencyResponse)
    fr.states = {'metered_frequency': metered_frequency}
    fr.nominal_frequency = nominal_frequency
    return fr


def make_regulation(agc_signal):
    from rt_control.use_cases.regulation import Regulation
    reg = Regulation.__new__(Regulation)
    reg.states = {'agc_signal': agc_signal}
    return reg
