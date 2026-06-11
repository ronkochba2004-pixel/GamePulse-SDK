FROM python:3.11-slim
WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml ./
COPY packages/gamepulse-core ./packages/gamepulse-core
COPY packages/gamepulse-sdk ./packages/gamepulse-sdk
COPY packages/gamepulse-simulator ./packages/gamepulse-simulator

RUN uv pip install --system \
    -e ./packages/gamepulse-core \
    -e ./packages/gamepulse-sdk \
    -e ./packages/gamepulse-simulator

WORKDIR /app/packages/gamepulse-simulator
CMD ["python", "-m", "simulator", "--players", "25", "--duration", "60"]
