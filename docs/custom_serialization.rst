Custom serialization
====================

By default, `django-cqrs` serializes all the fields declared for the
master model or the subset specified by the ``CQRS_FIELDS`` attribute.

Sometimes you want to customize how the master model will be serialized, for example
including some other fields from related models.

.. warning::

    When there are master models with related entities in CQRS_SERIALIZER, it's important to have operations 
    within atomic transactions. CQRS sync will happen on transaction commit. Please, avoid saving master model
    within transaction more then once to reduce syncing and potential racing on replica side.
    Updating of related model won't trigger CQRS automatic synchronization for master model. 
    This needs to be done manually.

Master service
--------------

In this case you can control how an instance of the master model is serialized providing
a serializer class to be used for that:

.. code-block:: python


    class MyMasterModel(MasterMixin):
        CQRS_ID = 'my_model'
        CQRS_SERIALIZER = 'mymodule.serializers.MyMasterModelSerializer'

        @classmethod
        def relate_cqrs_serialization(cls, queryset):
            # Optimize related models fetching here
            return queryset

If you would to serialize fields from related models, you can optimize 
database access overriding the ``relate_cqrs_serialization`` method using the 
`select_related <https://docs.djangoproject.com/en/3.0/ref/models/querysets/#select-related>`_
and `prefetch_related <https://docs.djangoproject.com/en/3.0/ref/models/querysets/#prefetch-related>`_ methods of the
`QuerySet <https://docs.djangoproject.com/en/3.0/ref/models/querysets/#queryset-api-reference>`_ object.

Replica service
---------------

If you provide a serializer to customize serialization, you must handle
yourself deserialization for the replica model.

.. code-block:: python


    class MyReplicaModel(ReplicaMixin):
        CQRS_ID = 'my_model'
        CQRS_CUSTOM_SERIALIZATION = True # bypass default deserialization.
    
        @classmethod
        def cqrs_create(cls, sync, mapped_data, previous_data=None):
            # Custom deserialization logic here
            pass
            
        def cqrs_update(self, sync, mapped_data, previous_data=None):
            # Custom deserialization logic here
            pass

.. note::

    A serializer class must follow these rules:

        * The constructor must accept the model instance as the only positional argument
        * Must have a ``data`` property that returns a python dictionary as the instance
          representation.

    If your service exposes a RESTful API written using 
    `Django REST framework <https://www.django-rest-framework.org/api-guide/serializers/>`_
    you can use your model serializers out of the box also for CQRS serialization.

