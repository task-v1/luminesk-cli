# Bundled Nesk 2.0 build fixture.
FROM python:3.13-slim AS build
RUN python -m venv /nesk-out/.venv \
    && /nesk-out/.venv/bin/pip install --no-cache-dir endstone
FROM scratch
COPY --from=build /nesk-out/.venv/ /nesk-out/.venv/
