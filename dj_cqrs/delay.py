#  Copyright © 2021 Ingram Micro Inc. All rights reserved.

from queue import Full, PriorityQueue

from django.utils import timezone


class DelayMessage:
    """Delay message.

    :param delivery_tag: The server-assigned and channel-specific delivery tag.
    :type delivery_tag: int
    :param payload: Transport payload.
    :type payload: dj_cqrs.dataclasses.TransportPayload
    :param eta: Time after which the message should be requeued.
    :type eta: datetime.datetime
    """

    def __init__(self, delivery_tag, payload, eta):
        self.delivery_tag = delivery_tag
        self.payload = payload
        self.eta = eta


class DelayQueue:
    """Queue for delay messages."""

    def __init__(self, max_size=None):
        if max_size is not None:
            assert max_size > 0, "Delay queue max_size should be positive integer."

        self._max_size = max_size
        self._queue = PriorityQueue()

    def get(self):
        """
        :rtype: DelayMessage
        """
        *_, delay_message = self._queue.get()
        return delay_message

    def get_ready(self):
        """Returns messages with expired ETA.

        :return: delayed messages generator
        :rtype: typing.Generator[DelayMessage]
        """
        while self.qsize():
            delay_message = self.get()
            if delay_message.eta > timezone.now():
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
        if self.full():
            raise Full("Delay queue is full")

        self._queue.put((
            delay_message.eta.timestamp(),
            delay_message.delivery_tag,
            delay_message,
        ))

    def qsize(self):
        return self._queue.qsize()

    def full(self):
        return (
            self._max_size is not None
            and self.qsize() >= self._max_size
        )
