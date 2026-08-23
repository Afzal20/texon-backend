FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
 && rm -rf /var/lib/apt/lists/*

# Copy project
COPY . /app

# Install dependencies
RUN pip install --upgrade pip
# Install the project from pyproject.toml (PEP 517/621) and runtime tools.
RUN pip install .
RUN pip install gunicorn

# Collect static
RUN python manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
