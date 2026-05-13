"""
Configuration utilities for the EyeTracker application
"""
import json
import logging
import os
import sys
from copy import deepcopy
from pathlib import Path
from typing import Dict, Optional, Tuple

# Default configuration
DEFAULT_CONFIG = {
    # Video settings
    "video": {
        "input_method": 2,  # 1 for video file, 2 for webcam
        "video_path": "./assets/eye_test.mp4",
        "zoom_factor": 1,
        "zoom_center": None,  # None means use the center of the frame
    },

    # Eye tracking settings
    "eye_tracking": {
        "lockpos_threshold": 48,
        "threshold_switch_confidence_margin": 2,
    },

    # Arduino settings
    "arduino": {
        "enabled": False,
        "port": "/dev/cu.usbserial-120",  # Default port, only for platform dev, will be removed
        "baud_rate": 115200,
        "port_identifiers": ['arduino', 'usb', 'serial', 'uno', 'r4', 'wifi']  # NOTE: no longer used, we're looking at VID to ident arduinos instead of description
    },

    # Test settings
    "test": {
        "num_points": 16,  # Number of points to flash during the test
        "point_duration": 0.5,  # Duration each point is visible in seconds
        "minimum_interval": 0.2,  # Minimum interval between points in seconds
        "maximum_interval": 1.0,  # Maximum interval between points in seconds
    },

    # UI settings
    "ui": {
        "theme": "default",
        "fullscreen": False,
        "window_size": [800, 600],
    },

    # Google Sheets settings
    "google_sheets": {
        "enabled": False,
        "credentials_path": "",
        "spreadsheet_id": "",
        "worksheet_name": "Results",
    },
}

GOOGLE_SHEETS_ENV_MAP = {
    "enabled": ("EYETRACKER_GOOGLE_SHEETS_ENABLED", "GOOGLE_SHEETS_ENABLED"),
    "credentials_path": (
        "EYETRACKER_GOOGLE_SHEETS_CREDENTIALS_PATH",
        "GOOGLE_SHEETS_CREDENTIALS_PATH",
    ),
    "spreadsheet_id": (
        "EYETRACKER_GOOGLE_SHEETS_SPREADSHEET_ID",
        "GOOGLE_SHEETS_SPREADSHEET_ID",
    ),
    "worksheet_name": (
        "EYETRACKER_GOOGLE_SHEETS_WORKSHEET_NAME",
        "GOOGLE_SHEETS_WORKSHEET_NAME",
    ),
}


def get_app_root():
    """Get the root directory of the application source tree."""
    return Path(__file__).resolve().parents[2]


def _iter_dotenv_candidates():
    seen = set()
    candidates = []

    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).resolve().parent / ".env")

    candidates.append(get_app_root() / ".env")

    for path in candidates:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        yield resolved


def get_dotenv_path() -> Optional[Path]:
    """Return the first supported .env file path if it exists."""
    for path in _iter_dotenv_candidates():
        if path.exists():
            return path
    return None


def _parse_dotenv_file(path: Path) -> Dict[str, str]:
    """Parse a basic .env file without requiring an external dependency."""
    env_values = {}

    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if not key:
            continue

        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]

        env_values[key] = value

    return env_values


def _parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"Invalid boolean value: {value}")


def _resolve_path(value: str, base_dir: Path) -> str:
    expanded = os.path.expandvars(os.path.expanduser(value.strip()))
    if not expanded:
        return ""

    candidate = Path(expanded)
    if candidate.is_absolute():
        return str(candidate)

    return str((base_dir / candidate).resolve())


def _merge_config_sections(config, overrides):
    for section, values in overrides.items():
        if section in config and isinstance(config[section], dict) and isinstance(values, dict):
            config[section].update(values)
        else:
            config[section] = values


def _get_env_override(
    env_names: Tuple[str, ...],
    dotenv_values: Dict[str, str],
    dotenv_base_dir: Path,
):
    for env_name in env_names:
        if env_name in os.environ:
            return os.environ[env_name], Path.cwd()
        if env_name in dotenv_values:
            return dotenv_values[env_name], dotenv_base_dir
    return None, None


def _apply_google_sheets_env_overrides(config):
    dotenv_path = get_dotenv_path()
    dotenv_values = _parse_dotenv_file(dotenv_path) if dotenv_path else {}
    dotenv_base_dir = dotenv_path.parent if dotenv_path else get_app_root()

    google_sheets = config.setdefault("google_sheets", {})

    for field, env_names in GOOGLE_SHEETS_ENV_MAP.items():
        raw_value, base_dir = _get_env_override(env_names, dotenv_values, dotenv_base_dir)
        if raw_value is None:
            continue

        try:
            if field == "enabled":
                google_sheets[field] = _parse_bool(raw_value)
            elif field == "credentials_path":
                google_sheets[field] = _resolve_path(raw_value, base_dir)
            else:
                google_sheets[field] = raw_value.strip()
        except ValueError as exc:
            logging.warning("Skipping invalid value for %s: %s", env_names[0], exc)


def get_config_dir():
    """Get the directory for config files"""
    # Platform-specific configuration directory
    if os.name == 'nt':  # Windows
        config_dir = os.path.join(os.environ['APPDATA'], 'EyeTracker')
    else:  # macOS, Linux
        config_dir = os.path.join(os.path.expanduser('~'), '.config', 'eyetracker')

    # Create directory if it doesn't exist
    os.makedirs(config_dir, exist_ok=True)

    return config_dir


def get_config_path():
    """Get the path to the config file"""
    return os.path.join(get_config_dir(), 'config.json')


def load_config(include_env=True):
    """Load configuration from file

    Returns:
        dict: Configuration dictionary
    """
    config_path = get_config_path()
    config = deepcopy(DEFAULT_CONFIG)

    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                user_config = json.load(f)

            # Update default config with user config
            _merge_config_sections(config, user_config)
        else:
            # Save default config if no config file exists
            save_config(config)
    except Exception as e:
        logging.error(f"Error loading config: {e}")
        # Fall back to default config

    if include_env:
        _apply_google_sheets_env_overrides(config)

    return config


def save_config(config):
    """Save configuration to file

    Args:
        config (dict): Configuration to save
    """
    config_path = get_config_path()

    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        logging.error(f"Error saving config: {e}")


def get_default_video_path():
    """Get the default video path for testing

    Returns:
        str: Path to the default test video
    """
    # Check for the test video in the application directory
    app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    video_path = os.path.join(app_dir, 'eye_test.mp4')

    if os.path.exists(video_path):
        return video_path

    return None


def get_platform_specific_settings():
    """Get platform-specific settings

    Returns:
        dict: Platform-specific settings
    """
    settings = {}

    if os.name == 'nt':  # Windows
        settings['default_arduino_port'] = 'COM3'
    elif os.name == 'posix':  # macOS and Linux
        if 'darwin' in os.uname().sysname.lower():  # macOS
            settings['default_arduino_port'] = '/dev/cu.usbserial-120'
        else:  # Linux
            settings['default_arduino_port'] = '/dev/ttyACM0'

    return settings


def update_config_section(section, values):
    """Update a specific section of the configuration

    Args:
        section (str): Section name
        values (dict): Values to update
    """
    config = load_config(include_env=False)

    if section not in config:
        config[section] = {}

    config[section].update(values)
    save_config(config)
