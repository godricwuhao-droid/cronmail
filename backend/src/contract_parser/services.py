"""合同解析服务"""
import io
import json
import re
import logging
import time
import base64
import asyncio
import requests as http_requests
from openai import OpenAI
from src.core.config import settings
from src.contract_parser.prompts import SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger(__name__)

# document-converter 服务地址（K8s 内部 DNS）
CONVERTER_URL = "http://document-converter.cronmail.svc.cluster.local:8080"


def convert_to_pdf(file_bytes: bytes, filename: str) -> bytes:
    """通过 document-converter 服务将文件转为 PDF"""
    resp = http_requests.post(
        f"{CONVERTER_URL}/convert",
        files={'file': (filename, io.BytesIO(file_bytes))},
        timeout=120,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"文档转换失败: HTTP {resp.status_code}")
    return resp.content


def extract_text_from_docx(file_bytes: bytes) -> str:
    """从 Word 文件提取纯文本（含表格）"""
    from docx import Document
    doc = Document(io.BytesIO(file_bytes))
    parts = []
    
    # 1. 段落文本
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            parts.append(text)
    
    # 2. 表格数据（服务清单等关键信息在这里）
    for ti, table in enumerate(doc.tables):
        parts.append(f"\n[表格{ti+1}]")
        for ri, row in enumerate(table.rows):
            cells = [cell.text.strip().replace('\n', ' ') for cell in row.cells]
            parts.append(" | ".join(cells))
    
    return "\n".join(parts)


def extract_images_from_pdf(file_bytes: bytes, max_pages: int = 50) -> list[str]:
    """将 PDF 逐页转为 base64 图片列表（JPEG 压缩 + 并行）"""
    from pdf2image import convert_from_bytes
    from concurrent.futures import ThreadPoolExecutor
    
    images = convert_from_bytes(file_bytes, dpi=100, fmt='jpeg', thread_count=4)
    if len(images) > max_pages:
        images = images[:max_pages]
    
    def _encode(img) -> str:
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=85, optimize=True)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode('utf-8')
    
    with ThreadPoolExecutor(max_workers=4) as pool:
        result = list(pool.map(_encode, images))
    
    return result


def extract_text_from_doc(file_bytes: bytes) -> str:
    """从旧版 .doc 文件提取纯文本（通过 antiword）"""
    import tempfile
    import subprocess
    with tempfile.NamedTemporaryFile(suffix='.doc', delete=True) as tmp:
        tmp.write(file_bytes)
        tmp.flush()
        try:
            result = subprocess.run(
                ['antiword', tmp.name],
                capture_output=True, text=True, timeout=30,
            )
            text = result.stdout.strip()
            if not text:
                raise ValueError("antiword 无法提取文本，请将文件另存为 .docx 或 .pdf 格式")
            return text
        except FileNotFoundError:
            raise ValueError("antiword 未安装，请联系管理员")

def parse_contract(file_bytes: bytes, filename: str, contract_type: str) -> dict:
    """解析合同文件 — 所有格式统一走 Vision 多模态图片识别

    Raises:
        ValueError: 文件格式不支持
        RuntimeError: 文档转换或 LLM 调用失败
    """
    processing_info = {"file_size_kb": round(len(file_bytes) / 1024, 1)}

    ext = filename.lower().rsplit('.', 1)[-1] if '.' in filename else ''

    # .doc/.docx → converter → PDF → 统一走 Vision
    if ext in ('doc', 'docx'):
        processing_info["mode"] = "vision"
        processing_info["file_type"] = ext
        try:
            pdf_bytes = convert_to_pdf(file_bytes, filename)
        except Exception as e:
            raise RuntimeError(f"文档转换失败: {e}")
        processing_info["converted_from"] = ext
        return parse_contract_vision(pdf_bytes, filename.rsplit('.', 1)[0] + '.pdf', contract_type, processing_info)

    # .pdf → 直接走 Vision
    elif ext == 'pdf':
        processing_info["mode"] = "vision"
        processing_info["file_type"] = "pdf"
        return parse_contract_vision(file_bytes, filename, contract_type, processing_info)

    else:
        raise ValueError(f"不支持的文件格式: .{ext}，支持 .doc / .docx / .pdf")


