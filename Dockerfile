FROM python:3.11-slim AS builder
RUN python -m pip install pdm==2.8.1
RUN pdm config python.use_venv false

COPY pyproject.toml pdm.lock /project/
WORKDIR /project
RUN pdm install --prod --no-lock --no-editable

FROM python:3.11-slim AS bot
ENV PYTHONPATH=/project/pkgs

COPY src/ /project/pkgs/

# this will change most often
COPY --from=builder /project/__pypackages__/3.11/lib /project/pkgs
WORKDIR /project
ENTRYPOINT ["python", "-m", "tenpo"]
