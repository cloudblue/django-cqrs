#  Copyright © 2022 Ingram Micro Inc. All rights reserved.


def batch_qs(qs, batch_size=10000):
    """
    Helper function to manage RAM usage on big dataset iterations.
    This function can be used only on STATIC DB state. It's a good fit for migrations, but
    it can't be used in real applications.
    """
    assert batch_size > 0

    total = qs.count()
    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        yield qs[start:end]
