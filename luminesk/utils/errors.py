from __future__ import annotations


def format_error(error: object) -> str:
    text = str(error).strip()

    if text:
        return text

    if isinstance(error, BaseException):
        return error.__class__.__name__

    return "Unknown error"
