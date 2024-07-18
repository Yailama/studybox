# Dockerfile

# Use Python 3.11 base image
FROM python:3.11

# Set the working directory in the container
WORKDIR /app

# Copy the poetry.lock and pyproject.toml to the working directory
COPY poetry.lock pyproject.toml /app/

# Install Poetry
RUN pip install poetry

# Install dependencies using Poetry
RUN poetry config virtualenvs.create false && \
    poetry install --no-dev

# Copy the rest of the application code to the working directory
COPY . .

# Expose port 8000 to the outside world (if needed)
EXPOSE 8000

# Define the command to run your application (modify as needed)
#CMD ["poetry", "run", "uvicorn", "app.main:app", "--reload"]
