from datetime import datetime, timezone

from rt_control.use_cases import UseCase


class PeakLimiting(UseCase):
    def __init__(self, realtime_power_topic: str, realtime_power_point: str, **kwargs):
        super(PeakLimiting, self).__init__(**kwargs)
        pubsub_kwargs = {'all_platforms': True} if kwargs.get('subscribe_all_platforms') else {}
        self.controller.vip.pubsub.subscribe('pubsub', realtime_power_topic,
                                             self._ingest_state('realtime_power', realtime_power_point, default=0.0),
                                             **pubsub_kwargs)

    @property
    def realtime_power(self):
        return self.states.get('realtime_power', 0.0)

    def to_julia(self):
        super(PeakLimiting, self).to_julia()
        from julia.CtrlEvalEngine import FixedIntervalTimeSeries
        from julia.CtrlEvalEngine import EnergyStorageUseCases
        # TODO: This passes 0 as the peakThreshold. That doesn't appear to be used in Julia
        #  (control algorithms have it as a parameter instead), but why is it there at all?
        return EnergyStorageUseCases.PeakLimiting(
            0.0,
            FixedIntervalTimeSeries(datetime.now(timezone.utc), self.controller.resolution, [self.realtime_power]),
        )
