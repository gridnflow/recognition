"""macOS `say` 기반 음성 안내. 논블로킹, 추가 의존성 없음."""

import shutil
import subprocess


def _pick_voice() -> list[str]:
    """한국어 음성(Yuna)이 있으면 사용, 없으면 시스템 기본 음성."""
    if shutil.which("say") is None:
        return []
    try:
        out = subprocess.run(
            ["say", "-v", "?"], capture_output=True, text=True, timeout=5
        ).stdout
    except Exception:
        return ["say"]
    if "Yuna" in out:
        return ["say", "-v", "Yuna"]
    return ["say"]


class Speaker:
    def __init__(self):
        self._cmd = _pick_voice()
        self._proc: subprocess.Popen | None = None

    def say(self, text: str, rate: int | None = None, interrupt: bool = True):
        if not self._cmd:
            return
        if interrupt:
            self.stop()
        cmd = list(self._cmd)
        if rate:
            cmd += ["-r", str(rate)]
        cmd.append(text)
        try:
            self._proc = subprocess.Popen(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except OSError:
            self._cmd = []  # say가 죽으면 이후 조용히 무시

    def stop(self):
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
        self._proc = None
