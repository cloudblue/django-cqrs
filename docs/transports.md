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
was idle for no longer than `RabbitMQTransport.PRODUCER_ASSUMED_ALIVE_HEARTBEATS` (1.5) times
the heartbeat negotiated with the broker: 90 seconds with the RabbitMQ default of 60, and
always below the 2 heartbeats after which the broker may close a silent connection. The
transport does not set a heartbeat of its own, so the broker's configured value applies. With
heartbeats disabled on the broker the connection is never dropped for being idle.

A connection idle for longer is not closed gracefully: closing a connection the broker may
already have killed makes pika log the very error this avoids. It is simply discarded, and the
broker releases it when its heartbeat times out.

A broker in a memory or disk alarm stops reading from a connection on its first publish during
the alarm and sends it `Connection.Blocked`, so it would not answer a close until the alarm
clears. The transport tracks that notification and drains the broker's pending frames before
closing: a connection still blocked when the request finishes is dropped like an idle one
instead of holding the thread for pika's `blocked_connection_timeout` (10 seconds). The
notification follows the publish by about a round trip, so a request that finishes within that
round trip of its last publish still pays the timeout. What remains otherwise is a broker that
vanished without closing the socket: closing in order waits for its reply with no time bound of
its own, until pika's heartbeat checker gives up after about two heartbeat intervals. That
stalls a thread after its response was sent, and only while the broker is down.

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
