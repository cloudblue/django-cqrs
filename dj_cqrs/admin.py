#  Copyright © 2021 Ingram Micro Inc. All rights reserved.

from django.utils.translation import gettext_lazy


class CQRSAdminMasterSyncMixin:
    """
    Mixin that includes a custom action in AdminModel. This action allows synchronizing
    master's model items from Django Admin page,
    """

    def get_actions(self, request):
        """
        Overriding method from AdminModel class; it is used to include the sync method in
        the actions list.
        """
        if self.actions is not None and 'sync_items' not in self.actions:
            self.actions = list(self.actions) + ['sync_items']
        return super().get_actions(request)

    def _cqrs_sync_queryset(self, queryset):
        """
        This function is used to adjust the QuerySet before sending the sync signal.

        :param queryset: Original queryset
        :type queryset: Queryset
        :return: Updated queryset
        :rtype: Queryset
        """
        return queryset

    def sync_items(self, request, queryset):
        """
        This method synchronizes selected items from the Admin Page.
        It is registered as a custom action in Django Admin
        """
        items_not_synced = []
        for item in self._cqrs_sync_queryset(queryset):
            if not item.cqrs_sync():
                items_not_synced.append(item)

        total = len(queryset)
        total_w_erros = len(items_not_synced)
        total_sucess = total - total_w_erros
        self.message_user(
            request,
            f'{total_sucess} successfully synced. {total_w_erros} failed: {items_not_synced}',
        )

    sync_items.short_description = gettext_lazy(
        'Synchronize selected %(verbose_name_plural)s via CQRS',
    )