def parse_contract_vision(file_bytes: bytes, filename: str, contract_type: str, processing_info: dict = None) -> dict:
    """累进式 Vision 管道：逐页分析，每页带上下文"""
    t0 = time.time()
    timing = {}  # 耗时记录
    if processing_info is None:
        processing_info = {"mode": "vision", "file_size_kb": round(len(file_bytes) / 1024, 1), "file_type": "pdf"}

    # 1. PDF 转图片
    t1 = time.time()
    b64_images = extract_images_from_pdf(file_bytes)
    if not b64_images:
        raise ValueError("PDF 无有效页面")
    timing["pdf_to_images"] = {"seconds": round(time.time() - t1, 1), "pages": len(b64_images)}
    processing_info["pdf_pages"] = len(b64_images)
    processing_info["extract_seconds"] = timing["pdf_to_images"]["seconds"]

    # 2. 累进式逐页分析
    from src.contract_parser.prompts import VISION_SYSTEM_PROMPT, get_vision_page_prompt, get_vision_final_prompt

    client = OpenAI(
        base_url=settings.LLM_BASE_URL,
        api_key=settings.LLM_API_KEY,
        timeout=180,
    )

    accumulated = {}  # 累积结果
    page_results = []  # 每页分析记录
    total_pages = len(b64_images)

    for i, b64 in enumerate(b64_images):
        t_page = time.time()
        page_num = i + 1

        # 构建累进式 prompt
        if i == 0:
            page_prompt = get_vision_page_prompt(contract_type, page_num, total_pages, None)
        else:
            prev_summary = json.dumps(accumulated, ensure_ascii=False, indent=2)
            page_prompt = get_vision_page_prompt(contract_type, page_num, total_pages, prev_summary)

        content = [
            {"type": "text", "text": page_prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
        ]

        try:
            response = client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": VISION_SYSTEM_PROMPT},
                    {"role": "user", "content": content},
                ],
                temperature=0.1,
                max_tokens=4096,
                extra_body={"chat_template_kwargs": {"enable_thinking": False}},
            )
            raw = response.choices[0].message.content
        except Exception as e:
            logger.error(f"Vision LLM 第{page_num}页失败: {e}")
            page_results.append({"page": page_num, "error": str(e), "seconds": round(time.time() - t_page, 1)})
            continue

        # 解析本页结果
        page_data = _parse_llm_json(raw)

        # 合并到累积结果
        _deep_merge(accumulated, page_data)

        elapsed = round(time.time() - t_page, 1)
        page_results.append({
            "page": page_num,
            "seconds": elapsed,
            "found_fields": [k for k, v in page_data.items() if v is not None and v != [] and v != {}],
        })

    timing["per_page"] = page_results

    # 3. 最终汇总（如果超过 3 页）
    if total_pages > 3:
        t_final = time.time()
        final_prompt = get_vision_final_prompt(contract_type, json.dumps(accumulated, ensure_ascii=False, indent=2))
        try:
            response = client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": "你是合同信息提取助手，请汇总分析结果。"},
                    {"role": "user", "content": final_prompt},
                ],
                temperature=0.1,
                max_tokens=8192,
                extra_body={"chat_template_kwargs": {"enable_thinking": False}},
            )
            raw = response.choices[0].message.content
            final_data = _parse_llm_json(raw)
            _deep_merge(accumulated, final_data)
        except Exception:
            pass  # 汇总失败不影响结果
        timing["final_summary"] = {"seconds": round(time.time() - t_final, 1)}

    timing["total_vision"] = {"seconds": round(time.time() - t0, 1)}
    accumulated["_processing_info"] = processing_info
    accumulated["_timing"] = timing
    accumulated["_page_results"] = page_results
    return accumulated


def _parse_llm_json(raw: str) -> dict:
    """安全解析 LLM 返回的 JSON"""
    if not raw or not raw.strip():
        return {}
    try:
        cleaned = re.sub(r'^```(?:json)?\s*', '', raw.strip())
        cleaned = re.sub(r'\s*```$', '', cleaned)
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {}


def _deep_merge(base: dict, update: dict):
    """深度合并，update 中的非 null 值覆盖 base"""
    for k, v in update.items():
        if v is None or v == [] or v == {}:
            continue
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_merge(base[k], v)
        elif isinstance(v, list) and isinstance(base.get(k), list):
            base[k].extend(v)
        else:
            base[k] = v


