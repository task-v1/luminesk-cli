# Bundled Luminesk 2.0 build fixture.
FROM python:3.13-slim AS build
RUN python -m venv /luminesk-out/.venv \
    && /luminesk-out/.venv/bin/pip install --no-cache-dir endstone
FROM scratch
COPY --from=build /luminesk-out/.venv/ /luminesk-out/.venv/
