from rt_control.modes.es_control_mode import ESControlMode

class RuleBased(ESControlMode):
    def __init__(self, bound: float, *args, **kwargs):
        super(RuleBased, self).__init__(*args, **kwargs)
        self.bound:float = bound

    def _get_julia_mode_struct(self):
        return self.CEE.EnergyStorageRTControl.RuleBasedController(self.bound)
