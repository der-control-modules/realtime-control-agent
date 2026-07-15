from datetime import datetime, timezone

from rt_control.use_cases import UseCase


class Regulation(UseCase):
    def __init__(self, agc_signal_topic: str, agc_signal_point: str, **kwargs):
        super(Regulation, self).__init__(**kwargs)
        pubsub_kwargs = {'all_platforms': True} if kwargs.get('subscribe_all_platforms') else {}
        self.controller.vip.pubsub.subscribe('pubsub', agc_signal_topic,
                                             self._ingest_state('agc_signal', agc_signal_point, default=0.0),
                                             **pubsub_kwargs)

    @property
    def agc_signal(self):
        return self.states.get('agc_signal', 0.0)

    @property
    def price(self):
        # TODO: What is this exactly? Julia code implements regulation price as a vector of (capacity ,service) prices.
        return 0.0, 0.0

    @property
    def performance_score(self):
        return 0.0  # TODO: How to implement Regulation performance_score?

    def to_julia(self, cee):
        return cee.EnergyStorageUseCases.Regulation(
            cee.FixedIntervalTimeSeries(datetime.now(timezone.utc), self.controller.resolution, [self.agc_signal]),
            cee.FixedIntervalTimeSeries(datetime.now(timezone.utc), self.controller.resolution,
                                    [cee.EnergyStorageUseCases.RegulationPricePoint(*self.price)]),
            self.performance_score
        )