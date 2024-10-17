FROM python:3.11-slim

# Set environment variables
ENV PATH="/root/.local/bin:$PATH"
ENV POETRY_VERSION=1.8.0
ENV TRUFFLEHUG_VERSION=3.82.9

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        # deps for installing poetry
        curl \
        # deps for building python deps
        build-essential

# Install Poetry and trufflehog
RUN python3 -m pip install --user pipx \
    && python3 -m pipx ensurepath \
    && pipx install poetry==${POETRY_VERSION} \
    && poetry config virtualenvs.create false \
    && curl -sSfL https://raw.githubusercontent.com/trufflesecurity/trufflehog/${POETRY_VERSION}/scripts/install.sh | sh -s -- -b /usr/local/bin

# Set the working directory
WORKDIR /app

# Copy the pyproject.toml and poetry.lock files first
COPY pyproject.toml poetry.lock ./

# Install the dependencies
RUN poetry install --no-root --no-dev \ 
&& python3 -m spacy download en_core_web_lg

# Copy the rest of the application code
COPY . .

# Expose the port your application will run on
EXPOSE 8080

# Set Gunicorn as the entry point to run the Flask app
ENTRYPOINT ["python3"]

# Set the default command to run the application with Gunicorn
CMD ["src/app.py"]