"""Section-aware markdown chunking for retrieval."""

from dataclasses import dataclass
from hashlib import sha256
import re

SECTION_PATTERN = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


@dataclass(frozen=True, slots=True)
class DocumentChunk:
    """Represent one retrievable markdown fragment and its source metadata."""

    doc_name: str
    section: str
    text: str
    chunk_id: str


def chunk_markdown(doc_name: str, markdown: str, max_chars: int = 1_200) -> list[DocumentChunk]:
    """Split markdown on level-two headings and return bounded chunks with stable IDs.

    Args:
        doc_name: Source document name used for citations.
        markdown: Complete markdown source.
        max_chars: Maximum character count for an individual chunk.

    Returns:
        Chunks retaining their document and section provenance.

    Raises:
        ValueError: If max_chars is not positive.
    """
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")

    matches = list(SECTION_PATTERN.finditer(markdown))
    sections: list[tuple[str, str]] = []
    if not matches:
        sections.append(("Document", markdown))
    else:
        preamble = markdown[: matches[0].start()].strip()
        if preamble:
            sections.append(("Overview", preamble))
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
            sections.append((match.group(1).strip(), markdown[match.end() : end].strip()))

    chunks: list[DocumentChunk] = []
    for section, content in sections:
        for part_index, text in enumerate(_split_text(content, max_chars)):
            identity = f"{doc_name}:{section}:{part_index}:{text}"
            chunks.append(
                DocumentChunk(
                    doc_name=doc_name,
                    section=section,
                    text=text,
                    chunk_id=sha256(identity.encode("utf-8")).hexdigest(),
                )
            )
    return chunks


def _split_text(text: str, max_chars: int) -> list[str]:
    """Split long section text at paragraph or word boundaries without empty chunks."""
    paragraphs = [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            words = paragraph.split()
            part = ""
            for word in words:
                candidate = f"{part} {word}".strip()
                if part and len(candidate) > max_chars:
                    chunks.append(part)
                    part = word
                else:
                    part = candidate
            if part:
                chunks.append(part)
            continue
        candidate = f"{current}\n\n{paragraph}".strip()
        if current and len(candidate) > max_chars:
            chunks.append(current)
            current = paragraph
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks
