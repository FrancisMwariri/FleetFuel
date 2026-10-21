FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir -r requirements.txt \
    && useradd --create-home --uid 10001 fleetfuel \
    && mkdir -p /app/private_uploads \
    && chown -R fleetfuel:fleetfuel /app

COPY --chown=fleetfuel:fleetfuel app ./app
COPY --chown=fleetfuel:fleetfuel migrations ./migrations
COPY --chown=fleetfuel:fleetfuel alembic.ini ./alembic.ini

USER fleetfuel
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]