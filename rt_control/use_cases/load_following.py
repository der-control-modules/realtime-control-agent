from datetime import datetime, timezone

from rt_control.use_cases import UseCase


class LoadFollowing(UseCase):
    def __init__(self, realtime_power_topic: str, realtime_power_point: str, **kwargs):
        super(LoadFollowing, self).__init__(**kwargs)
        pubsub_kwargs = {'all_platforms': True} if kwargs.get('subscribe_all_platforms') else {}
        self.controller.vip.pubsub.subscribe('pubsub', realtime_power_topic,
                                             self._ingest_state('realtime_power', realtime_power_point, default=0.0),
                                             **pubsub_kwargs)

    @property
    def forecast_power(self):
        return 0.0  # TODO: Implement this?

    @property
    def realtime_power(self):
        return self.states.get('realtime_power', 0.0)

    def to_julia(self, cee):
        return cee.EnergyStorageUseCases.LoadFollowing(
            cee.FixedIntervalTimeSeries(datetime.now(timezone.utc), self.controller.resolution, [self.forecast_power]),
            cee.FixedIntervalTimeSeries(datetime.now(timezone.utc), self.controller.resolution, [self.realtime_power]),
        )