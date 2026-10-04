import logging
import time
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

MAX_AUDIO_BYTES = 10 * 1024 * 1024
MAX_BATCH_AUDIO_BYTES = 100 * 1024 * 1024
SUPPORTED_AUDIO_TYPES = {
    "audio/webm", "video/webm", "audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp3",
    "audio/mp4", "audio/x-m4a", "audio/aac", "audio/ogg", "audio/opus", "audio/flac",
    "audio/x-flac", "audio/amr", "audio/x-ms-wma",
}


def transcribe_audio(data: bytes, filename: str, content_type: str, language_code: str = "auto") -> dict:
    if not settings.sarvam_api_key:
        raise ValueError("Sarvam voice transcription is not configured")
    if not data:
        raise ValueError("The audio recording is empty")
    if len(data) > MAX_AUDIO_BYTES:
        raise ValueError("Audio recording exceeds the 10 MB limit")
    normalized_content_type = content_type.split(";", 1)[0].strip().lower()
    if normalized_content_type not in SUPPORTED_AUDIO_TYPES:
        raise ValueError("Unsupported audio format")
    form = {"model": settings.sarvam_speech_model, "mode": "transcribe", "language_code": "unknown" if language_code == "auto" else language_code}
    try:
        response = httpx.post(
            f"{settings.sarvam_base_url.rstrip('/')}/speech-to-text",
            headers={"api-subscription-key": settings.sarvam_api_key}, data=form,
            files={"file": (filename or "recording.webm", data, normalized_content_type)}, timeout=settings.sarvam_timeout_seconds,
        )
        response.raise_for_status()
        result = response.json(); transcript = result.get("transcript", "").strip()
        if not transcript: raise ValueError("No speech was detected in the recording")
        return {"transcript": transcript, "language_code": result.get("language_code"), "language_probability": result.get("language_probability")}
    except httpx.TimeoutException as exc:
        raise ValueError("Voice transcription timed out. Please try again") from exc
    except httpx.HTTPStatusError as exc:
        try:
            payload = exc.response.json(); error = payload.get("error", payload.get("detail", payload))
            detail = error.get("message", error.get("detail", "")) if isinstance(error, dict) else str(error)
        except ValueError:
            detail = exc.response.text
        detail = detail.strip()[:500]
        logger.warning("Sarvam speech-to-text failed (%s): %s", exc.response.status_code, detail)
        if exc.response.status_code in (401, 403):
            raise ValueError("Sarvam rejected the API key or speech-model access") from exc
        if exc.response.status_code == 429:
            raise ValueError("Sarvam voice-transcription quota or rate limit was reached") from exc
        if exc.response.status_code == 422:
            raise ValueError("The recording format or duration was rejected by Sarvam. Please record a shorter clip") from exc
        raise ValueError(detail or "Sarvam could not transcribe this recording") from exc
    except httpx.RequestError as exc:
        raise ValueError("Voice transcription service is unavailable") from exc


def transcribe_audio_batch(data: bytes, filename: str, content_type: str) -> dict:
    if not settings.sarvam_api_key: raise ValueError("Sarvam voice transcription is not configured")
    if not data: raise ValueError("The audio recording is empty")
    if len(data)>MAX_BATCH_AUDIO_BYTES: raise ValueError("Audio recording exceeds the 100 MB limit")
    normalized=content_type.split(";",1)[0].strip().lower()
    if normalized not in SUPPORTED_AUDIO_TYPES: raise ValueError("Unsupported audio format")
    safe_name=(filename or "recording.mp3").replace("/","_").replace("\\","_")
    headers={"api-subscription-key":settings.sarvam_api_key}
    base=settings.sarvam_base_url.rstrip("/")+"/speech-to-text/job/v1"
    try:
        with httpx.Client(timeout=60) as client:
            created=client.post(base,headers=headers,json={"job_parameters":{"model":settings.sarvam_speech_model,"mode":"transcribe","language_code":"unknown"}});created.raise_for_status();job_id=created.json()["job_id"]
            links=client.post(f"{base}/upload-files",headers=headers,json={"job_id":job_id,"files":[safe_name]});links.raise_for_status();upload_url=links.json()["upload_urls"][safe_name]["file_url"]
            upload_headers={"Content-Type":normalized}
            if "blob.core.windows.net" in upload_url: upload_headers["x-ms-blob-type"]="BlockBlob"
            uploaded=client.put(upload_url,content=data,headers=upload_headers);uploaded.raise_for_status()
            started=client.post(f"{base}/{job_id}/start",headers=headers);started.raise_for_status()
            deadline=time.monotonic()+600;status={}
            while time.monotonic()<deadline:
                time.sleep(5);response=client.get(f"{base}/{job_id}/status",headers=headers);response.raise_for_status();status=response.json()
                if status.get("job_state") in ("Completed","PartiallyCompleted","Failed"):break
            else: raise ValueError("Batch transcription timed out after 10 minutes")
            if status.get("job_state")=="Failed" or not status.get("successful_files_count"): raise ValueError(status.get("error_message") or "Sarvam could not process this recording")
            output=status["job_details"][0]["outputs"][0]["file_name"]
            downloads=client.post(f"{base}/download-files",headers=headers,json={"job_id":job_id,"files":[output]});downloads.raise_for_status();download_url=downloads.json()["download_urls"][output]["file_url"]
            result=client.get(download_url);result.raise_for_status();payload=result.json();transcript=payload.get("transcript","").strip()
            if not transcript: raise ValueError("No speech was detected in the recording")
            return {"transcript":transcript,"language_code":payload.get("language_code") or "auto","language_probability":payload.get("language_probability")}
    except httpx.HTTPStatusError as exc:
        logger.warning("Sarvam batch speech-to-text failed (%s): %s",exc.response.status_code,exc.response.text[:500])
        raise ValueError("Sarvam batch transcription failed. Please verify the recording and try again") from exc
    except (httpx.RequestError,KeyError) as exc:
        raise ValueError("Sarvam batch transcription service is unavailable") from exc
