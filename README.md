# Task API - Dockerized CI/CD Pipeline

A resume-ready Flask project that exposes a small task management REST API and demonstrates containerization, automated testing, and GitHub Actions based CI/CD.

## Features

- `GET /health` for service and container health checks
- `GET /tasks` to list tasks
- `POST /tasks` to create a task
- `PUT /tasks/<id>` to update task title, description, or completion status
- `pytest` coverage for API behavior and validation paths
- Non-root Docker image with container health checks
- `docker-compose` setup for local app startup and optional containerized test runs
- GitHub Actions workflow that:
  - runs tests on every push and pull request
  - builds and pushes a Docker image to GHCR on pushes to `main`

## Project Structure

```text
task-api-devops-project/
|-- app/
|   `-- main.py
|-- tests/
|   `-- test_main.py
|-- .github/workflows/ci.yml
|-- Dockerfile
|-- docker-compose.yml
|-- requirements.txt
`-- README.md
```

## Run Locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app/main.py
```

The API will be available at `http://localhost:5000`.

## Run Tests

```bash
pytest -v
```

## Run with Docker

```bash
docker build -t task-api .
docker run -p 5000:5000 task-api
```

## Run with Docker Compose

```bash
docker compose up --build
```

To run the tests inside containers:

```bash
docker compose --profile test up --build task-api-tests
```

## Example Requests

Create a task:

```bash
curl -X POST http://localhost:5000/tasks \
  -H "Content-Type: application/json" \
  -d "{\"title\":\"Add GHCR publishing\",\"description\":\"Push image on main\"}"
```

Update a task:

```bash
curl -X PUT http://localhost:5000/tasks/2 \
  -H "Content-Type: application/json" \
  -d "{\"done\":true}"
```

## GitHub Actions Notes

The workflow in `.github/workflows/ci.yml` uses the built-in `GITHUB_TOKEN` to authenticate to GHCR. After pushing this folder to a GitHub repository, merges to `main` will publish:

```text
ghcr.io/<your-github-username>/task-api:latest
```

## Resume Bullet

Task API - Dockerized CI/CD Pipeline | Python (Flask) | Docker | GitHub Actions | pytest

- Built a small REST API with health check, create/list/update task endpoints and automated tests.
- Containerized the service with a non-root Docker image, Docker health checks, and docker-compose for local orchestration.
- Set up a GitHub Actions pipeline to run tests on every push and pull request, then build and push an image to GHCR on merges to `main`.
