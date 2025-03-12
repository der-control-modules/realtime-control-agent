import re

from datetime import datetime, timedelta
from typing import List, Union

from importlib.metadata import distribution, PackageNotFoundError
try:
    distribution('volttron-core')
    from volttron.utils import parse_timestamp_string
except PackageNotFoundError:
    from volttron.platform.agent.utils import parse_timestamp_string

first_cap_re = re.compile('(.)([A-Z][a-z]+)')
all_cap_re = re.compile('([a-z\d])([A-Z])')


def camel_to_snake(name):
    s1 = first_cap_re.sub(r'\1_\2', name)
    return all_cap_re.sub(r'\1_\2', s1).lower()


class FixedIntervalTimeSeries(list):
    def __init__(self, start_time, resolution, values=None):
        values = values if values else [0.0]
        super(FixedIntervalTimeSeries, self).__init__(values)
        self.start_time: datetime = start_time
        self.resolution: timedelta = resolution

    def dump(self):
        return self.start_time, self.resolution, self


class VariableIntervalTimeSeries:
    def __init__(self, t: List[datetime] = None, value: List[any] = None):
        # TODO: Is it valid to init this with two empty lists?
        self.t = t if t else []
        self.value = value if value else []

    def dump(self):
        return self.t, self.value


class SchedulePeriod:
    def __init__(self, p: float, t_start: Union[datetime, str], duration: Union[timedelta, float] = timedelta(hours=1),
                 soc_start: float = 0.0, soc_end: float = 0.0, reg_cap_kw: float = 0.0):
        self.p: float = p
        self.t_start: datetime = t_start if isinstance(t_start, datetime) else parse_timestamp_string(t_start)
        self.duration: timedelta = timedelta(seconds=duration) if not isinstance(duration, timedelta) else duration
        self.soc_start: float = soc_start
        self.soc_end: float = soc_end
        self.reg_cap_kw: float = reg_cap_kw

    @property
    def end_time(self):
        return self.t_start + self.duration

    def dump(self):
        return self.p, self.t_start, self.duration, self.soc_start, self.soc_end, self.reg_cap_kw
