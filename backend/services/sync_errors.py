"""Payroll responses that must not be automatically submitted again."""

import re


def is_duplicate_error(error_code, reason):
    """Recognize explicit punch-duplicate responses, not generic 'already exists' errors.

    A nearby punch is not necessarily the same IN/OUT event. We stop retrying it
    for this destination and preserve the reason, rather than claiming it synced.
    "Sync ID already exists" means Payroll stored this exact punch on an earlier
    attempt whose answer was lost.
    """
    if str(error_code).strip() == '120':
        return True
    message = (reason or '').strip().lower()
    return bool(re.match(r'^(duplicate record\b|time in range\b|sync id already exists\b)', message))


# Per-record answers where Payroll looked at the log and said no, so nothing was
# stored and HR can retry without checking Payroll first. Matches the reason
# text older builds saved (raw Payroll reason or its friendly message).
DEFINITE_REJECTIONS = {
    'no employee',
    'invalid request format',
    'missing required field',
    'invalid date format',
    'invalid time format',
    'invalid employee code',
    'branch not found',
    'employee not found in payroll system',
    'employee is inactive',
    'employee not assigned to branch',
    'employee not recognized in payroll system',
    'invalid log type',
    'record outside allowed date range',
}


def is_definite_rejection(reason):
    return (reason or '').strip().lower() in DEFINITE_REJECTIONS
