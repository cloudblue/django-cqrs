.. _lifecycle:

Message lifecycle
=================
.. warning::

    Expiration, retrying and dead letter supports only ``RabbitMQTransport`` (**on** by default).

`django-cqrs` since version 1.11 provides mechanism for reliable message delivery.

.. image:: _static/img/lifecycle.png
   :scale: 50 %
   :alt: Message lifecycle

Expiration
----------
+------------------+------------+--------------------------------------------------------------------------------------------------+
| Name             | Default    | Description                                                                                      |
+==================+============+==================================================================================================+
| CQRS_MESSAGE_TTL | 86400      | Limits message lifetime in **seconds**, after that period it will be moved to dead letter queue. |
+------------------+------------+--------------------------------------------------------------------------------------------------+

.. code-block:: python

    # settings.py

    CQRS = {
        ...
        'master': {
            'CQRS_MESSAGE_TTL': 86400, # 1 day
        },
    }

Fail
----
Message is failed when consume raises any exception or returns negative boolean value (*False*, *None*).

.. code-block:: python

    # models.py

    class Example(ReplicaMixin, models.Model):
        CQRS_ID = 'example'
        ...

        @classmethod
        def cqrs_create(cls, sync, mapped_data, previous_data=None):
            raise Exception("Some issue during create") # exception could be caught at should_retry_cqrs method

        @classmethod
        def cqrs_update(cls, sync, mapped_data, previous_data=None):
            return None # returning negative boolean triggers retrying

Retrying
--------
+----------------------+----------+-----------------------------------------------------------------------------+
| Name                 | Default  | Description                                                                 |
+======================+==========+=============================================================================+
| CQRS_MAX_RETRIES     | 30       | Maximum number of retry attempts. Infinite if *None*, 0 for retry disabling.|
+----------------------+----------+-----------------------------------------------------------------------------+
| CQRS_RETRY_DELAY     | 2        | Constant delay in **seconds** between message fail and requeue.             |
+----------------------+----------+-----------------------------------------------------------------------------+
| delay_queue_max_size | *None*   | Maximum number of delayed messages per worker. Infinite if *None*.          |
+----------------------+----------+-----------------------------------------------------------------------------+

.. code-block:: python

    # settings.py

    CQRS = {
        ...
        'replica': {
            'CQRS_MAX_RETRIES': 30, # attempts
            'CQRS_RETRY_DELAY': 2,  # seconds
            'delay_queue_max_size': None, # infinite
        },
    }

Customization
^^^^^^^^^^^^^
The :class:`dj_cqrs.mixins.ReplicaMixin` allows to set retrying behaviour manually.

.. code-block:: python

    # models.py

    class Example(ReplicaMixin, models.Model):
        CQRS_ID = 'example'
        ...

        @classmethod
        def get_cqrs_retry_delay(cls, current_retry=0):
            # Linear delay growth
            return (current_retry + 1) * 60

        @classmethod
        def should_retry_cqrs(cls, current_retry, exception=None):
            # Retry 10 times or until we have troubles with database
            return (
                current_retry < 10
                or isinstance(exception, django.db.OperationalError)
            )

Dead letter
-----------
Expired or failed messages which should not be retried moved to dead letter queue.

+-------------------+------------------------+----------------------------------------------------+
| Name              | Default                | Description                                        |
+===================+========================+====================================================+
| dead_letter_queue | dead_letter + queue    | Queue name for dead letter messages.               |
+-------------------+------------------------+----------------------------------------------------+
| dead_message_ttl  | 864000                 | Expiration **seconds**. Infinite if *None*.        |
+-------------------+------------------------+----------------------------------------------------+

.. code-block:: python

    # settings.py

    CQRS = {
        ...
        'queue': 'example',
        'replica': {
            ...
            'dead_letter_queue': 'dead_letter_example', # generates from CQRS.queue
            'dead_message_ttl': 864000, # 10 days
        },
    }

