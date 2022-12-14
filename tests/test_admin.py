#  Copyright © 2021 Ingram Micro Inc. All rights reserved.

import pytest
from django.contrib import admin

from dj_cqrs.admin import CQRSAdminMasterSyncMixin


class MockAdminModel(CQRSAdminMasterSyncMixin, admin.ModelAdmin):
    pass


@pytest.mark.parametrize(
    ('total_sync', 'total_failed'),
    (
        (2, 1),
        (3, 0),
        (0, 3),
        (0, 0),
    ),
)
def test_sync_items_function(total_sync, total_failed, mocker):
    model_path = 'dj_cqrs.mixins.MasterMixin'
    mock_model = mocker.patch(model_path)
    request = None

    qs = []
    for _ in range(total_sync):
        m = mocker.patch(model_path)
        m.cqrs_sync.return_value = True
        qs.append(m)

    failed_items = []
    for _ in range(total_failed):
        m = mocker.patch(model_path)
        m.cqrs_sync.return_value = False
        qs.append(m)
        failed_items.append(m)

    mixin = MockAdminModel(model=mock_model, admin_site=admin.sites.AdminSite())
    mixin.message_user = mocker.Mock()
    mixin.sync_items(request, qs)

    mixin.message_user.assert_called_once_with(
        request,
        f'{total_sync} successfully synced. {total_failed} failed: {failed_items}',
    )


def test_admin_actions_enabled_with_sync_items_action(mocker):
    mock_model = mocker.Mock()
    request = mocker.patch('django.http.HttpRequest')
    mixin = MockAdminModel(model=mock_model, admin_site=admin.sites.AdminSite())
    actions = mixin.get_actions(request)

    assert 'sync_items' in actions
    assert 'delete_selected' in actions


def test_actions_not_enabled(mocker):
    mock_model = mocker.Mock()
    request = mocker.patch('django.http.HttpRequest')
    mixin = MockAdminModel(model=mock_model, admin_site=admin.sites.AdminSite())
    mixin.actions = None
    actions = mixin.get_actions(request)

    assert actions == {}
