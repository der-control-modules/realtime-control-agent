"""Unit tests for the MESA reactive-power modes (ConstantVar, FixedPowerFactor,
VoltVar, WattVar). DynamicReactiveCurrentSupport and PowerFactorCorrection have their
own dedicated test files."""
import math
import sys
from datetime import datetime, timezone

import pytest

from conftest import FakeESS, FakeController, make_voltage_control
from rt_control.util import SchedulePeriod, VariableIntervalTimeSeries
from rt_control.modes import ReactiveMesaMode

from rt_control.modes.reactive.constant_var import ConstantVar
from rt_control.modes.reactive.fixed_power_factor import FixedPowerFactor
from rt_control.modes.reactive.volt_var import VoltVar
from rt_control.modes.reactive.watt_var import WattVar


def now():
    return datetime.now(timezone.utc)


def build(mode_cls, *, ess=None, use_cases=None, reactive_capacity=60.0, power_command=0.0, **params):
    ess = ess or FakeESS(maximum_power=100.0, reactive_capacity=reactive_capacity, power_command=power_command)
    controller = FakeController(ess)
    mode = mode_cls(controller=controller, ess=ess, use_cases=use_cases or [], priority=0, **params)
    mode.wip = [0.0]
    return mode


def q(mode):
    t = now()
    return mode.control_reactive(SchedulePeriod(p=0.0, t_start=t), t, VariableIntervalTimeSeries())


def active(mode):
    t = now()
    return mode.control(SchedulePeriod(p=0.0, t_start=t), t, VariableIntervalTimeSeries())


# --------------------------- ConstantVar ---------------------------
def test_constant_var_is_reactive_and_inert_on_active():
    mode = build(ConstantVar, reactive_power_target=50.0)
    assert isinstance(mode, ReactiveMesaMode)
    assert active(mode) == 0.0


def test_constant_var_percentage_of_capacity():
    mode = build(ConstantVar, reactive_capacity=60.0, reactive_power_target=50.0)
    assert q(mode) == pytest.approx(30.0)


def test_constant_var_negative_target_is_inductive():
    mode = build(ConstantVar, reactive_capacity=60.0, reactive_power_target=-25.0)
    assert q(mode) == pytest.approx(-15.0)


# --------------------------- FixedPowerFactor ---------------------------
def _expected_pf_q(p, pf):
    return math.copysign(abs(p) * math.tan(math.acos(min(abs(pf), 1.0))), pf)


def test_fixed_power_factor_generating():
    ess = FakeESS(maximum_power=100.0, reactive_capacity=1000.0, power_command=80.0)
    mode = build(FixedPowerFactor, ess=ess, power_factor_generating=0.9)
    assert q(mode) == pytest.approx(_expected_pf_q(80.0, 0.9))


def test_fixed_power_factor_charging_uses_charging_setpoint():
    ess = FakeESS(maximum_power=100.0, reactive_capacity=1000.0, power_command=-50.0)
    mode = build(FixedPowerFactor, ess=ess, power_factor_generating=0.95, power_factor_charging=0.8)
    assert q(mode) == pytest.approx(_expected_pf_q(-50.0, 0.8))


def test_fixed_power_factor_unity_gives_zero():
    ess = FakeESS(maximum_power=100.0, reactive_capacity=1000.0, power_command=60.0)
    mode = build(FixedPowerFactor, ess=ess, power_factor_generating=1.0)
    assert q(mode) == pytest.approx(0.0)


# --------------------------- VoltVar ---------------------------
def test_volt_var_midpoint_zero():
    vc = make_voltage_control(245.0)
    mode = build(VoltVar, use_cases=[vc], reactive_capacity=100.0,
                 volt_var_curve=[[240.0, 100.0], [245.0, 0.0], [250.0, -100.0]])
    assert q(mode) == pytest.approx(0.0)


def test_volt_var_low_voltage_injects_capacitive():
    vc = make_voltage_control(240.0)
    mode = build(VoltVar, use_cases=[vc], reactive_capacity=100.0,
                 volt_var_curve=[[240.0, 100.0], [250.0, -100.0]])
    assert q(mode) == pytest.approx(100.0)  # 100% of 100 kVAR


def test_volt_var_no_use_case_returns_zero():
    mode = build(VoltVar, reactive_capacity=100.0, volt_var_curve=[[240.0, 100.0], [250.0, -100.0]])
    assert q(mode) == pytest.approx(0.0)


# --------------------------- WattVar ---------------------------
def test_watt_var_interpolates_on_active_percentage():
    ess = FakeESS(maximum_power=100.0, reactive_capacity=100.0, power_command=50.0)
    mode = build(WattVar, ess=ess, watt_var_curve=[[0.0, 0.0], [100.0, -50.0]])
    assert q(mode) == pytest.approx(-25.0)  # P=50% -> -25% of 100 kVAR


def test_watt_var_zero_power_zero_var():
    ess = FakeESS(maximum_power=100.0, reactive_capacity=100.0, power_command=0.0)
    mode = build(WattVar, ess=ess, watt_var_curve=[[0.0, 0.0], [100.0, -50.0]])
    assert q(mode) == pytest.approx(0.0)


def test_no_julia_loaded():
    assert 'julia' not in sys.modules
