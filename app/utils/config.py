"""
Configuration utilities for the EyeTracker application
"""
import os
import json
import logging

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
    }
}

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


def load_config():
    """Load configuration from file
    
    Returns:
        dict: Configuration dictionary
    """
    config_path = get_config_path()
    config = DEFAULT_CONFIG.copy()
    
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                
            # Update default config with user config
            for section, values in user_config.items():
                if section in config:
                    config[section].update(values)
                else:
                    config[section] = values
        else:
            # Save default config if no config file exists
            save_config(config)
    except Exception as e:
        logging.error(f"Error loading config: {e}")
        # Fall back to default config
    
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
    config = load_config()
    
    if section not in config:
        config[section] = {}
    
    config[section].update(values)
    save_config(config)