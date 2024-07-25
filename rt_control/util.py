import re

from datetime import datetime, timedelta

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


class VariableIntervalTimeSeries:
    pass


class SchedulePeriod:
    def __init__(self, p, t_start, duration=timedelta(hours=1), soc_start=0.0, soc_end=0.0):
        self.p: float = p
        self.t_start: datetime = t_start
        self.duration: timedelta = duration
        self.soc_start: float = soc_start
        self.soc_end: float = soc_end

    @property
    def end_time(self):
        return self.t_start + self.duration
