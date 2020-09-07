.. _transports:

Transports
==========

`django-cqrs` ships with two transport that allow users to choose the messaging broker
that best fit their needs.


RabbitMQ transport
------------------


The :class:`dj_cqrs.transport.RabbitMQTransport` transport
is based on the `pika <https://pika.readthedocs.io/en/stable/>`_ messaging library.

To configure the ``RabbitMQTransport`` you must provide the rabbitmq connection url:

.. code-block:: python

    CQRS = {
        'transport': 'dj_cqrs.transport.RabbitMQTransport',
        'url': 'amqp://guest:guest@rabbit:5672/'
    }

.. warning::

    Previous versions of the ``RabbitMQTransport`` use the attributes
    ``host``, ``port``, ``user``, ``password`` to configure the connection
    with rabbitmq. These attributes are deprecated and will be removed in 
    future versions of `django-cqrs`.


Kombu transport
---------------

The :class:`dj_cqrs.transport.KombuTransport` transport
is based on the `kombu <https://kombu.readthedocs.io/en/master/index.html>`_ messaging library.

Kombu supports different messaging brokers like RabbitMQ, Redis, Amazon SQS etc.

To configure the ``KombuTransport`` you must provide the rabbitmq connection url:

.. code-block:: python

    CQRS = {
        'transport': 'dj_cqrs.transport.KombuTransport',
        'url': 'redis://redis:6379/'
    }

Please read `https://kombu.readthedocs.io/en/master/introduction.html#transport-comparison <https://kombu.readthedocs.io/en/master/introduction.html#transport-comparison>`_
and `https://kombu.readthedocs.io/en/master/userguide/connections.html#urls <https://kombu.readthedocs.io/en/master/userguide/connections.html#urls>`_ for 
more information on supported brokers and configuration urls.
