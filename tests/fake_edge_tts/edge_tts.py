"""Fake edge_tts untuk testing (tanpa network).

Menyediakan edge_tts.Communicate yang save()-nya selalu menulis mp3
12 detik via ffmpeg — dipakai untuk menguji loop penyesuaian rate di
lib/tts.py. Dipakai via PYTHONPATH, BUKAN sebagai dependensi asli.
"""
import subprocess


class Communicate:
    def __init__(self, text, voice="en-US", rate="+0%", volume="+0%",
                 pitch="+0Hz", connector=None, proxy=None,
                 connect_timeout=10, receive_timeout=60):
        self.rate = rate

    async def save(self, path):
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
             "-i", "sine=frequency=440:duration=12",
             "-c:a", "libmp3lame", str(path)],
            check=True, timeout=60)
