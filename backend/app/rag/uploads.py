"""Validate a single uploaded filename consistently on Windows and POSIX."""

from pathlib import Path

RESERVED_NAMES = {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"} | {
    f"{prefix}{digit}" for prefix in ("COM", "LPT") for digit in "123456789¹²³"
}


def upload_destination(directory: Path, name: str) -> Path:
    if (
        not name
        or name in {".", ".."}
        or any(c in name for c in '/\\:<>"|?*\x00')
        or any(ord(c) < 32 for c in name)
        or name.endswith((".", " "))
        or name.split(".")[0].rstrip(" ").upper() in RESERVED_NAMES
        or Path(name).suffix.lower() not in {".pdf", ".md", ".txt"}
    ):
        raise ValueError("文件名或扩展名无效")
    target = (directory / name).resolve()
    if target.parent != directory.resolve():
        raise ValueError("文件路径超出上传目录")
    return target
