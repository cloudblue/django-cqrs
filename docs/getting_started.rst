***************
Getting started
***************

.. note::

    This guide assumes that you have at least a single instance of `RabbitMQ <https://www.rabbitmq.com/>`_
    up and running.
    For other messaging brokers/transports please see :ref:`transports`.



Requirements
============

`django-cqrs` works with Python 3.6 or later and has the following dependencies:

    * Django >= 1.11.20
    * pika 1.1.0
    * kombu 4.6
    * ujson 3.0.0
    * django-model-utils 4.0.0


Install
=======

`django-cqrs` can be installed from pypi.org with pip:

.. code-block:: shell

    $ pip install django-cqrs



Master service
==============

Configure master service
------------------------

Add dj_cqrs to Django ``INSTALLED_APPS``:

.. code-block:: python

    INSTALLED_APPS = [
        ...
        'dj_cqrs',
        ...
    ]


and add the `django-cqrs` configuration:

.. code-block:: python

    CQRS = {
        'transport': 'dj_cqrs.transport.RabbitMQTransport',
        'url': 'amqp://guest:guest@rabbit:5672/'
    }


Setup master models
-------------------

To setup master models add the ``dj_cqrs.mixins.MasterMixin`` to your model.

For example:

.. code-block:: python

    from django.db import models

    from dj_cqrs.mixins import MasterMixin


    class MyMasterModel(MasterMixin, models.Model):

        CQRS_ID = 'my_model'  # each model must have its unique CQRS_ID

        my_field = models.CharField(max_length=100)
        ....


Create and run migrations for master
------------------------------------

Since the ``MasterMixin`` adds the ``cqrs_revision`` and ``cqrs_updated`` fields
to the model, you must create a new migration for it:

.. code-block:: shell

    $ ./manage.py makemigrations
    $ ./manage.py migrate


Run your django application
---------------------------


.. code-block:: shell

    $ ./manage.py runserver




Replica service
===============

Configure replica service
-------------------------

Add dj_cqrs to Django ``INSTALLED_APPS``:

.. code-block:: python

    INSTALLED_APPS = [
        ...
        'dj_cqrs',
        ...
    ]


and add the `django-cqrs` configuration:

.. code-block:: python
    :emphasize-lines: 4

    CQRS = {
        'transport': 'dj_cqrs.transport.RabbitMQTransport',
        'url': 'amqp://guest:guest@rabbit:5672/',
        'queue': 'my_replica', # Each replica service must have a unique queue.
    }


Setup replica models
--------------------

To setup replica models add the ``dj_cqrs.mixins.ReplicaMixin`` to each model.

For example:

.. code-block:: python

    from django.db import models

    from dj_cqrs.mixins import ReplicaMixin


    class MyReplicaModel(MasterMixin, models.Model):

        CQRS_ID = 'my_model' 

        my_field = models.CharField(max_length=100)
        ....


Create and run migrations for replica
-------------------------------------

Since the ``ReplicaMixin`` adds the ``cqrs_revision`` and ``cqrs_updated`` fields
to the model, you must create a new migration for it:

.. code-block:: shell

    $ ./manage.py makemigrations
    $ ./manage.py migrate


Run consumer process
--------------------

.. code-block:: shell

    $ ./manage.py cqrs_consume -w 2


And that's all!

Now every time you modify your master model, changes are replicated to
all the service that have a replica model with the same CQRS_ID.
