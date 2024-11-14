FROM python:3.12

# Install ffmpeg curl
RUN apt-get update && apt-get install -y ffmpeg curl

# Set the working directory
WORKDIR /app

# Install poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:/root/.poetry/bin:$PATH"

# Copy the poetry files
COPY pyproject.toml poetry.lock /app/

# Configure poetry
RUN poetry config virtualenvs.create false
RUN poetry install


# Create entrypoint
CMD ["poetry", "run", "python3", "src/main.py"]

