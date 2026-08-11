"""UTF-8 safe writer for payloads subject to the 8000-character tool gate."""

from pathlib import Path

DEFAULT_CHUNK_BYTES = 6000
MAX_CHUNKS = 128
MAX_TOTAL_BYTES = 256 * 1024


def split_utf8_chunks(content: str, max_bytes: int = DEFAULT_CHUNK_BYTES) -> list[str]:
    if max_bytes <= 0:
        raise ValueError("max_bytes must be positive")
    chunks: list[str] = []
    current: list[str] = []
    current_bytes = 0
    for char in content:
        char_bytes = len(char.encode("utf-8"))
        if char_bytes > max_bytes:
            raise ValueError("max_bytes is smaller than one UTF-8 character")
        if current and current_bytes + char_bytes > max_bytes:
            chunks.append("".join(current))
            current = []
            current_bytes = 0
        current.append(char)
        current_bytes += char_bytes
    if current or not chunks:
        chunks.append("".join(current))
    if len(chunks) > MAX_CHUNKS:
        raise ValueError("content exceeds maximum chunk count")
    if len(content.encode("utf-8")) > MAX_TOTAL_BYTES:
        raise ValueError("content exceeds maximum total size")
    return chunks


def write_chunked(path: str | Path, content: str, max_bytes: int = DEFAULT_CHUNK_BYTES) -> None:
    path = Path(path)
    chunks = split_utf8_chunks(content, max_bytes)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".chunked.tmp")
    try:
        with temp_path.open("wb") as handle:
            for chunk in chunks:
                handle.write(chunk.encode("utf-8"))
        temp_path.replace(path)
    finally:
        temp_path.unlink(missing_ok=True)
