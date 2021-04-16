#  Copyright © 2021 Ingram Micro Inc. All rights reserved.

import logging


logger = logging.getLogger('django-cqrs')


class LoggingMixin:
    _BASE_PAYLOAD_LOG_TEMPLATE = "CQRS is %s: pk = %s (%s), correlation_id = %s."

    @staticmethod
    def log_consumed(payload):
        """
        :param dj_cqrs.dataclasses.TransportPayload payload: Transport payload from master model.
        """
        msg = "CQRS is received: pk = %s (%s), correlation_id = %s."
        logger.info(msg, payload.pk, payload.cqrs_id, payload.correlation_id)

    @staticmethod
    def log_consumed_accepted(payload):
        """
        :param dj_cqrs.dataclasses.TransportPayload payload: Transport payload from master model.
        """
        msg = "CQRS is applied: pk = %s (%s), correlation_id = %s."
        logger.info(msg, payload.pk, payload.cqrs_id, payload.correlation_id)

    @staticmethod
    def log_consumed_denied(payload):
        """
        :param dj_cqrs.dataclasses.TransportPayload payload: Transport payload from master model.
        """
        msg = "CQRS is denied: pk = %s (%s), correlation_id = %s."
        logger.warning(msg, payload.pk, payload.cqrs_id, payload.correlation_id)

    @staticmethod
    def log_consumed_failed(payload):
        """
        :param dj_cqrs.dataclasses.TransportPayload payload: Transport payload from master model.
        """
        msg = (
            "CQRS is failed: pk = %s (%s), correlation_id = %s, retries = %s.",
        )
        logger.warning(
            msg, payload.pk, payload.cqrs_id, payload.correlation_id, payload.retries,
        )

    @staticmethod
    def log_dead_letter(payload):
        """
        :param dj_cqrs.dataclasses.TransportPayload payload: Transport payload from master model.
        """
        msg = "CQRS is added to dead letter queue: pk = %s (%s), correlation_id = %s."
        logger.warning(msg, payload.pk, payload.cqrs_id, payload.correlation_id)

    @staticmethod
    def log_delayed(payload, delay, eta):
        """
        :param dj_cqrs.dataclasses.TransportPayload payload: Transport payload from master model.
        :param delay: Seconds to wait before requeuing message.
        :param eta: Requeuing datetime.
        """
        msg = (
            "CQRS is delayed: pk = %s (%s), correlation_id = %s, delay = %s sec, eta = %s.",
        )
        logger.warning(
            msg, payload.pk, payload.cqrs_id, payload.correlation_id,  delay, eta,
        )

    @staticmethod
    def log_requeued(payload):
        """
        :param dj_cqrs.dataclasses.TransportPayload payload: Transport payload from master model.
        """
        msg = (
            "CQRS is requeued: pk = %s (%s), correlation_id = %s.",
        )
        logger.warning(msg, payload.pk, payload.cqrs_id, payload.correlation_id)

    @staticmethod
    def log_produced(payload):
        """
        :param dj_cqrs.dataclasses.TransportPayload payload: Transport payload from master model.
        """
        msg = "CQRS is published: pk = %s (%s), correlation_id = %s."
        logger.info(msg, payload.pk, payload.cqrs_id, payload.correlation_id)
