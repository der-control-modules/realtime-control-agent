import logging

from importlib.metadata import distribution, PackageNotFoundError
try:
    distribution('volttron-core')
    from volttron.client.logs import setup_logging
except PackageNotFoundError:
    from volttron.platform.agent.utils import setup_logging

from rt_control.modes import MesaMode, RampParams
from rt_control.use_cases import GenerationFollowing, LoadFollowing, PeakLimiting

setup_logging()
_log = logging.getLogger(__name__)

class ActivePowerResponse(MesaMode):
    def __init__(self, activation_threshold: float, output_ratio: float, ramp_params: dict, **kwargs):
        super(ActivePowerResponse, self).__init__(**kwargs)
        self.activation_threshold: float = activation_threshold # Watts
        self.output_ratio: float = output_ratio # Percentage
        self.ramp_params: RampParams = RampParams(**ramp_params)

    def control(self, schedule_period, start_time, sp_progress):
        peak_limiting = next((c for c in self.use_cases if isinstance(c, PeakLimiting)), None)
        load_following = next((c for c in self.use_cases if isinstance(c, LoadFollowing)), None)
        gen_following = next((c for c in self.use_cases if isinstance(c, GenerationFollowing)), None)
        current_power = self.wip[-1]
        if peak_limiting and not load_following and not gen_following: # Only peak limiting.
            # TODO: This retrieves realtime_power using get_period in ESControl,
            #  but that isn't as relevant to a realtime usage. Should we keep getting a tuple like in ESControl
            #  or just the value, as is done here? get_period returns (value, start, stop) for the period requested.
            reference_power = peak_limiting.realtime_power
            power_past_limit = max(reference_power - self.activation_threshold, 0)
        elif not peak_limiting and load_following and not gen_following: # Only load following.
            reference_power = load_following.realtime_power
            power_past_limit = max((reference_power - self.activation_threshold) * self.output_ratio / 100, 0)
        elif not peak_limiting and not load_following and gen_following: # Only gen following.
            reference_power = gen_following.realtime_power
            power_past_limit = min((reference_power - self.activation_threshold) * self.output_ratio / 100, 0)
        elif gen_following or load_following or peak_limiting:
            _log.error('Disallowed set of UseCases: Only one of "PeakLimiting", "LoadFollowing",'
                       ' and "GenerationFollowing" may be used with the MESA Active Response Mode.')
            reference_power = 0.0
            power_past_limit = 0.0
        else:
            _log.error('MESA Active Response Mode requires exactly one of "PeakLimiting, "LoadFollowing,'
                       ' or "GenerationFollowing" to be provided as a use case.')
            reference_power = 0.0
            power_past_limit = 0.0

        _log.debug(f'In control, the reference power is: {reference_power} and the power_past_limit is: {power_past_limit}')
        ramp_limited_power = self.ramp_params.apply_ramps(self.ess, current_power, power_past_limit)
        ess_limited_power = min(max(ramp_limited_power, self.ess.minimum_power), self.ess.maximum_power)
        energy_limited_power = self.controller.apply_energy_limits(ess_limited_power, self.controller.resolution)
        return energy_limited_power
