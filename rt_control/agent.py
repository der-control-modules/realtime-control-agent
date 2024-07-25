import logging
import sys

from datetime import datetime, timedelta
from importlib.metadata import version

if int(version('volttron').split('.')[0]) >= 10:
    from volttron.client.vip.agent import Agent
    from volttron.utils import get_aware_utc_now, load_config, parse_timestamp_string, setup_logging, vip_main
    from volttron.utils.scheduling import periodic
else:
    from volttron.platform.agent.utils import (get_aware_utc_now, load_config, parse_timestamp_string, setup_logging,\
        vip_main)
    from volttron.platform.scheduling import periodic
    from volttron.platform.vip.agent import Agent

from rt_control.ess import EnergyStorageSystem
from rt_control.modes import ControlMode
from rt_control.use_cases import UseCase
from rt_control.util import FixedIntervalTimeSeries, SchedulePeriod, VariableIntervalTimeSeries

setup_logging()
_log = logging.getLogger(__name__)

__version__ = 0.1

class RTControlAgent(Agent):
    def __init__(self, config_path, *args, **kwargs):
        super(RTControlAgent, self).__init__(*args, **kwargs)
        config = load_config(config_path)
        self.vip.config.set_default('config', config)

        self.ess: EnergyStorageSystem = EnergyStorageSystem.factory(self, {})
        self.modes: list[ControlMode] = []
        self.resolution: timedelta = timedelta(seconds=1.0)
        self.schedule: list[SchedulePeriod] = [SchedulePeriod(**c) for c in config.get('schedule', [])]
        self.use_cases = []
        self.wip: FixedIntervalTimeSeries = FixedIntervalTimeSeries(get_aware_utc_now(), 0.0)

        self.vip.config.subscribe(self.configure_main, ['NEW', 'UPDATE'], 'config')

    def configure_main(self, _, __, contents):
        self.ess: EnergyStorageSystem = EnergyStorageSystem.factory(self, contents.get('ess', {}))
        self.modes.sort(key=lambda m: m.priority)
        self.resolution = self.wip.resolution = timedelta(seconds=contents.get('resolution', self.resolution.seconds))
        self.use_cases: list[UseCase] = [UseCase.factory(self, u) for u in contents.get('use_cases', self.use_cases)]
        time_string = contents.get('start_time')
        self.wip.start_time = parse_timestamp_string(time_string) if time_string else get_aware_utc_now()

        for m in contents.get('modes', self.modes):
            mode = ControlMode.factory(self, self.ess, self.use_cases, m)
            _log.debug(f'Modes is: {mode}')
            self.modes.append(mode)
        self.core.schedule(periodic(self.resolution.seconds), self.loop)

    def add_mode(self, mode):
        self.modes = sorted(self.modes + [mode], key=lambda m: m.priority)

    def remove_mode(self, mode):
        self.modes = [m for m in self.modes if m.__class__ != mode]

    def apply_energy_limits(self, power: float, duration: timedelta, min_reserve: float = None,
                            max_reserve: float = None):
        if self.ess.energy_state is None:
            return 0.0
        # TODO: Why are we setting energy variables to power?
        min_energy = min_reserve / 100 * self.ess.maximum_power if min_reserve is not None else self.ess.minimum_power
        max_energy = max_reserve / 100 * self.ess.maximum_power if max_reserve is not None else self.ess.maximum_power
        proposed_new_energy = self.ess.energy_state + (power * duration.seconds)
        if proposed_new_energy > max_energy:
            return (max_energy - self.ess.energy_state) / duration.seconds
        elif proposed_new_energy < min_energy:
            return (min_energy - self.ess.energy_state) / duration.seconds
        else:
            return power

    def control(self, schedule_period: SchedulePeriod, start_time: datetime, sp_progress: VariableIntervalTimeSeries):
        # Initialize global power value for new iteration:
        current_iteration_power = 0.0
        # Call each mode in order of priority:
        for mode in self.modes:
            # Initialize mode power value for new iteration.
            mode.wip.append(0.0)

            mode_power = mode.control(schedule_period, start_time, sp_progress)
            mode.wip[-1] = mode_power
            current_iteration_power += mode_power
        # Apply limits to the output before controlling:
        ess_limited_power = min(max(current_iteration_power, self.ess.minimum_power), self.ess.maximum_power)
        energy_limited_power = self.apply_energy_limits(ess_limited_power, self.resolution)
        self.wip.append(energy_limited_power)
        return FixedIntervalTimeSeries(start_time, self.resolution, [energy_limited_power])

    def loop(self):
        now = get_aware_utc_now()
        current_schedule_period = next(filter(lambda s: s.t_start < now < s.end_time, self.schedule), 0.0)
        command = self.control(current_schedule_period, now, VariableIntervalTimeSeries())  # TODO: Implement something for SP_Progress?
        if self.ess.power != command[0]: # Reading from power gets last received value from ESS.
            self.ess.power = command[0]  # Writing to power actuates.
        else:
            _log.debug(f'Skipping actuation, command: {command[0]} already matches ess.power: {self.ess.power}.')


def main():
    """Main method called by the app."""
    try:
        vip_main(RTControlAgent)
    except Exception as exception:
        _log.exception("unhandled exception")
        _log.error(repr(exception))


if __name__ == "__main__":
    """Entry point for script"""
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass
