"""Unit tests for the MESA active-power modes (native control paths)."""
import sys
from datetime import datetime, timezone

import pytest

from conftest import (FakeESS, FakeController, make_voltage_control, make_frequency_response,
                      make_regulation, make_generation_following, make_peak_limiting)
from rt_control.util import SchedulePeriod, VariableIntervalTimeSeries
from rt_control.modes import MesaMode

from rt_control.modes.active.active_power_limit import ActivePowerLimit
from rt_control.modes.active.active_power_response import ActivePowerResponse
from rt_control.modes.active.active_power_smoothing import ActivePowerSmoothing
from rt_control.modes.active.agc import AGC
from rt_control.modes.active.charge_discharge_storage import ChargeDischargeStorage
from rt_control.modes.active.frequency_watt import FrequencyWatt
from rt_control.modes.active.volt_watt import VoltWatt


def now():
    return datetime.now(timezone.utc)


def build(mode_cls, *, use_cases=None, energy_state=50.0, reactive_capacity=0.0, wip=None, **params):
    ess = FakeESS(maximum_power=100.0, reactive_capacity=reactive_capacity, energy_state=energy_state)
    controller = FakeController(ess)
    mode = mode_cls(controller=controller, ess=ess, use_cases=use_cases or [], priority=0, **params)
    mode.wip = wip if wip is not None else [0.0]
    return mode


def run(mode, p=0.0, reg_cap_kw=0.0):
    t = now()
    return mode.control(SchedulePeriod(p=p, t_start=t, reg_cap_kw=reg_cap_kw), t, VariableIntervalTimeSeries())


# --------------------------- ActivePowerLimit ---------------------------
def test_active_power_limit_is_mesa_mode():
    assert isinstance(build(ActivePowerLimit, maximum_charge_percentage=50.0,
                            maximum_discharge_percentage=80.0), MesaMode)


def test_active_power_limit_clamps_over_cap():
    mode = build(ActivePowerLimit, maximum_charge_percentage=100.0, maximum_discharge_percentage=80.0,
                 wip=[90.0])  # 90 kW over the 80 kW discharge cap
    assert run(mode) == pytest.approx(80.0 - 90.0)  # correcting delta


def test_active_power_limit_within_cap_no_change():
    mode = build(ActivePowerLimit, maximum_charge_percentage=100.0, maximum_discharge_percentage=80.0,
                 wip=[50.0])
    assert run(mode) == pytest.approx(0.0)


# --------------------------- ActivePowerResponse ---------------------------
def test_active_power_response_peak_limiting():
    pl = make_peak_limiting(70.0)
    mode = build(ActivePowerResponse, use_cases=[pl], activation_threshold=10.0,
                 output_ratio=100.0, ramp_params={})
    # power_past_limit = 70 - 10 = 60; ramp full; energy limit 50+60>100 -> (100-50)/1 = 50
    assert run(mode) == pytest.approx(50.0)


def test_active_power_response_no_use_case_returns_zero():
    mode = build(ActivePowerResponse, activation_threshold=10.0, output_ratio=100.0, ramp_params={})
    assert run(mode) == pytest.approx(0.0)


# --------------------------- AGC ---------------------------
def test_agc_follows_schedule_without_regulation():
    mode = build(AGC, minimum_usable_soc=10.0, maximum_usable_soc=90.0)
    assert run(mode, p=25.0) == pytest.approx(25.0)


def test_agc_scales_signal_by_reg_capacity():
    reg = make_regulation(0.5)
    mode = build(AGC, use_cases=[reg], minimum_usable_soc=10.0, maximum_usable_soc=90.0)
    # target = 40 * 0.5 = 20 kW; ramp full; energy 50+20 < 90 -> passes
    assert run(mode, reg_cap_kw=40.0) == pytest.approx(20.0)


# --------------------------- ActivePowerSmoothing ---------------------------
def test_active_power_smoothing_opposes_rate_of_change():
    gen = make_generation_following(10.0)
    mode = build(ActivePowerSmoothing, use_cases=[gen], smoothing_gradient=2.0,
                 lower_smoothing_limit=-50.0, upper_smoothing_limit=50.0, smoothing_filter_time=1.0)
    mode._previous_reference_power = 0.0  # dP/dt = 10 -> target -20 (charge); min_power=0 clamps to 0
    assert run(mode) == pytest.approx(0.0)


def test_active_power_smoothing_discharge_on_falling_reference():
    gen = make_generation_following(0.0)
    mode = build(ActivePowerSmoothing, use_cases=[gen], smoothing_gradient=2.0,
                 lower_smoothing_limit=-50.0, upper_smoothing_limit=50.0, smoothing_filter_time=1.0)
    mode._previous_reference_power = 10.0  # dP/dt = -10 -> target +20 kW discharge
    assert run(mode) == pytest.approx(20.0)


# --------------------------- VoltWatt ---------------------------
def test_volt_watt_deadband_returns_zero():
    vc = make_voltage_control(240.5, reference_voltage=240.0)
    mode = build(VoltWatt, use_cases=[vc], reference_voltage_offset=0.0,
                 volt_watt_curve=[[245.0, 0.0], [255.0, -100.0]], gradient=1.0, filter_time=0.0,
                 lower_deadband=2.0, upper_deadband=2.0)
    assert run(mode) == pytest.approx(0.0)


def test_volt_watt_no_use_case_returns_zero():
    mode = build(VoltWatt, reference_voltage_offset=0.0,
                 volt_watt_curve=[[245.0, 0.0], [255.0, -100.0]], gradient=1.0, filter_time=0.0,
                 lower_deadband=2.0, upper_deadband=2.0)
    assert run(mode) == pytest.approx(0.0)


# --------------------------- FrequencyWatt ---------------------------
def _fw(freq):
    fr = make_frequency_response(freq)
    return build(FrequencyWatt, use_cases=[fr], use_curves=True,
                 frequency_watt_curve=[[60.0, 0.0], [61.0, 100.0]],
                 low_hysteresis_curve=[[59.0, 0.0]], high_hysteresis_curve=[[61.0, 0.0]],
                 start_delay=0.0, stop_delay=0.0, minimum_soc=10.0, maximum_soc=90.0,
                 use_hysteresis=True, use_snapshot_power=False,
                 high_starting_frequency=60.3, low_starting_frequency=59.7,
                 high_stopping_frequency=60.1, low_stopping_frequency=59.9,
                 high_discharge_gradient=1.0, low_discharge_gradient=1.0,
                 high_charge_gradient=1.0, low_charge_gradient=1.0,
                 high_return_gradient=1.0, low_return_gradient=1.0)


def test_frequency_watt_activates_above_high_start():
    mode = _fw(60.5)  # active; curve 50% -> 50 kW; energy limited by 90% reserve -> 40
    assert run(mode) == pytest.approx(40.0)


def test_frequency_watt_inactive_within_deadband():
    mode = _fw(60.0)  # within stopping band -> inactive -> 0
    assert run(mode) == pytest.approx(0.0)


def test_no_julia_loaded():
    assert 'julia' not in sys.modules
