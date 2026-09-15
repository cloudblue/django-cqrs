Transports
==========

**django-cqrs** ships with two transport that allow users to
choose the messaging broker that best fit their needs.

# RabbitMQ transport

The `dj_cqrs.transport.RabbitMQTransport` transport is based on the
[pika](https://pika.readthedocs.io/en/stable/) messaging library.

To configure the `RabbitMQTransport` you must provide the rabbitmq
connection url:

``` py3
CQRS = {
    'transport': 'dj_cqrs.transport.RabbitMQTransport',
    'url': 'amqp://guest:guest@rabbit:5672/'
}
```

!!! warning

    Previous versions of the `RabbitMQTransport` use the attributes `host`,
    `port`, `user`, `password` to configure the connection with rabbitmq.
    These attributes are deprecated and will be removed in future versions
    of **django-cqrs**.

## Producer connections

The transport keeps **one producer connection per thread** and reuses it for every signal
type, as long as it is still open and was last used no longer than
`RabbitMQTransport.PRODUCER_IDLE_MAX_SECONDS` (30 seconds) ago. A pika `BlockingConnection`
is not thread-safe, so it is never shared between threads.

A `BlockingConnection` only services heartbeats while the application is inside a pika call,
so the broker closes a connection that stayed idle for about 2-3x the heartbeat while pika
still reports it as open. The idle window keeps connections well below that limit and
therefore **requires the broker heartbeat to be 60 seconds or more** (the RabbitMQ default);
lower it only together with `PRODUCER_IDLE_MAX_SECONDS`.

A connection dropped because it exceeded the idle window is not closed gracefully: closing a
connection the broker may already have killed raises the very error this avoids. It is simply
discarded, and the broker releases it when its heartbeat times out.

# Kombu transport

The `dj_cqrs.transport.KombuTransport` transport is based on the
[kombu](https://kombu.readthedocs.io/en/master/index.html) messaging
library.

Kombu supports different messaging brokers like RabbitMQ, Redis, Amazon
SQS etc.

To configure the `KombuTransport` you must provide the rabbitmq
connection url:

``` py3
CQRS = {
    'transport': 'dj_cqrs.transport.KombuTransport',
    'url': 'redis://redis:6379/'
}
```

Please read [Transport
Comparison](https://kombu.readthedocs.io/en/master/introduction.html#transport-comparison)
and [URLs](https://kombu.readthedocs.io/en/master/userguide/connections.html#urls)
articles for Kombu to get more information on supported brokers and
configuration urls.
