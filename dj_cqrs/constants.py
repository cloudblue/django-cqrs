#  Copyright © 2021 Ingram Micro Inc. All rights reserved.

ALL_BASIC_FIELDS = '__all__'

FIELDS_TRACKER_FIELD_NAME = '__fields_tracker'
TRACKED_FIELDS_ATTR_NAME = '__tracked_fields'


class SignalType:
    """Type of signal that generates this event."""

    SAVE = 'SAVE'
    """The master model has been saved."""

    DELETE = 'DELETE'
    """The master model has been deleted."""

    SYNC = 'SYNC'
    """The master model needs syncronization."""


NO_QUEUE = 'None'

DEFAULT_DEAD_MESSAGE_TTL = 864000  # 10 days

DEFAULT_MASTER_AUTO_UPDATE_FIELDS = False
DEFAULT_MASTER_MESSAGE_TTL = 86400  # 1 day

DEFAULT_REPLICA_MAX_RETRIES = 30
DEFAULT_REPLICA_RETRY_DELAY = 2  # seconds
DEFAULT_REPLICA_DELAY_QUEUE_MAX_SIZE = 1000
