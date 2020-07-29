Keep track of changes to fields
===============================

In some circumstances, you want to keep track of changes made on some fields of the master model.

`django-cqrs` can send previous values of the tracked fields to replicas.

To do so, you can use the ``CQRS_TRACKED_FIELDS`` attribute to specify which fields to track:

.. code-block:: python

    class MyMasterModel(MasterMixin):

        CQRS_ID = 'my_model'
        CQRS_TRACKED_FIELDS = ('char_field', 'parent', 'status')
        

        char_field = models.CharField(max_length=100)
        status = models.CharField(max_length=15, choices=STATUSES)

        parent = models.ForeignKey(ParentMode, on_delete=models.CASCADE)


This way, you can override the ``cqrs_save`` and apply your persistence logic
based o tracked fields before accessing your database:


.. code-block:: python

    class MyReplicaModel(ReplicaMixin):

        CQRS_ID = 'my_model'

    @classmethod
    def cqrs_save(cls, master_data, previous_data=None, sync=False):
        # Custom logic based on previous_data here.
        pass
    

.. note::

    The fields tracking features honors the ``CQRS_MAPPING`` attribute.  


.. note::

    The fields tracking features relies on the 
    `FieldTracker <https://django-model-utils.readthedocs.io/en/latest/utilities.html#field-tracker>`_
    utility class from the `django-model-utils <https://github.com/jazzband/django-model-utils>`_ library.
