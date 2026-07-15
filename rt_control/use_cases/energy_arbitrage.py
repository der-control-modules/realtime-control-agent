from datetime import datetime, timezone

from rt_control.use_cases import UseCase


# TODO: Should this use case be returning vectors of values up to now or single values of the current time?
class EnergyArbitrage(UseCase):
    def __init__(self, actual_price_topic: str, actual_price_point: str, **kwargs):
        super(EnergyArbitrage, self).__init__(**kwargs)
        pubsub_kwargs = {'all_platforms': True} if kwargs.get('subscribe_all_platforms') else {}
        self.controller.vip.pubsub.subscribe('pubsub', actual_price_topic,
                                             self._ingest_state('actual_price', actual_price_point, default=0.0),
                                             **pubsub_kwargs)

    @property
    def forecast_price(self):
        return None  # TODO: Implement this? How? Subscription to forecast publish? Config?

    @property
    def actual_price(self):
        return self.states.get('actual_price', 0.0)

    def to_julia(self, cee):
        return cee.EnergyStorageUseCases.EnergyArbitrage(
            cee.FixedIntervalTimeSeries(datetime.now(timezone.utc), self.controller.resolution, [self.actual_price]),
            cee.FixedIntervalTimeSeries(datetime.now(timezone.utc), self.controller.resolution, [self.forecast_price]),
        )