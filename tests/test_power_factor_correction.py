"""Unit tests for the MESA Power Factor Correction mode."""
import math
import sys

import pytest

from conftest import FakeESS, FakeController, make_peak_limiting, make_load_following
from rt_control.modes.reactive.power_factor_correction import PowerFactorCorrection
from rt_control.modes import ReactiveMesaMode
from rt_control.util import VariableIntervalTimeSeries, SchedulePeriod
from datetime import datetime, timezone


def build(use_cases, reactive_capacity=1000.0, **params):
    ess = FakeESS(maximum_power=100.0, reactive_capacity=reactive_capacity)
    controller = FakeController(ess)
    mode = PowerFactorCorrection(controller=controller, ess=ess, use_cases=use_cases, priority=0, **params)
    mode.wip = [0.0]
    return mode


def q(mode):
    now = datetime.now(timezone.utc)
    return mode.control_reactive(SchedulePeriod(p=0.0, t_start=now), now, VariableIntervalTimeSeries())


def expected_q(active_power, pf):
    return math.copysign(abs(active_power) * math.tan(math.acos(min(abs(pf), 1.0))), pf)


def test_is_reactive_mode():
    mode = build([make_peak_limiting(50.0)], average_pf_target=0.95)
    assert isinstance(mode, ReactiveMesaMode)


def test_corrects_toward_target_pf_from_peak_limiting():
    mode = build([make_peak_limiting(80.0)], average_pf_target=0.9)
    assert q(mode) == pytest.approx(expected_q(80.0, 0.9))


def test_uses_load_following_when_no_peak_limiting():
    mode = build([make_load_following(60.0)], average_pf_target=0.95)
    assert q(mode) == pytest.approx(expected_q(60.0, 0.95))


def test_unity_power_factor_gives_zero_reactive():
    mode = build([make_peak_limiting(70.0)], average_pf_target=1.0)
    assert q(mode) == pytest.approx(0.0)


def test_negative_pf_target_gives_inductive_sign():
    mode = build([make_peak_limiting(50.0)], average_pf_target=-0.9)
    result = q(mode)
    assert result < 0
    assert result == pytest.approx(expected_q(50.0, -0.9))


def test_pf_target_clamped_into_limit_band():
    # Target 0.8 but lower limit 0.95 -> corrected using 0.95.
    mode = build([make_peak_limiting(50.0)], average_pf_target=0.8,
                 lower_pf_limit=0.95, upper_pf_limit=1.0)
    assert q(mode) == pytest.approx(expected_q(50.0, 0.95))


def test_reactive_clamped_to_ess_capacity():
    # Small reactive capacity forces clamping of a large computed Q.
    mode = build([make_peak_limiting(100.0)], reactive_capacity=5.0, average_pf_target=0.5)
    result = q(mode)
    assert result == pytest.approx(5.0)  # clamped to maximum_reactive_power


def test_missing_use_case_returns_zero():
    mode = build([], average_pf_target=0.9)
    assert q(mode) == 0.0


def test_no_julia_loaded():
    assert 'julia' not in sys.modules
