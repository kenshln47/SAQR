# Local only. The process binds 127.0.0.1 inside the container.
# On Linux publish it with: docker run --network host ...
# Do not switch the app to 0.0.0.0 to make the port mapping look easier.
FROM python:3.12-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates git \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /uvx /bin/

WORKDIR /app
COPY pyproject.toml uv.lock requirements.txt ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .
ENV SAQR_PORT=8765
EXPOSE 8765
CMD ["uv", "run", "--no-dev", "python", "-m", "app.server"]
