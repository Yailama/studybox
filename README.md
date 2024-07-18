# OpenAI Evaluation Microservice

This microservice evaluates speaking and writing answers using OpenAI's powerful language models. It is built with FastAPI for the API framework, Celery for asynchronous task processing, and Redis as the message broker and backend result storage.

## Requirements

- Docker
- docker-compose

## Getting Started

### 1. Clone Repository

```bash
git clone https://github.com/your/repository.git
cd repository
```

### 2. Set Environment Variables

Create a `.env` file in the root directory with required varuables found in `.envrc`:

### 3. Build and Launch with Docker Compose

```bash
docker-compose up --build
```

This command will build the necessary Docker images and start the services defined in `docker-compose.yml`.

### 4. Access the API

Once the services are up and running, you can access the API at `http://localhost:8000`.

### 5. API Documentation

Swagger UI is available for interactive API documentation at `http://localhost:8000/docs`.

## Development

For development purposes, `poetry` is required to manage dependencies. Ensure to update `redis` server to `localhost` if application is running locally.
