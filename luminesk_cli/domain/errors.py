"""Stable, renderer-independent errors used by the 2.0 command surface."""

from __future__ import annotations

from enum import IntEnum
from typing import Any


class ErrorCode(IntEnum):
    """Process exit codes shared by plain, interactive and JSON renderers."""

    OK = 0
    USAGE = 2
    VALIDATION = 3
    RESOLUTION = 4
    NETWORK = 5
    SECURITY = 6
    CONFLICT = 7
    RUNTIME = 8
    TRANSACTION = 9
    INTERNAL = 10


class LumineskError(Exception):
    """Base exception carrying a stable code and structured context."""

    code = ErrorCode.INTERNAL

    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class ValidationError(LumineskError):
    """A manifest, lock, package, or instance violated its contract."""

    code = ErrorCode.VALIDATION


class ResolutionError(LumineskError):
    """A declared source could not be resolved unambiguously."""

    code = ErrorCode.RESOLUTION


class NetworkError(LumineskError):
    """A bounded network operation failed."""

    code = ErrorCode.NETWORK


class SecurityError(LumineskError):
    """Untrusted input violated a security boundary."""

    code = ErrorCode.SECURITY


class ConflictError(LumineskError):
    """Applying a plan would overwrite user-owned state."""

    code = ErrorCode.CONFLICT


class RuntimeOperationError(LumineskError):
    """A runtime driver operation failed."""

    code = ErrorCode.RUNTIME


class TransactionError(LumineskError):
    """An install or update transaction could not commit safely."""

    code = ErrorCode.TRANSACTION
