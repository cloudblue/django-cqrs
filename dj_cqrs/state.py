#  Copyright © 2025 CloudBlue Inc. All rights reserved.

import threading


cqrs_state = threading.local()
cqrs_state.bulk_relate_cm = None
