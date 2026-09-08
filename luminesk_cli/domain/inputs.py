"""Typed input resolution and runtime-safe interpolation."""

from __future__ import annotations

import re
from collections.abc import Mapping

from luminesk_cli.domain.errors import ValidationError
from luminesk_cli.domain.manifest import Manifest

type InputValue = str | int | bool

INPUT_REFERENCE_RE = re.compile(r"\$\{input\.([A-Za-z0-9_-]+)\}")


def resolve_inputs(
    manifest: Manifest,
    overrides: Mapping[str, InputValue],
    *,
    require_required: bool = True,
) -> dict[str, InputValue]:
    """Merge validated manifest defaults with explicit input overrides."""

    declared = {item.name: item for item in manifest.inputs}
    unknown = sorted(set(overrides) - set(declared))

    if unknown:
        raise ValidationError(f"unknown input: {unknown[0]}")

    missing = [
        spec
        for spec in manifest.inputs
        if spec.required and spec.default is None and spec.name not in overrides
    ]
    if missing and require_required:
        names = ", ".join(spec.name for spec in missing)
        raise ValidationError(
            f"required inputs have no values: {names}",
            missingInputs=[
                {
                    "name": spec.name,
                    "option": "--set-file" if spec.secret else "--set",
                }
                for spec in missing
            ],
        )

    values: dict[str, InputValue] = {}

    for name, spec in declared.items():
        value = overrides.get(name, spec.default)

        if value is None:
            continue

        expected_type = {"string": str, "integer": int, "boolean": bool}[spec.type]

        if not isinstance(value, expected_type) or (
            spec.type == "integer" and isinstance(value, bool)
        ):
            raise ValidationError(f"input {name} has the wrong type")

        if isinstance(value, int) and not isinstance(value, bool):
            if spec.minimum is not None and value < spec.minimum:
                raise ValidationError(f"input {name} is below its minimum")

            if spec.maximum is not None and value > spec.maximum:
                raise ValidationError(f"input {name} is above its maximum")

        if isinstance(value, str) and spec.pattern is not None:
            if re.fullmatch(spec.pattern, value) is None:
                raise ValidationError(f"input {name} does not match its pattern")

        values[name] = value

    return values


def interpolate_input_references(
    value: str,
    inputs: Mapping[str, InputValue],
    *,
    context: str = "runtime",
) -> str:
    """Replace declared input references without shell or environment expansion."""

    def replace_input(match: re.Match[str]) -> str:
        name = match.group(1)

        if name not in inputs:
            raise ValidationError(f"{context} references missing input: {name}")

        return str(inputs[name])

    return INPUT_REFERENCE_RE.sub(replace_input, value)


def resolve_runtime_port(
    value: int | str,
    inputs: Mapping[str, InputValue],
    *,
    name: str,
) -> int:
    """Resolve and validate one Docker port value."""

    interpolated = interpolate_input_references(str(value), inputs)

    try:
        number = int(interpolated)
    except ValueError as exc:
        raise ValidationError(f"runtime {name} port is not an integer") from exc

    if not 1 <= number <= 65535:
        raise ValidationError(f"runtime {name} port is out of range")

    return number
