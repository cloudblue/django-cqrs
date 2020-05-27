#  Copyright © 2020 Ingram Micro Inc. All rights reserved.

import pytest

from dj_cqrs.metas import _MetaUtils


@pytest.mark.django_db
def test_no_cqrs_id():
    with pytest.raises(AssertionError) as e:

        class Cls(object):
            CQRS_ID = None

        _MetaUtils.check_cqrs_id(Cls)

    assert str(e.value) == 'CQRS_ID must be set for every model, that uses CQRS.'
