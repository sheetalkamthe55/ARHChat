import logging
import os
from pathlib import Path
from typing import Any

from api.settings.readyaml import load_yaml_with_envvars
from api.constant import PROJECT_ROOT_PATH

logger = logging.getLogger(__name__)

_folder_settings = os.environ.get("SETTINGS_FOLDER", PROJECT_ROOT_PATH)
logger.info(_folder_settings)

def load_settings_from_profile() -> dict[str, Any]:
    profile_file_name = "settings.yaml"

    path = Path(_folder_settings) / profile_file_name
    with Path(path).open("r") as f:
        config = load_yaml_with_envvars(f)
    if not isinstance(config, dict):
        raise TypeError(f"Config file has no top-level mapping: {path}")
    return config

