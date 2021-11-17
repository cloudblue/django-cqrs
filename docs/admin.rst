Django Admin
====================

Synchronize items
-----------------

Add action to synchronize master items from Django Admin page.

.. code-block:: python

    from django.db import models
    from django.contrib import admin

    from dj_cqrs.admin_mixins import CQRSAdminMasterSyncMixin


    class AccountAdmin(CQRSAdminMasterSyncMixin, admin.ModelAdmin):
        pass


    admin.site.register(models.Account, AccountAdmin)


* If necessary, override ``_cqrs_sync_queryset`` from ``CQRSAdminMasterSyncMixin`` to adjust the QuerySet and use it for synchronization.