async def parse_contract_stream(file_bytes: bytes, filename: str, contract_type: str):
    """SSE 流式解析：每完成一页 yield 一个事件"""
    t0 = time.time()
    processing_info = {"mode": "vision", "file_size_kb": round(len(file_bytes) / 1024, 1), "file_type": "pdf"}

    ext = filename.lower().rsplit('.', 1)[-1] if '.' in filename else ''

    if ext in ('doc', 'docx'):
        processing_info["file_type"] = ext
        loop = asyncio.get_running_loop()
        pdf_bytes = await loop.run_in_executor(None, convert_to_pdf, file_bytes, filename)
        processing_info["converted_from"] = ext
    else:
        pdf_bytes = file_bytes

    # 1. PDF 转图片
    t1 = time.time()
    loop = asyncio.get_running_loop()
    b64_images = await loop.run_in_executor(None, extract_images_from_pdf, pdf_bytes)
    yield {"event": "progress", "data": json.dumps({
        "step": "pdf_to_images", "pages": len(b64_images), "seconds": round(time.time() - t1, 1)
    }, ensure_ascii=False)}

    # 2. 逐页分析
    from src.contract_parser.prompts import VISION_SYSTEM_PROMPT, get_vision_page_prompt, get_vision_final_prompt

    client = OpenAI(
        base_url=settings.LLM_BASE_URL,
        api_key=settings.LLM_API_KEY,
        timeout=180,
    )

    accumulated = {}
    total_pages = len(b64_images)

    for i, b64 in enumerate(b64_images):
        t_page = time.time()
        page_num = i + 1

        if i == 0:
            page_prompt = get_vision_page_prompt(contract_type, page_num, total_pages, None)
        else:
            page_prompt = get_vision_page_prompt(contract_type, page_num, total_pages, json.dumps(accumulated, ensure_ascii=False, indent=2))

        content = [
            {"type": "text", "text": page_prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
        ]

        try:
            response = await loop.run_in_executor(
                None,
                lambda content=content, sp=VISION_SYSTEM_PROMPT, m=settings.LLM_MODEL: client.chat.completions.create(
                    model=m,
                    messages=[{"role": "system", "content": sp}, {"role": "user", "content": content}],
                    temperature=0.1, max_tokens=4096,
                    extra_body={"chat_template_kwargs": {"enable_thinking": False}},
                )
            )
            raw = response.choices[0].message.content
            page_data = _parse_llm_json(raw)
            _deep_merge(accumulated, page_data)

            found = [k for k, v in page_data.items() if v not in (None, [], {}, "", 0)]
        except Exception as e:
            found = []
            logger.error(f"第{page_num}页失败: {e}")

        elapsed = round(time.time() - t_page, 1)
        yield {"event": "page", "data": json.dumps({
            "page": page_num, "total": total_pages, "seconds": elapsed,
            "found_fields": found, "image_base64": b64,
        }, ensure_ascii=False)}

    # 3. 最终汇总
    if total_pages > 3:
        t_final = time.time()
        # 保存 raw_tables（不被汇总覆盖）
        saved_tables = accumulated.get("raw_tables", [])
        final_prompt = get_vision_final_prompt(contract_type, json.dumps(accumulated, ensure_ascii=False, indent=2))
        try:
            response = await loop.run_in_executor(
                None,
                lambda fp=final_prompt, m=settings.LLM_MODEL: client.chat.completions.create(
                    model=m,
                    messages=[{"role": "system", "content": "汇总合同信息，保留所有 raw_tables 和 resource_summary，不要丢失"}, {"role": "user", "content": fp}],
                    temperature=0.1, max_tokens=8192,
                    extra_body={"chat_template_kwargs": {"enable_thinking": False}},
                )
            )
            _deep_merge(accumulated, _parse_llm_json(response.choices[0].message.content))
        except Exception:
            pass
        # 恢复 raw_tables（汇总可能丢失）
        if saved_tables and (not accumulated.get("raw_tables") or len(accumulated.get("raw_tables", [])) < len(saved_tables)):
            accumulated["raw_tables"] = saved_tables
        yield {"event": "progress", "data": json.dumps({"step": "final_summary", "seconds": round(time.time() - t_final, 1)}, ensure_ascii=False)}

    # 4. raw_tables 去重（跨页表格可能被多页识别为多条，按 title 去重保留最长行数的）
    if accumulated.get("raw_tables"):
        deduped = {}
        for t in accumulated["raw_tables"]:
            key = (t.get("title", ""), tuple(t.get("headers", [])))
            if key not in deduped or len(t.get("rows", [])) > len(deduped[key].get("rows", [])):
                deduped[key] = t
        accumulated["raw_tables"] = list(deduped.values())
    
    accumulated["_processing_info"] = processing_info
    accumulated["_processing_info"]["elapsed_seconds"] = round(time.time() - t0, 1)
    if accumulated.get("raw_tables"):
        accumulated["raw_tables_json"] = json.dumps(accumulated["raw_tables"], ensure_ascii=False)
    yield {"event": "done", "data": json.dumps({"fields": accumulated}, ensure_ascii=False)}


def _fallback_parse(raw: str, contract_type: str) -> dict:
    """JSON 解析失败时的降级策略：返回原始文本"""
    return {
        "raw_response": raw,
        "parse_error": True,
        "message": "AI 返回格式异常，请手动填写或重试",
    }
