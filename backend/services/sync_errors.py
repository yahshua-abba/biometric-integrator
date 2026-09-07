"""Payroll responses that must not be automatically submitted again."""

import re


def is_duplicate_error(error_code, reason):
    """Recognize explicit punch-duplicate responses, not generic 'already exists' errors.

    A nearby punch is not necessarily the same IN/OUT event. We stop retrying it
    for this destination and preserve the reason, rather than claiming it synced.
    """
    if str(error_code).strip() == '120':
        return True
    message = (reason or '').strip().lower()
    return bool(re.match(r'^(duplicate record\b|time in range\b)', message))
