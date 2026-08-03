from copy import deepcopy

import pytest

from app.main import DEFAULT_TASKS, create_app


@pytest.fixture()
def client():
    app = create_app()
    app.config["TESTING"] = True
    app.config["TASKS"] = deepcopy(DEFAULT_TASKS)

    with app.test_client() as test_client:
        yield test_client


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_list_tasks(client):
    response = client.get("/tasks")
    body = response.get_json()

    assert response.status_code == 200
    assert isinstance(body, list)
    assert len(body) == 2


def test_create_task(client):
    response = client.post(
        "/tasks",
        json={"title": "Document the API", "description": "Add README examples"},
    )
    body = response.get_json()

    assert response.status_code == 201
    assert body["id"] == 3
    assert body["title"] == "Document the API"
    assert body["description"] == "Add README examples"
    assert body["done"] is False


def test_create_task_requires_title(client):
    response = client.post("/tasks", json={"description": "Missing title"})

    assert response.status_code == 400
    assert response.get_json()["error"] == "title is required"


def test_update_task_fields(client):
    response = client.put(
        "/tasks/2",
        json={"title": "Ship the CI pipeline", "description": "Push image to GHCR", "done": True},
    )
    body = response.get_json()

    assert response.status_code == 200
    assert body["title"] == "Ship the CI pipeline"
    assert body["description"] == "Push image to GHCR"
    assert body["done"] is True


def test_update_task_requires_non_empty_title(client):
    response = client.put("/tasks/1", json={"title": "   "})

    assert response.status_code == 400
    assert response.get_json()["error"] == "title cannot be empty"


def test_update_task_requires_boolean_done(client):
    response = client.put("/tasks/1", json={"done": "yes"})

    assert response.status_code == 400
    assert response.get_json()["error"] == "done must be a boolean"


def test_update_task_not_found(client):
    response = client.put("/tasks/999", json={"done": True})

    assert response.status_code == 404
    assert response.get_json()["error"] == "task not found"
