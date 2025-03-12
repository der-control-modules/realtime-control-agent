from datetime import datetime, timezone

from rt_control.use_cases import UseCase


class FrequencyResponse(UseCase):
    def __init__(self, metered_frequency_topic: str, metered_frequency_point: str,
                 nominal_frequency: float = 60.0, **kwargs):
        super(FrequencyResponse, self).__init__(**kwargs)
        self.nominal_frequency: float = nominal_frequency
        pubsub_kwargs = {'all_platforms': True} if kwargs.get('subscribe_all_platforms') else {}
        self.controller.vip.pubsub.subscribe('pubsub', metered_frequency_topic,
                                             self._ingest_state('metered_frequency', metered_frequency_point, default=0.0),
                                             **pubsub_kwargs)

    @property
    def metered_frequency(self):
        return self.states.get('metered_frequency', 0.0)

    def to_julia(self, cee):
        return cee.EnergyStorageUseCases.FrequencyResponse(
            cee.FixedIntervalTimeSeries(datetime.now(timezone.utc), self.controller.resolution, [self.metered_frequency]),
            self.nominal_frequency
        )