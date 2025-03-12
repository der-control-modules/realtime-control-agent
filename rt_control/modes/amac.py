from rt_control.modes.es_control_mode import ESControlMode


# TODO: AMAController should probably be implemented directly from the python code
#  instead of wrapping the python-wrapped julia code again.
class ChargeDischargeStorage(ESControlMode):
    def _get_julia_mode_struct(self):
        return self.CEE.AMAController()
