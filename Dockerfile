FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY fixtures ./fixtures
COPY rubrics ./rubrics

RUN pip install --no-cache-dir .

USER nobody

# Offline demo. Does not call a model vendor.
CMD ["python", "-m", "hemp", "demo", "--artifact-dir", "/tmp/hemp-demo"]
