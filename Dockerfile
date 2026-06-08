# Diff two datasets from inside a container by mounting them:
#
#   docker build -t dsdiff .
#   docker run --rm -v "$PWD:/w" -w /w dsdiff diff a.parquet b.parquet
#
FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/jmweb-org/dsdiff"
LABEL org.opencontainers.image.description="Diff two dataset files: schema changes plus column-level distribution drift."
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src

RUN pip install --no-cache-dir .

ENTRYPOINT ["dsdiff"]
CMD ["--help"]
