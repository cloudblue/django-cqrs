#  Copyright © 2023 CloudBlue Inc. All rights reserved.

from dj_cqrs.transport.mock import TransportMock


def test_mock_transport():
    assert TransportMock.produce('abc') == 'abc'
