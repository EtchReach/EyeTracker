"""Backend audio playback helpers."""
import sys
from pathlib import Path

from PyQt6.QtCore import QCoreApplication, QUrl
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer


_SOUND_FILES = {
    "correct": "correct.mp3",
    "wrong": "wrong.mp3",
    "look_straight": "look_straight.mp3",
}

_SHARED_AUDIO_PLAYER = None


def resolve_asset_path(filename):
    """Resolve an asset path for source and packaged app runs."""
    base_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return base_dir / "assets" / filename


class BackendAudioPlayer:
    """Shared Qt audio players for backend-triggered sounds."""

    def __init__(self):
        self._players = {}
        self._initialized = False

    def _ensure_initialized(self):
        """Create Qt media objects only after a Qt app exists."""
        if self._initialized:
            return

        if QCoreApplication.instance() is None:
            return

        for sound_name, filename in _SOUND_FILES.items():
            asset_path = resolve_asset_path(filename)
            if not asset_path.exists():
                print(f"Audio asset not found: {asset_path}")
                continue

            audio_output = QAudioOutput()
            audio_output.setVolume(1.0)

            player = QMediaPlayer()
            player.setAudioOutput(audio_output)
            player.setSource(QUrl.fromLocalFile(str(asset_path)))

            self._players[sound_name] = (player, audio_output)

        self._initialized = True

    def play(self, sound_name):
        """Play a named sound if it is available."""
        self._ensure_initialized()

        if not self._initialized and QCoreApplication.instance() is None:
            return

        player_bundle = self._players.get(sound_name)
        if player_bundle is None:
            print(f"Unknown or unavailable sound: {sound_name}")
            return

        player, _ = player_bundle
        player.stop()
        player.setPosition(0)
        player.play()


def get_shared_audio_player():
    """Return the shared backend audio player instance."""
    global _SHARED_AUDIO_PLAYER

    if _SHARED_AUDIO_PLAYER is None:
        _SHARED_AUDIO_PLAYER = BackendAudioPlayer()

    return _SHARED_AUDIO_PLAYER
