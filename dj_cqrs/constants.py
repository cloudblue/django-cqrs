#  Copyright © 2020 Ingram Micro Inc. All rights reserved.

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
