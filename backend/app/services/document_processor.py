from pathlib import Path

from PyPDF2 import PdfReader
from docx import Document
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import CHUNK_SIZE, CHUNK_OVERLAP

try:
    import pdfplumber
except ImportError:  # pragma: no cover - optional at runtime
    pdfplumber = None


def extract_text(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return _parse_pdf(file_path)
    elif suffix == ".docx":
        return _parse_docx(file_path)
    elif suffix == ".txt":
        return _parse_txt(file_path)
    else:
        raise ValueError(f"Unsupported file type: {suffix}")


# --- tables -----------------------------------------------------------------
#
# Forms and reports keep their facts in tables, and a bare grid of cells
# embeds badly: split a table across chunks and "John Anderson" arrives with
# no idea it was a Patient Name. Every row is therefore flattened to a
# self-describing line that carries its own labels:
#
#   two columns   ->  "Patient Name: John Anderson"
#   wider tables  ->  "Test: CBC | Result: 13.2 | Unit: g/dL"
#
# so a row still means something on its own, wherever the splitter cuts.


def _clean_cell(value) -> str:
    """Collapse a cell's whitespace so one cell is always one line."""
    return " ".join(str(value or "").split())


def _format_rows(rows: list[list[str]]) -> list[str]:
    """Turn raw table rows into labelled, self-contained lines."""
    rows = [[_clean_cell(c) for c in row] for row in rows]
    rows = [row for row in rows if any(row)]
    if not rows:
        return []

    width = max(len(row) for row in rows)

    # Key/value form (the common shape in requisitions, invoices, spec sheets)
    if width <= 2:
        lines = []
        for row in rows:
            cells = [c for c in row if c]
            if len(cells) >= 2:
                lines.append(f"{cells[0]}: {' '.join(cells[1:])}")
            elif cells:
                lines.append(cells[0])
        return lines

    # Grid form: repeat the header on every row so each line stands alone
    header = rows[0] + [""] * (width - len(rows[0]))
    body = rows[1:] or rows

    lines = [" | ".join(c for c in header if c)] if any(header) else []
    for row in body:
        row = row + [""] * (width - len(row))
        pairs = [
            f"{header[i]}: {row[i]}" if header[i] else row[i]
            for i in range(width)
            if row[i]
        ]
        if pairs:
            lines.append(" | ".join(pairs))
    return lines


# --- docx -------------------------------------------------------------------


def _iter_block_items(parent):
    """Yield a docx body's paragraphs and tables in document order.

    ``Document.paragraphs`` skips tables entirely, so a form whose content
    lives in a grid used to be indexed as little more than its title.
    """
    if isinstance(parent, _Cell):
        element = parent._tc
    else:
        element = parent.element.body

    for child in element.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)


def _docx_table_rows(table: Table) -> list[list[str]]:
    """Read a table's cells, inlining any table nested inside a cell."""
    rows = []
    for row in table.rows:
        cells = []
        for cell in row.cells:
            parts = [p.text for p in cell.paragraphs if p.text.strip()]
            for nested in cell.tables:
                parts.extend(_format_rows(_docx_table_rows(nested)))
            cells.append(" ".join(parts))
        rows.append(cells)
    return rows


def _parse_docx(file_path: Path) -> str:
    doc = Document(str(file_path))
    lines = []
    for block in _iter_block_items(doc):
        if isinstance(block, Paragraph):
            if block.text.strip():
                lines.append(block.text.strip())
        else:
            lines.extend(_format_rows(_docx_table_rows(block)))
    return "\n".join(lines)


# --- pdf --------------------------------------------------------------------


def _pdf_page_text(page) -> str:
    """A pdfplumber page as prose plus its tables, without duplicating either.

    Table cells also come back from ``extract_text``, so the table regions are
    filtered out of the prose first and re-added as labelled rows.
    """
    tables = page.find_tables()

    if tables:
        boxes = [t.bbox for t in tables]

        def outside_tables(obj):
            cx = (obj.get("x0", 0) + obj.get("x1", 0)) / 2
            cy = (obj.get("top", 0) + obj.get("bottom", 0)) / 2
            return not any(
                x0 <= cx <= x1 and top <= cy <= bottom
                for x0, top, x1, bottom in boxes
            )

        prose = page.filter(outside_tables).extract_text() or ""
    else:
        prose = page.extract_text() or ""

    parts = [prose.strip()] if prose.strip() else []
    for table in tables:
        lines = _format_rows(table.extract())
        if lines:
            parts.append("\n".join(lines))
    return "\n".join(parts)


def _parse_pdf(file_path: Path) -> str:
    if pdfplumber is not None:
        try:
            with pdfplumber.open(str(file_path)) as pdf:
                pages = []
                for page in pdf.pages:
                    try:
                        text = _pdf_page_text(page)
                    except Exception:
                        text = page.extract_text() or ""
                    if text.strip():
                        pages.append(text)
            if pages:
                return "\n".join(pages)
        except Exception:
            pass  # fall back to the plain reader below

    return _parse_pdf_basic(file_path)


def _parse_pdf_basic(file_path: Path) -> str:
    reader = PdfReader(str(file_path))
    text_parts = []
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text_parts.append(page_text)
    return "\n".join(text_parts)


def _parse_txt(file_path: Path) -> str:
    return file_path.read_text(encoding="utf-8")


def chunk_text(text: str) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
    )
    return splitter.split_text(text)
