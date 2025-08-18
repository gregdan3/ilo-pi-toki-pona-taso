FROM python:3.11-slim AS deps

RUN python -m pip --no-cache-dir install pdm==2.25.6
COPY pyproject.toml pdm.lock /project/
WORKDIR /project
RUN mkdir __pypackages__ && pdm sync --prod --no-editable -vv

FROM python:3.11-slim AS bot
ENV PYTHONPATH=/project/pkgs

COPY src/ /project/pkgs/

# this will change most often
COPY --from=deps /project/__pypackages__/3.11/lib /project/pkgs
WORKDIR /project
ENTRYPOINT ["python", "-m", "tenpo"]
