#  Copyright © 2021 Ingram Micro Inc. All rights reserved.

from dj_cqrs.transport.base import BaseTransport

import pytest


def test_base_transport_consume():
    with pytest.raises(NotImplementedError):
        BaseTransport.consume(None)


def test_base_transport_produce():
    with pytest.raises(NotImplementedError):
        BaseTransport.produce(None)
