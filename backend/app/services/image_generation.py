from dataclasses import dataclass
import time
import httpx
from app.core.config import settings

@dataclass
class GeneratedImage:
    content:bytes
    filename:str="campaign.png"

def campaign_prompt(kind:str,segment:str,topic:str,context:str="")->str:
    purpose="customer retention and relationship reassurance" if kind=="retention" else f"a next-best opportunity for {topic}"
    safe_context=" ".join((context or "").split())[:400]
    return (
        f"Premium Indian banking email hero image illustrating {purpose}. "
        f"Customer segment: {segment}. Campaign context: {safe_context}. "
        "Warm, trustworthy, optimistic, realistic professional commercial photography, contemporary Indian setting, "
        "subtle blue and red accents, people positioned on the left, generous clean empty space on the right for email copy, "
        "no text, no letters, no numbers, no logo, no watermark, no bank documents, no personal information."
    )

def _workflow(prompt:str)->dict:
    return {
        "4":{"class_type":"CheckpointLoaderSimple","inputs":{"ckpt_name":settings.comfyui_checkpoint}},
        "5":{"class_type":"EmptySD3LatentImage","inputs":{"width":1024,"height":512,"batch_size":1}},
        "6":{"class_type":"CLIPTextEncode","inputs":{"text":prompt,"clip":["4",1]}},
        "7":{"class_type":"CLIPTextEncode","inputs":{"text":"","clip":["4",1]}},
        "3":{"class_type":"KSampler","inputs":{"seed":int(time.time_ns()%1_000_000_000_000),"steps":4,"cfg":1.0,"sampler_name":"euler","scheduler":"simple","denoise":1.0,"model":["4",0],"positive":["6",0],"negative":["7",0],"latent_image":["5",0]}},
        "8":{"class_type":"VAEDecode","inputs":{"samples":["3",0],"vae":["4",2]}},
        "9":{"class_type":"SaveImage","inputs":{"filename_prefix":"email_campaign","images":["8",0]}},
    }

def generate_campaign_image(prompt:str)->GeneratedImage:
    deadline=time.monotonic()+settings.comfyui_timeout_seconds
    try:
        with httpx.Client(base_url=settings.comfyui_base_url,timeout=30) as client:
            queued=client.post("/prompt",json={"prompt":_workflow(prompt),"client_id":"union-engage-email"})
            queued.raise_for_status();prompt_id=queued.json()["prompt_id"]
            while time.monotonic()<deadline:
                history=client.get(f"/history/{prompt_id}");history.raise_for_status()
                result=history.json().get(prompt_id)
                if result:
                    images=result.get("outputs",{}).get("9",{}).get("images",[])
                    if not images:raise RuntimeError("ComfyUI completed without producing an image")
                    item=images[0]
                    response=client.get("/view",params={"filename":item["filename"],"subfolder":item.get("subfolder",""),"type":item.get("type","output")})
                    response.raise_for_status()
                    return GeneratedImage(response.content,item["filename"])
                time.sleep(.5)
    except (httpx.HTTPError,KeyError,ValueError) as exc:
        raise RuntimeError(f"Local image generation failed: {exc}") from exc
    raise RuntimeError("Local image generation timed out")
