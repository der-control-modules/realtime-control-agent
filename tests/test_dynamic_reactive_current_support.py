"""Unit tests for the MESA Dynamic Reactive Current Support mode."""
import sys

import pytest

from conftest import FakeESS, FakeController, make_voltage_control
from rt_control.modes.reactive.dynamic_reactive_current_support import DynamicReactiveCurrentSupport
from rt_control.modes import ReactiveMesaMode


def build(voltage, reference_voltage=240.0, reactive_capacity=60.0, **params):
    ess = FakeESS(maximum_power=100.0, reactive_capacity=reactive_capacity)
    controller = FakeController(ess)
    vc = make_voltage_control(voltage, reference_voltage)
    mode = DynamicReactiveCurrentSupport(controller=controller, ess=ess, use_cases=[vc], priority=0, **params)
    mode.wip = [0.0]
    return mode


def q(mode):
    from rt_control.util import VariableIntervalTimeSeries, SchedulePeriod
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    return mode.control_reactive(SchedulePeriod(p=0.0, t_start=now), now, VariableIntervalTimeSeries())


def test_is_reactive_mode_and_inert_on_active_axis():
    mode = build(240.0, gradient_sag=1.0)
    assert isinstance(mode, ReactiveMesaMode)
    from rt_control.util import VariableIntervalTimeSeries, SchedulePeriod
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    assert mode.control(SchedulePeriod(p=0.0, t_start=now), now, VariableIntervalTimeSeries()) == 0.0


def test_within_deadband_no_support():
    # deadbands +/-2%, voltage at nominal -> zero.
    mode = build(240.0, deadband_min_voltage=-2.0, deadband_max_voltage=2.0,
                 gradient_sag=1.0, gradient_swell=1.0)
    assert q(mode) == 0.0


def test_sag_injects_capacitive_positive_vars():
    # 228 V vs 240 nominal = -5% deviation; deadband_min -2% -> excess 3%; gradient 2 -> 6% of 60 = 3.6 kVAR
    mode = build(228.0, deadband_min_voltage=-2.0, deadband_max_voltage=2.0,
                 gradient_sag=2.0, gradient_swell=2.0, reactive_capacity=60.0)
    result = q(mode)
    assert result == pytest.approx(3.6)
    assert result > 0  # capacitive


def test_swell_absorbs_inductive_negative_vars():
    # 252 V vs 240 = +5% deviation; deadband_max 2% -> excess 3%; gradient 2 -> -6% of 60 = -3.6 kVAR
    mode = build(252.0, deadband_min_voltage=-2.0, deadband_max_voltage=2.0,
                 gradient_sag=2.0, gradient_swell=2.0, reactive_capacity=60.0)
    result = q(mode)
    assert result == pytest.approx(-3.6)
    assert result < 0  # inductive


def test_block_zone_suppresses_support():
    # Deep sag to 50% but block zone at 60% -> no support despite the sag.
    mode = build(120.0, deadband_min_voltage=-2.0, gradient_sag=5.0, block_zone_voltage=60.0)
    assert q(mode) == 0.0


def test_missing_voltage_control_returns_zero():
    ess = FakeESS(maximum_power=100.0, reactive_capacity=60.0)
    controller = FakeController(ess)
    mode = DynamicReactiveCurrentSupport(controller=controller, ess=ess, use_cases=[], priority=0,
                                         gradient_sag=1.0)
    mode.wip = [0.0]
    assert q(mode) == 0.0


def test_zero_reference_voltage_returns_zero():
    mode = build(228.0, reference_voltage=0.0, gradient_sag=2.0)
    assert q(mode) == 0.0


def test_no_julia_loaded():
    assert 'julia' not in sys.modules
