#  Copyright © 2021 Ingram Micro Inc. All rights reserved.

import logging


logger = logging.getLogger('django-cqrs')


class LoggingMixin:

    @staticmethod
    def log_consumed(payload):
        """
        :param dj_cqrs.dataclasses.TransportPayload payload: Transport payload from master model.
        """
        if payload.pk:
            logger.info('CQRS is received: pk = {} ({}).'.format(payload.pk, payload.cqrs_id))

    @staticmethod
    def log_consumed_accepted(payload):
        """
        :param dj_cqrs.dataclasses.TransportPayload payload: Transport payload from master model.
        """
        if payload.pk:
            logger.info('CQRS is applied: pk = {} ({}).'.format(payload.pk, payload.cqrs_id))

    @staticmethod
    def log_consumed_denied(payload):
        """
        :param dj_cqrs.dataclasses.TransportPayload payload: Transport payload from master model.
        """
        if payload.pk:
            logger.warning('CQRS is denied: pk = {} ({}).'.format(payload.pk, payload.cqrs_id))

    @staticmethod
    def log_consumed_failed(payload):
        """
        :param dj_cqrs.dataclasses.TransportPayload payload: Transport payload from master model.
        """
        if payload.pk:
            logger.warning(
                'CQRS is failed: pk = {} ({}), retries = {}.'.format(
                    payload.pk, payload.cqrs_id, payload.retries,
                )
            )

    @staticmethod
    def log_delayed(payload, delay, eta):
        """
        :param dj_cqrs.dataclasses.TransportPayload payload: Transport payload from master model.
        :param delay: Seconds to wait before requeuing message.
        :param eta: Requeuing datetime.
        """
        if payload.pk:
            logger.warning(
                'CQRS is delayed: pk = {} ({}), delay = {} sec, eta = {}.'.format(
                    payload.pk, payload.cqrs_id, delay, eta,
                )
            )

    @staticmethod
    def log_requeued(payload):
        """
        :param dj_cqrs.dataclasses.TransportPayload payload: Transport payload from master model.
        """
        if payload.pk:
            logger.warning('CQRS is requeued: pk = {} ({}).'.format(payload.pk, payload.cqrs_id))

    @staticmethod
    def log_produced(payload):
        """
        :param dj_cqrs.dataclasses.TransportPayload payload: Transport payload from master model.
        """
        logger.info('CQRS is published: pk = {} ({}).'.format(payload.pk, payload.cqrs_id))
