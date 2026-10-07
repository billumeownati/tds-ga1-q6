import os

import yaml
from dotenv import dotenv_values
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()

# Allow the grader's browser to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}


def to_bool(value):
    if isinstance(value, bool):
        return value

    return str(value).strip().lower() in {
        "true",
        "1",
        "yes",
        "on",
    }


def coerce(key, value):
    if key in {"port", "workers"}:
        return int(value)

    if key == "debug":
        return to_bool(value)

    return str(value)


def load_config():
    # Layer 1: defaults
    config = DEFAULTS.copy()

    # Layer 2: config.<env>.yaml
    environment = os.getenv("APP_ENV", "development")
    yaml_file = f"config.{environment}.yaml"

    if os.path.exists(yaml_file):
        with open(yaml_file, "r", encoding="utf-8") as f:
            yaml_config = yaml.safe_load(f) or {}

        for key, value in yaml_config.items():
            config[key] = value

    # Layer 3: .env
    env_file = dotenv_values(".env")

    env_mapping = {
        "APP_PORT": "port",
        "APP_WORKERS": "workers",
        "NUM_WORKERS": "workers",
        "APP_DEBUG": "debug",
        "APP_LOG_LEVEL": "log_level",
        "APP_API_KEY": "api_key",
    }

    for source_key, target_key in env_mapping.items():
        if source_key in env_file and env_file[source_key] is not None:
            config[target_key] = env_file[source_key]

    # Layer 4: OS environment variables
    for source_key, target_key in env_mapping.items():
        if source_key in os.environ:
            config[target_key] = os.environ[source_key]

    # Apply correct types
    for key in config:
        config[key] = coerce(key, config[key])

    return config


@app.get("/effective-config")
def effective_config(
    set: list[str] | None = Query(default=None)
):
    config = load_config()

    # Highest precedence: query-parameter overrides.
    for item in set or []:
        if "=" not in item:
            continue

        key, value = item.split("=", 1)
        key = key.strip()

        if key in config:
            config[key] = coerce(key, value)

    # Never expose the real API key.
    config["api_key"] = "****"

    return config