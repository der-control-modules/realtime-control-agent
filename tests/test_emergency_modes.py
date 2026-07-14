"""Unit tests for the MESA emergency ride-through modes."""
import sys
from datetime import datetime, timezone

from conftest import FakeESS, FakeController, make_voltage_control, make_frequency_response
from rt_control.modes import EmergencyMesaMode

from rt_control.modes.emergency.voltage_ride_through import VoltageRideThrough
from rt_control.modes.emergency.frequency_ride_through import FrequencyRideThrough


def now():
    return datetime.now(timezone.utc)


def build(mode_cls, *, use_cases=None, **params):
    ess = FakeESS(maximum_power=100.0, reactive_capacity=60.0)
    controller = FakeController(ess)
    mode = mode_cls(controller=controller, ess=ess, use_cases=use_cases or [], priority=0, **params)
    mode.wip = [0.0]
    return mode


# --------------------------- VoltageRideThrough ---------------------------
def _vrt(voltage):
    return build(VoltageRideThrough, use_cases=[make_voltage_control(voltage)],
                 high_must_trip=264.0, low_must_trip=211.0,
                 high_momentary_cessation=252.0, low_momentary_cessation=222.0)


def test_voltage_ride_through_is_emergency_mode_and_inert_on_active():
    mode = _vrt(240.0)
    assert isinstance(mode, EmergencyMesaMode)
    t = now()
    from rt_control.util import SchedulePeriod, VariableIntervalTimeSeries
    assert mode.control(SchedulePeriod(p=0.0, t_start=t), t, VariableIntervalTimeSeries()) == 0.0


def test_voltage_high_must_trip():
    mode = _vrt(265.0)
    assert mode.gate(50.0, 10.0, now()) == (0.0, 0.0)
    assert mode.tripped is True


def test_voltage_low_must_trip():
    mode = _vrt(200.0)
    assert mode.gate(50.0, 10.0, now()) == (0.0, 0.0)
    assert mode.tripped is True


def test_voltage_momentary_cessation_holds_zero_without_trip():
    mode = _vrt(255.0)  # past cessation (252) but below must-trip (264)
    assert mode.gate(50.0, 10.0, now()) == (0.0, 0.0)
    assert mode.tripped is False


def test_voltage_in_band_passes_through():
    mode = _vrt(240.0)
    assert mode.gate(50.0, 10.0, now()) == (50.0, 10.0)


def test_voltage_missing_use_case_passes_through():
    mode = build(VoltageRideThrough, high_must_trip=264.0, low_must_trip=211.0)
    assert mode.gate(50.0, 10.0, now()) == (50.0, 10.0)


# --------------------------- FrequencyRideThrough ---------------------------
def _frt(freq):
    return build(FrequencyRideThrough, use_cases=[make_frequency_response(freq)],
                 high_must_trip=61.5, low_must_trip=58.5,
                 high_momentary_cessation=60.5, low_momentary_cessation=59.5)


def test_frequency_high_must_trip():
    mode = _frt(62.0)
    assert mode.gate(50.0, 10.0, now()) == (0.0, 0.0)
    assert mode.tripped is True


def test_frequency_low_must_trip():
    mode = _frt(58.0)
    assert mode.gate(50.0, 10.0, now()) == (0.0, 0.0)
    assert mode.tripped is True


def test_frequency_momentary_cessation():
    mode = _frt(61.0)  # past cessation (60.5) but below trip (61.5)
    assert mode.gate(50.0, 10.0, now()) == (0.0, 0.0)
    assert mode.tripped is False


def test_frequency_in_band_passes_through():
    mode = _frt(60.0)
    assert mode.gate(50.0, 10.0, now()) == (50.0, 10.0)


def test_no_julia_loaded():
    assert 'julia' not in sys.modules
