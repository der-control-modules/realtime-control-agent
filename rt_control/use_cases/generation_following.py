from rt_control.use_cases import UseCase


class GenerationFollowing(UseCase):
    def __init__(self, realtime_power_topic: str, **kwargs):
        super(GenerationFollowing, self).__init__(**kwargs)
        realtime_power_topic, realtime_power_point = realtime_power_topic.rsplit('/', 1)

        self.controller.vip.pubsub.subscribe('pubsub', realtime_power_topic,
                                        self._ingest_state('realtime_power', realtime_power_point))

    @property
    def realtime_power(self):
        return self.states.get('realtime_power', 0.0)