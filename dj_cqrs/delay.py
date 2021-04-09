#  Copyright © 2021 Ingram Micro Inc. All rights reserved.

from datetime import timedelta
from queue import PriorityQueue

from dj_cqrs.utils import utc_now


class DelayMessage:
    """Delay message.

    :param delivery_tag:
    :type delivery_tag: int
    :param payload:
    :type payload: dj_cqrs.dataclasses.TransportPayload
    """

    def __init__(self, delivery_tag, payload, delay):
        assert delay >= 0
        self.delivery_tag = delivery_tag
        self.payload = payload
        self.eta = utc_now() + timedelta(seconds=delay)


class DelayQueue:
    """Queue for delay messages."""

    def __init__(self):
        self._queue = PriorityQueue()

    def get(self):
        _, delay_message = self._queue.get()
        return delay_message

    def get_ready(self):
        """Returns messages for which the timeout parameter has passed.

        :return: delayed messages generator
        :rtype: typing.Generator[DelayMessage]
        """
        while self.qsize():
            delay_message = self.get()
            if delay_message.eta > utc_now():
                # Queue is ordered by message ETA.
                # Remaining messages should wait longer, we don't check them.
                self.put(delay_message)
                break

            yield delay_message

    def put(self, delay_message):
        """Adds message to queue.

        :param delay_message: DelayMessage instance.
        :type delay_message: DelayMessage
        """
        assert isinstance(delay_message, DelayMessage)
        self._queue.put(
            (delay_message.eta.timestamp(), delay_message),
        )

    def qsize(self):
        return self._queue.qsize()
