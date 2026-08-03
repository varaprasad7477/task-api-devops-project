from copy import deepcopy

from flask import Flask, jsonify, request

DEFAULT_TASKS = [
    {"id": 1, "title": "Set up Docker", "description": "Containerize the API", "done": True},
    {"id": 2, "title": "Write CI pipeline", "description": "Run pytest on every push", "done": False},
]


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["TASKS"] = deepcopy(DEFAULT_TASKS)

    @app.get("/health")
    def health():
        return jsonify(status="ok"), 200

    @app.get("/tasks")
    def list_tasks():
        return jsonify(app.config["TASKS"]), 200

    @app.post("/tasks")
    def create_task():
        payload = request.get_json(silent=True) or {}
        title = str(payload.get("title", "")).strip()
        if not title:
            return jsonify(error="title is required"), 400

        tasks = app.config["TASKS"]
        new_task = {
            "id": (tasks[-1]["id"] + 1) if tasks else 1,
            "title": title,
            "description": str(payload.get("description", "")).strip(),
            "done": bool(payload.get("done", False)),
        }
        tasks.append(new_task)
        return jsonify(new_task), 201

    @app.put("/tasks/<int:task_id>")
    def update_task(task_id: int):
        payload = request.get_json(silent=True) or {}
        title = payload.get("title")
        description = payload.get("description")
        done = payload.get("done")

        if title is None and description is None and done is None:
            return jsonify(error="at least one field must be provided"), 400

        for task in app.config["TASKS"]:
            if task["id"] != task_id:
                continue

            if title is not None:
                title = str(title).strip()
                if not title:
                    return jsonify(error="title cannot be empty"), 400
                task["title"] = title

            if description is not None:
                task["description"] = str(description).strip()

            if done is not None:
                if not isinstance(done, bool):
                    return jsonify(error="done must be a boolean"), 400
                task["done"] = done

            return jsonify(task), 200

        return jsonify(error="task not found"), 404

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
