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

    * Django >= 2.2
    * pika >= 1.0.0
    * kombu >= 4.6
    * ujson >= 3.0.0
    * django-model-utils >= 4.0.0
    * python-dateutil >= 2.4


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


    class MyReplicaModel(ReplicaMixin, models.Model):

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
all services that have a replica model with the same CQRS_ID.

Use of customized meta data
===========================

The library allow us to send customized metadata from the Master models to the Replica ones.

Configuring the metadata for Master model
-----------------------------------------

There are two ways to specify what we want to include in this metadata, overriding the master function or setting a default generic function that will be executed for all masters.


Override master function
^^^^^^^^^^^^^^^^^^^^^^^^

Inside the Master model class you have to add the **get_cqrs_meta** function that will replace the default one (that returns an empty dict). For instance if you want to return the access of a given model instance inside the metadata you could do the following:

.. code-block:: python

    def get_cqrs_meta(self, **kwargs):
        meta = super().get_cqrs_meta(**kwargs)
        if self.is_owner():
            meta['access']['owner'] = True
            meta['access']['others'] = False
        else:
            meta['access']['owner'] = False
            meta['access']['others'] = True
        return meta


Setting a default generic function
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In the django settings you could configure a function that will be executed everytime an event is emitted in any Master:

.. code-block:: python

    from ... import get_cqrs_meta

    CQRS = {
        ...
        'master': {
            ...
            'meta_function': get_cqrs_meta,
        },
    }

Retrieving the metadata from the Replica model
----------------------------------------------

From the replica model you will now receive an additional parameter called **meta** that will contain all metadata set in the Master model. These data will be present in the following class functions:
* cqrs_update
* cqrs_create
* cqrs_delete

For instance replacing the **cqrs_update** we could do something like:

.. code-block:: python

    def cqrs_update(self, sync, mapped_data, previous_data=None, meta=None):
        if meta and not meta['access']['owner']:
            # Call asynchronously external system to update some resource.
        else:
            # Call asynchronously internal system to update some resource.
        return super().cqrs_update(sync, mapped_data, previous_data, meta)
