"""合同解析 API 路由"""
import asyncio
import json
from fastapi import APIRouter, File, UploadFile, Query, HTTPException
from fastapi.responses import StreamingResponse
from src.contract_parser.services import parse_contract, parse_contract_stream

parse_router = APIRouter(prefix="/api/contracts", tags=["Contract Parser"])

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


@parse_router.post("/parse")
async def parse_contract_file(
    file: UploadFile = File(...),
    contract_type: str = Query(..., description="compute_leasing / satellite_data / compute_service / project"),
):
    """上传合同文件，AI 自动提取关键字段

    所有格式统一走 Vision 多模态图片识别：
    - .doc / .docx → document-converter 服务转 PDF → 逐页拆图 → Vision LLM
    - .pdf → 逐页拆图 → Vision LLM
    """
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="文件大小超过 10MB 限制")

    filename = file.filename or "unknown"

    # 在独立线程中执行，避免阻塞健康检查
    loop = asyncio.get_event_loop()
    try:
        fields = await loop.run_in_executor(None, parse_contract, content, filename, contract_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return {
        "fields": fields,
        "processing_info": fields.pop("_processing_info", {}),
        "timing": fields.pop("_timing", {}),
        "page_results": fields.pop("_page_results", []),
    }


@parse_router.post("/parse/stream")
async def parse_contract_stream_endpoint(
    file: UploadFile = File(...),
    contract_type: str = Query(..., description="compute_leasing / satellite_data / compute_service / project"),
):
    """SSE 流式解析合同：每完成一页推送一次事件（含图片 base64），前端实时展示"""
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="文件大小超过 10MB 限制")

    filename = file.filename or "unknown"

    async def event_generator():
        gen = parse_contract_stream(content, filename, contract_type)
        try:
            async for item in gen:
                event_type = item.get("event", "message")
                event_data = item.get("data", "")
                yield f"event: {event_type}\ndata: {event_data}\n\n"
        except ValueError as e:
            yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"
        except RuntimeError as e:
            yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲
        }
    )
