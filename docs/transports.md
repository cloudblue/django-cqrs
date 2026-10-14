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

The transport keeps **one producer connection per thread** and uses it for every signal
type. A pika `BlockingConnection` is not thread-safe, so it is never shared between threads.

Inside a request the connection is handled the way Django handles a database connection with
`CONN_MAX_AGE=0`: opened on the first publish, reused for the rest of the request and closed
in order when the response is done (a `request_finished` receiver calls
`RabbitMQTransport.clean_connection()`). A `BlockingConnection` only services heartbeats while
the application is inside a pika call, so a connection kept by a thread waiting for its next
request sends none, and the broker closes it after 2-3x the heartbeat while pika still reports
it as open.

Outside requests (consumer requeues, management commands) the connection is reused while it
was last used no longer than `RabbitMQTransport.PRODUCER_ASSUMED_ALIVE_SECONDS` (90 seconds)
ago, 30 seconds below the earliest moment the broker may close a silent connection with the
default heartbeat. This **requires the broker heartbeat to be 60 seconds or more** (the
RabbitMQ default); lower it only together with `PRODUCER_ASSUMED_ALIVE_SECONDS`.

A connection idle for longer is not closed gracefully: closing a connection the broker may
already have killed makes pika log the very error this avoids. It is simply discarded, and the
broker releases it when its heartbeat times out.

Closing in order waits for the broker's reply. If the broker vanishes without closing the
socket, pika's heartbeat checker ends the wait after about two heartbeat intervals, so a
thread may stall after its response was sent, only while the broker is down.

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
