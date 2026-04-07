from __future__ import annotations

from pathlib import Path


INPUT_PATH = Path("docs/architecture/runtime_architecture_guide.md")
OUTPUT_PATH = Path("docs/architecture/runtime_architecture_guide.pdf")


def _escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _wrap_text(text: str, max_chars: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]

    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
            continue
        lines.append(current)
        current = word

    if current:
        lines.append(current)
    return lines


def _parse_markdown_lines(text: str) -> list[tuple[str, int]]:
    lines: list[tuple[str, int]] = []
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            lines.append(("", 11))
            continue
        if stripped.startswith("# "):
            lines.append((stripped[2:], 18))
            continue
        if stripped.startswith("## "):
            lines.append((stripped[3:], 15))
            continue
        if stripped.startswith("### "):
            lines.append((stripped[4:], 13))
            continue
        if stripped.startswith("- "):
            lines.append((f"- {stripped[2:]}", 11))
            continue
        lines.append((stripped, 11))
    return lines


def _paginate(lines: list[tuple[str, int]], max_chars: int = 95) -> list[list[tuple[str, int]]]:
    pages: list[list[tuple[str, int]]] = []
    current_page: list[tuple[str, int]] = []
    y = 760

    for text, size in lines:
        wrapped = [("", size)] if text == "" else [(part, size) for part in _wrap_text(text, max_chars)]
        for part, part_size in wrapped:
            line_height = int(part_size * 1.6)
            if y - line_height < 50:
                pages.append(current_page)
                current_page = []
                y = 760
            current_page.append((part, part_size))
            y -= line_height

    if current_page:
        pages.append(current_page)

    return pages


def _build_content_stream(page_lines: list[tuple[str, int]]) -> bytes:
    commands = ["BT", "/F1 16 Tf", "50 790 Td"]
    first = True
    for text, size in page_lines:
        if first:
            commands.append(f"/F1 {size} Tf")
            commands.append(f"({_escape_pdf_text(text)}) Tj")
            first = False
            continue
        commands.append(f"0 -{int(size * 1.6)} Td")
        commands.append(f"/F1 {size} Tf")
        commands.append(f"({_escape_pdf_text(text)}) Tj")
    commands.append("ET")
    return "\n".join(commands).encode("latin-1", errors="replace")


def build_pdf(markdown_text: str) -> bytes:
    pages = _paginate(_parse_markdown_lines(markdown_text))

    objects: list[bytes] = []

    def add_object(payload: bytes) -> int:
        objects.append(payload)
        return len(objects)

    font_obj = add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    content_ids: list[int] = []
    page_ids: list[int] = []

    for page_lines in pages:
        stream = _build_content_stream(page_lines)
        content_obj = add_object(
            f"<< /Length {len(stream)} >>\nstream\n".encode("latin-1") + stream + b"\nendstream"
        )
        content_ids.append(content_obj)

    pages_obj_placeholder = add_object(b"")

    for content_obj in content_ids:
        page_obj = add_object(
            (
                f"<< /Type /Page /Parent {pages_obj_placeholder} 0 R /MediaBox [0 0 612 842] "
                f"/Resources << /Font << /F1 {font_obj} 0 R >> >> /Contents {content_obj} 0 R >>"
            ).encode("latin-1")
        )
        page_ids.append(page_obj)

    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects[pages_obj_placeholder - 1] = (
        f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode("latin-1")
    )
    catalog_obj = add_object(f"<< /Type /Catalog /Pages {pages_obj_placeholder} 0 R >>".encode("latin-1"))

    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("latin-1"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref_start = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))

    pdf.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_obj} 0 R >>\n"
            f"startxref\n{xref_start}\n%%EOF\n"
        ).encode("latin-1")
    )
    return bytes(pdf)


def main() -> None:
    markdown_text = INPUT_PATH.read_text(encoding="utf-8")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_bytes(build_pdf(markdown_text))
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()
