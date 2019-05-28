from __future__ import unicode_literals

import pytest
from django.db.models.signals import post_save

from tests.dj_master import models


@pytest.mark.parametrize('model', (models.AllFieldsModel, models.BasicFieldsModel))
def test_signals_are_registered(model):
    assert post_save.has_listeners(model)
