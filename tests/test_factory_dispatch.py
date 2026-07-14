"""Verify ControlMode.factory resolves every mode from its category subpackage, and
that the category subpackages export the expected classes."""
import pytest

from conftest import FakeESS, FakeController, make_voltage_control, make_frequency_response

from rt_control.modes import ControlMode, MesaMode, ReactiveMesaMode, EmergencyMesaMode


# class_name -> minimal kwargs required to construct it via the factory.
MODE_CASES = {
    # active
    'ActivePowerLimit': dict(maximum_charge_percentage=100.0, maximum_discharge_percentage=80.0),
    'ActivePowerResponse': dict(activation_threshold=10.0, output_ratio=100.0, ramp_params={}),
    'ActivePowerSmoothing': dict(smoothing_gradient=1.0, lower_smoothing_limit=-50.0,
                                 upper_smoothing_limit=50.0, smoothing_filter_time=1.0),
    'AGC': dict(minimum_usable_soc=10.0, maximum_usable_soc=90.0),
    'ChargeDischargeStorage': dict(),
    'FrequencyWatt': dict(use_curves=True, frequency_watt_curve=[[60.0, 0.0], [61.0, 100.0]],
                          low_hysteresis_curve=[[59.0, 0.0]], high_hysteresis_curve=[[61.0, 0.0]],
                          start_delay=0.0, stop_delay=0.0, minimum_soc=10.0, maximum_soc=90.0,
                          use_hysteresis=True, use_snapshot_power=False,
                          high_starting_frequency=60.3, low_starting_frequency=59.7,
                          high_stopping_frequency=60.1, low_stopping_frequency=59.9,
                          high_discharge_gradient=1.0, low_discharge_gradient=1.0,
                          high_charge_gradient=1.0, low_charge_gradient=1.0,
                          high_return_gradient=1.0, low_return_gradient=1.0),
    'VoltWatt': dict(reference_voltage_offset=0.0, volt_watt_curve=[[245.0, 0.0], [255.0, -100.0]],
                     gradient=1.0, filter_time=0.0, lower_deadband=2.0, upper_deadband=2.0),
    # reactive
    'ConstantVar': dict(reactive_power_target=50.0),
    'DynamicReactiveCurrentSupport': dict(gradient_sag=1.0, gradient_swell=1.0),
    'FixedPowerFactor': dict(power_factor_generating=0.95),
    'PowerFactorCorrection': dict(average_pf_target=0.98),
    'VoltVar': dict(volt_var_curve=[[240.0, 100.0], [250.0, -100.0]]),
    'WattVar': dict(watt_var_curve=[[0.0, 0.0], [100.0, -50.0]]),
    # emergency
    'VoltageRideThrough': dict(high_must_trip=264.0, low_must_trip=211.0),
    'FrequencyRideThrough': dict(high_must_trip=61.5, low_must_trip=58.5),
    # NOTE: The novel modes (PID, RuleBased, and the amac ChargeDischargeStorage) import
    # julia at module load, so they cannot be resolved without a Julia runtime and are
    # not exercised here. See test_novel_modes_require_julia below.
}

# Novel modes live in rt_control.modes.novel and depend on a Julia runtime at import.
NOVEL_MODULES = {
    'PID': 'rt_control.modes.novel.pid',
    'RuleBased': 'rt_control.modes.novel.rule_based',
    'ESControlMode': 'rt_control.modes.novel.es_control_mode',
}


@pytest.mark.parametrize('class_name', sorted(MODE_CASES))
def test_factory_resolves_mode(class_name):
    ess = FakeESS(maximum_power=100.0, reactive_capacity=60.0)
    controller = FakeController(ess)
    config = {'class_name': class_name, **MODE_CASES[class_name]}
    mode = ControlMode.factory(controller, ess, [], config)
    assert type(mode).__name__ == class_name


def test_factory_unknown_class_raises():
    ess = FakeESS()
    controller = FakeController(ess)
    with pytest.raises(ModuleNotFoundError):
        ControlMode.factory(controller, ess, [], {'class_name': 'NoSuchMode'})


@pytest.mark.parametrize('class_name,module_name', sorted(NOVEL_MODULES.items()))
def test_novel_modes_live_in_novel_subpackage(class_name, module_name):
    """Novel modes import julia at module load. When a Julia runtime is present the
    module imports and exposes the class; otherwise importing it raises (never silently
    resolves elsewhere). Either way, the module path is under rt_control.modes.novel."""
    import importlib
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:  # noqa: BLE001 - julia runtime missing is expected here
        assert 'julia' in repr(exc).lower() or 'julia' in str(exc).lower()
        pytest.skip(f'{class_name} requires a Julia runtime (not installed): {exc!r}')
    else:
        assert hasattr(module, class_name)


def test_category_subpackages_export_classes():
    import rt_control.modes.active as active
    import rt_control.modes.reactive as reactive
    import rt_control.modes.emergency as emergency
    for name in ['ActivePowerLimit', 'AGC', 'ChargeDischargeStorage', 'FrequencyWatt', 'VoltWatt',
                 'ActivePowerResponse', 'ActivePowerSmoothing']:
        assert issubclass(getattr(active, name), MesaMode)
    for name in ['ConstantVar', 'DynamicReactiveCurrentSupport', 'FixedPowerFactor',
                 'PowerFactorCorrection', 'VoltVar', 'WattVar']:
        assert issubclass(getattr(reactive, name), ReactiveMesaMode)
    for name in ['VoltageRideThrough', 'FrequencyRideThrough']:
        assert issubclass(getattr(emergency, name), EmergencyMesaMode)
