API Reference
=============


Mixins
------

.. autoclass:: dj_cqrs.mixins.RawMasterMixin
   :members:
   :exclude-members: save

.. autoclass:: dj_cqrs.mixins.MasterMixin
   :members:
   :show-inheritance:


.. autoclass:: dj_cqrs.mixins.ReplicaMixin
   :members:


Managers
--------

.. autoclass:: dj_cqrs.managers.MasterManager
   :members:


.. autoclass:: dj_cqrs.managers.ReplicaManager
   :members:


Signals
-------

.. automodule:: dj_cqrs.signals
   :members: post_bulk_create, post_update

.. autoclass:: dj_cqrs.signals.MasterSignals
   :members:



Transports
----------

.. autoclass:: dj_cqrs.transport.BaseTransport
   :members:

.. autoclass:: dj_cqrs.transport.RabbitMQTransport
   :members:

.. autoclass:: dj_cqrs.transport.KombuTransport
   :members:

.. autoclass:: dj_cqrs.constants.SignalType
   :members:

.. autoclass:: dj_cqrs.dataclasses.TransportPayload
   :members:


Registries
----------

.. autoclass:: dj_cqrs.registries.MasterRegistry
   :members: register_model, get_model_by_cqrs_id


.. autoclass:: dj_cqrs.registries.ReplicaRegistry
   :members: register_model, get_model_by_cqrs_id