FROM python:3.14.4-slim@sha256:2ca02f32b4d9d893863367ce07ec1972819f476dd38d8612f2a9cb6a41cbb727 AS wheels
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
WORKDIR /build
COPY requirements.lock.txt ./requirements.lock.txt
RUN python -m pip wheel --require-hashes --wheel-dir=/wheels -r requirements.lock.txt

FROM python:3.14.4-slim@sha256:2ca02f32b4d9d893863367ce07ec1972819f476dd38d8612f2a9cb6a41cbb727 AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.lock.txt /tmp/requirements.lock.txt
COPY --from=wheels /wheels /wheels
RUN python -m pip install --no-index --find-links=/wheels --require-hashes -r /tmp/requirements.lock.txt \
    && rm -rf /wheels /tmp/requirements.lock.txt \
    && groupadd --system --gid 10001 verifier \
    && useradd --system --uid 10001 --gid 10001 --home-dir /nonexistent --shell /usr/sbin/nologin verifier
COPY --chown=10001:10001 main.py /app/main.py
USER 10001:10001
EXPOSE 8080
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--no-access-log", "--no-server-header"]
