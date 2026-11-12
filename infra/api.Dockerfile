FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b
RUN pip install --no-cache-dir uv==0.13.7
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --all-extras --no-install-project
COPY . .
RUN uv sync --locked --all-extras && useradd --uid 1000 --create-home lab && chown -R lab:lab /app
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 UV_CACHE_DIR=/tmp/uv-cache
USER lab
CMD ["uvicorn", "banking_lab.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
