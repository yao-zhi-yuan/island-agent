from __future__ import annotations

import os
from typing import Annotated
from typing import Any

import httpx
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

router = APIRouter(prefix="/asr", tags=["asr"])


def _get_asr_base_url() -> str:
    value = (
        os.getenv("ASR_BASE_URL")
        or os.getenv("DASHSCOPE_COMPAT_BASE_URL")
        or "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    return value.rstrip("/")


def _get_asr_api_key() -> str | None:
    return (os.getenv("ASR_API_KEY") or os.getenv("DASHSCOPE_API_KEY") or "").strip() or None


def _get_asr_model() -> str:
    # qwen3-asr-flash works with DashScope OpenAI-compatible chat/completions.
    return os.getenv("ASR_MODEL", "qwen3-asr-flash").strip() or "qwen3-asr-flash"


def _to_data_url(audio_bytes: bytes, mime: str) -> str:
    import base64

    return f"data:{mime};base64,{base64.b64encode(audio_bytes).decode('ascii')}"


def _extract_text(payload: dict[str, Any]) -> str:
    direct = payload.get("text")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()

    output = payload.get("output")
    if isinstance(output, dict):
        output_text = output.get("text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()

    result = payload.get("result")
    if isinstance(result, dict):
        result_text = result.get("text")
        if isinstance(result_text, str) and result_text.strip():
            return result_text.strip()

    segments = payload.get("segments")
    if isinstance(segments, list):
        parts: list[str] = []
        for item in segments:
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                parts.append(text.strip())
        if parts:
            return " ".join(parts)
    return ""


def _extract_text_from_chat_completion(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, dict):
        return ""
    message = first.get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                parts.append(text.strip())
        if parts:
            return "\n".join(parts)
    return ""


async def _transcribe_via_openai_audio(
    *,
    client: httpx.AsyncClient,
    base_url: str,
    api_key: str,
    model: str,
    filename: str,
    data: bytes,
    content_type: str,
    language: str,
    prompt: str | None,
) -> tuple[str, dict[str, Any]]:
    url = f"{base_url}/audio/transcriptions"
    form_data: dict[str, Any] = {"model": model, "language": language}
    if prompt:
        form_data["prompt"] = prompt
    response = await client.post(
        url,
        headers={"Authorization": f"Bearer {api_key}"},
        data=form_data,
        files={"file": (filename, data, content_type)},
    )
    if not response.is_success:
        raise HTTPException(
            status_code=502,
            detail=f"ASR upstream failed: {response.status_code} {response.text[:500]}",
        )
    payload = response.json()
    text = _extract_text(payload)
    if not text:
        raise HTTPException(status_code=502, detail=f"ASR upstream JSON has no text field: {payload}")
    return text, payload


async def _transcribe_via_dashscope_chat(
    *,
    client: httpx.AsyncClient,
    base_url: str,
    api_key: str,
    model: str,
    data: bytes,
    content_type: str,
    language: str,
) -> tuple[str, dict[str, Any]]:
    url = f"{base_url}/chat/completions"
    data_url = _to_data_url(data, content_type)
    body = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [{"type": "input_audio", "input_audio": {"data": data_url}}],
            }
        ],
        "stream": False,
        "extra_body": {"asr_options": {"language": language, "enable_itn": True}},
    }
    response = await client.post(
        url,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=body,
    )
    if not response.is_success:
        raise HTTPException(
            status_code=502,
            detail=f"ASR upstream failed: {response.status_code} {response.text[:500]}",
        )
    payload = response.json()
    text = _extract_text_from_chat_completion(payload)
    if not text:
        raise HTTPException(status_code=502, detail=f"ASR upstream JSON has no text field: {payload}")
    return text, payload


class TranscribeResponse(BaseModel):
    text: str
    model: str
    mode: str


@router.post(
    "/transcribe",
    response_model=TranscribeResponse,
    summary="语音转文字",
    description="上传音频文件，后端调用上游 ASR 服务并返回识别文本。",
)
async def transcribe_audio(
    file: Annotated[UploadFile, File(description="音频文件，例如 webm、wav、mp3、m4a。")],
    language: Annotated[str, Form(description="识别语言，默认 zh。")] = "zh",
    prompt: Annotated[str | None, Form(description="可选提示词，用于辅助上游识别。")] = None,
) -> dict[str, Any]:
    api_key = _get_asr_api_key()
    if not api_key:
        raise HTTPException(status_code=500, detail="ASR API key is not configured.")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Audio file is empty.")

    model = _get_asr_model()
    asr_mode = (os.getenv("ASR_MODE", "auto").strip().lower() or "auto")
    timeout = float(os.getenv("ASR_TIMEOUT_SECONDS", "60"))
    base_url = _get_asr_base_url()

    filename = file.filename or "audio.webm"
    content_type = file.content_type or "application/octet-stream"
    async with httpx.AsyncClient(timeout=timeout) as client:
        if asr_mode == "dashscope_chat":
            text, _ = await _transcribe_via_dashscope_chat(
                client=client,
                base_url=base_url,
                api_key=api_key,
                model=model,
                data=data,
                content_type=content_type,
                language=language,
            )
            return {"text": text, "model": model, "mode": "dashscope_chat"}

        if asr_mode == "openai_audio":
            text, _ = await _transcribe_via_openai_audio(
                client=client,
                base_url=base_url,
                api_key=api_key,
                model=model,
                filename=filename,
                data=data,
                content_type=content_type,
                language=language,
                prompt=prompt,
            )
            return {"text": text, "model": model, "mode": "openai_audio"}

        # auto mode: first try OpenAI audio endpoint, fallback to DashScope chat endpoint on 404.
        try:
            text, _ = await _transcribe_via_openai_audio(
                client=client,
                base_url=base_url,
                api_key=api_key,
                model=model,
                filename=filename,
                data=data,
                content_type=content_type,
                language=language,
                prompt=prompt,
            )
            return {"text": text, "model": model, "mode": "openai_audio"}
        except HTTPException as exc:
            detail = str(exc.detail)
            if "404" not in detail:
                raise
            text, _ = await _transcribe_via_dashscope_chat(
                client=client,
                base_url=base_url,
                api_key=api_key,
                model=model,
                data=data,
                content_type=content_type,
                language=language,
            )
            return {"text": text, "model": model, "mode": "dashscope_chat"}
