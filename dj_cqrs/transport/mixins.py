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
            logger.info('CQRS is denied: pk = {} ({}).'.format(payload.pk, payload.cqrs_id))

    @staticmethod
    def log_produced(payload):
        """
        :param dj_cqrs.dataclasses.TransportPayload payload: Transport payload from master model.
        """
        logger.info('CQRS is published: pk = {} ({}).'.format(payload.pk, payload.cqrs_id))
