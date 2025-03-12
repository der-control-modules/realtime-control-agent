from rt_control.modes.es_control_mode import ESControlMode


class ActivePowerLimit(ESControlMode):
    # TODO: Implement Ramp and Mesa Mode Params arguments.
    def __init__(self, maximum_charge_percentage: float, maximum_discharge_percentage: float, *args, **kwargs):
        super(ActivePowerLimit, self).__init__(*args, **kwargs)
        self.maximum_charge_percentage: float = maximum_charge_percentage
        self.maximum_discharge_percentage: float = maximum_discharge_percentage

    def _get_julia_mode_struct(self):
        # The only required parameter is the priority.
        mesa_mode_params = self.CEE.EnergyStorageRTControl.MesaModeParams(self.priority)
        return self.CEE.EnergyStorageRTControl.ActivePowerLimitMode(
            mesa_mode_params, self.maximum_charge_percentage, self.maximum_discharge_percentage)
