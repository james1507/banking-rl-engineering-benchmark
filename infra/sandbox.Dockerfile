FROM banking-rl-lab:local
USER root
RUN find /app -mindepth 1 -maxdepth 1 ! -name .venv -exec rm -rf {} +
USER lab
WORKDIR /candidate
ENV PYTHONPATH=/candidate/src:/candidate
