# EyeTracker - Visual Field Test System

A lightweight, robust eye-tracking system used as part of the pre-assessment preparation for patients undergoing the Humphrey Visual Field Test.

## 🚀 Quick Start

### Hardware Requirements
- Eye tracking hardware (see hardware setup guide)
- Arduino-compatible device
- Webcam or integrated camera

### Software Installation
1. Download the latest release from [Releases](https://github.com/dionyichia/EyeTracker/releases)
2. Extract the downloaded file
3. Run `EyeTracker.exe` (Windows) or `EyeTracker.app` (macOS)

### Hardware Setup
1. Connect your Arduino device
2. Upload the provided Arduino sketch (`arduino/eyetracker_arduino.ino`)
3. Follow the [Installation Guide](docs/installation.md) for detailed instructions

## 📋 System Requirements

### Windows
- Windows 10 or later
- 4GB RAM minimum, 8GB recommended
- USB ports for hardware connections

### macOS
- macOS 10.14 or later
- 4GB RAM minimum, 8GB recommended
- USB ports for hardware connections

### Linux
- Ubuntu 18.04+ or equivalent
- 4GB RAM minimum, 8GB recommended
- USB ports for hardware connections

## 🔧 For Developers

### Building from Source
```bash
# Clone the repository
git clone https://github.com/dionyichia/EyeTracker.git
cd EyeTracker

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Optional: configure Google Sheets result export
# Copy .env.example to .env and fill in the Google Sheets values

# Run the application
python main.py

# Build executable
python scripts/build.py
```

### Project Structure
```
EyeTracker/
├── core/           # Core tracking algorithms
├── gui/            # User interface components
├── arduino/        # Arduino code and integration
├── assets/         # Application assets
├── utils/          # Utility functions
└── main.py         # Application entry point
```

## 📖 Documentation
- [Installation Guide](docs/installation.md)
- [User Guide](docs/user_guide.md)
- [How it works](docs/how_it_works.md)
- [Developer's Manual](docs/dev_manual.md)

## 🐛 Troubleshooting
Check Dev Manual.

### Common Issues
1. **Camera not detected**: Ensure camera permissions are granted
2. **Arduino connection failed**: Check USB connection and driver installation
3. **Application won't start**: Run as administrator or check antivirus settings

## 📞 Support
- Create an issue on [GitHub Issues](https://github.com/yourusername/EyeTracker/issues)
- Check our [FAQ](docs/faq.md)

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments
- OpenCV community
- PyQt6 developers
- Arduino community
