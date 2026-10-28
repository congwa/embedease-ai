"""安全解析进程与结构分块；偏移始终基于保存的规范化全文。"""

import asyncio
import io
import json
import re
import sys
import uuid
import zipfile
from pathlib import PurePath

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings
from app.services.knowledge.rag.settings import RagError

MIMES = {
    ".txt": {"text/plain"},
    ".md": {"text/markdown", "text/plain"},
    ".pdf": {"application/pdf"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
}


def validate_upload(filename: str, mime: str, data: bytes) -> tuple[str, str]:
    """限制文件格式及魔数；文件名只保留展示用末段。"""
    filename = PurePath(filename.replace("\\", "/")).name[:300]
    ext = PurePath(filename).suffix.lower()
    if ext not in MIMES:
        raise RagError("仅支持 TXT、Markdown、文本 PDF 和 DOCX")
    mime = mime.split(";", 1)[0].lower()
    if mime not in MIMES[ext] | {"application/octet-stream", ""}:
        raise RagError("文件扩展名与内容类型不匹配")
    if not data:
        raise RagError("文件不能为空")
    if len(data) > settings.KNOWLEDGE_MAX_FILE_BYTES:
        raise RagError("文件超过大小限制", 413)
    if ext == ".pdf" and not data.startswith(b"%PDF-"):
        raise RagError("不是有效 PDF 文件")
    if ext == ".docx" and not data.startswith(b"PK"):
        raise RagError("不是有效 DOCX 文件")
    return filename, sorted(MIMES[ext])[0]


def normalized(text: str) -> str:
    """统一换行并去除 NUL，不改写文字顺序。"""
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")


def markdown_units(text: str) -> list[dict]:
    """按 ATX 标题分章，代码围栏内的井号不视为标题。"""
    units, lines, headings = [], [], []
    fence = None
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            marker = stripped[:3]
            fence = None if fence == marker else (marker if fence is None else fence)
        match = re.match(r"^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$", line) if fence is None else None
        if match:
            if lines:
                units.append({"text": "".join(lines), "heading_path": headings.copy()})
            lines = []
            level = len(match[1])
            headings = headings[: level - 1] + [match[2]]
        lines.append(line)
    if lines:
        units.append({"text": "".join(lines), "heading_path": headings.copy()})
    return units


def parse_sync(data: bytes, ext: str, max_chars: int, max_unpacked: int) -> list[dict]:
    """子进程内解析，不允许宏执行、OCR 或外部网络加载。"""
    if ext in {".txt", ".md"}:
        text = normalized(data.decode("utf-8-sig"))
        units = markdown_units(text) if ext == ".md" else [{"text": text}]
    elif ext == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise ValueError("不支持加密 PDF")
        units, count = [], 0
        for i, page in enumerate(reader.pages, 1):
            text = normalized(page.extract_text() or "")
            count += len(text)
            if count > max_chars:
                raise ValueError("解析全文超过字符限制")
            units.append({"text": text, "page": i})
    elif ext == ".docx":
        from docx import Document
        from docx.table import Table

        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            if sum(i.file_size for i in archive.infolist()) > max_unpacked:
                raise ValueError("DOCX 解压内容超过限制")
            if "word/document.xml" not in archive.namelist():
                raise ValueError("不是有效 DOCX 文档")
        document = Document(io.BytesIO(data))
        units, lines, headings = [], [], []
        for element in document.iter_inner_content():
            if isinstance(element, Table):
                lines.append(
                    "\n".join("\t".join(c.text for c in row.cells) for row in element.rows)
                )
            else:
                style = element.style.name if element.style else ""
                match = re.match(r"Heading (\d+)$", style)
                if match:
                    if lines:
                        units.append({"text": "\n".join(lines), "heading_path": headings.copy()})
                    lines = []
                    headings = headings[: int(match[1]) - 1] + [element.text]
                lines.append(element.text)
        if lines:
            units.append({"text": "\n".join(lines), "heading_path": headings.copy()})
        for unit in units:
            unit["text"] = normalized(unit["text"])
    else:
        raise ValueError("不支持的文档格式")
    if sum(len(u["text"]) + 2 for u in units) > max_chars:
        raise ValueError("解析全文超过字符限制")
    if not any(u["text"].strip() for u in units):
        raise ValueError("没有可提取文字；扫描件需要 OCR，当前版本不支持")
    return units


async def parse_document(data: bytes, filename: str) -> list[dict]:
    """有界时间的独立进程，超时或取消时终止并回收，避免孤儿解析器。"""
    ext = PurePath(filename).suffix.lower()
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "app.services.knowledge.rag.parsing",
        ext,
        str(settings.KNOWLEDGE_MAX_TEXT_CHARS),
        str(settings.KNOWLEDGE_DOCX_MAX_UNPACKED_BYTES),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    try:
        output, _ = await asyncio.wait_for(
            process.communicate(data), settings.KNOWLEDGE_PARSE_TIMEOUT
        )
        result = json.loads(output)
        if "error" in result:
            raise RagError(result["error"])
        if process.returncode != 0:
            raise RagError("文档解析进程失败")
        return result["units"]
    except TimeoutError as exc:
        raise RagError("文档解析超时") from exc
    except (json.JSONDecodeError, KeyError) as exc:
        raise RagError("文档解析失败") from exc
    finally:
        if process.returncode is None:
            process.kill()
        await process.wait()


def make_chunks(
    units: list[dict], revision_id: str, size: int, overlap: int
) -> tuple[str, list[dict]]:
    """结构单元内递归切分，验证每块是全文精确切片。"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=size,
        chunk_overlap=overlap,
        length_function=len,
        separators=["\n\n", "\n", "。", "；", "，", " ", ""],
        add_start_index=True,
        strip_whitespace=False,
    )
    full_parts, chunks, offset = [], [], 0
    for unit in units:
        text = unit["text"]
        if not text.strip():
            continue
        if full_parts:
            full_parts.append("\n\n")
            offset += 2
        full_parts.append(text)
        for part in splitter.create_documents([text]):
            local = part.metadata["start_index"]
            if local < 0 or text[local : local + len(part.page_content)] != part.page_content:
                raise RagError("分块偏移校验失败")
            index = len(chunks)
            chunks.append(
                {
                    "id": str(uuid.uuid5(uuid.UUID(revision_id), str(index))),
                    "revision_id": revision_id,
                    "chunk_index": index,
                    "content": part.page_content,
                    "start_offset": offset + local,
                    "end_offset": offset + local + len(part.page_content),
                    "page": unit.get("page"),
                    "heading_path": unit.get("heading_path", []),
                }
            )
            if len(chunks) > settings.KNOWLEDGE_MAX_CHUNKS:
                raise RagError("文档分块数超过限制")
        offset += len(text)
    full_text = "".join(full_parts)
    if len(full_text) > settings.KNOWLEDGE_MAX_TEXT_CHARS or not chunks:
        raise RagError("文档为空或全文超过限制")
    return full_text, chunks


def main() -> None:
    """解析子进程入口，只向父进程返回结构化结果。"""
    try:
        result = {
            "units": parse_sync(
                sys.stdin.buffer.read(), sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
            )
        }
    except Exception as exc:
        result = {"error": f"无法解析文档：{type(exc).__name__}: {str(exc)[:200]}"}
    sys.stdout.write(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
