import hashlib
import re
from io import BytesIO
import httpx
from pypdf import PdfReader
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models import KnowledgeChunk, KnowledgeDocument

MAX_PDF_BYTES=25*1024*1024
CHUNK_SIZE=1400
CHUNK_OVERLAP=220

def _clean(text:str)->str:
    text=text.replace("\x00","")
    return re.sub(r"[ \t]+"," ",re.sub(r"\n{3,}","\n\n",text)).strip()

def _chunks(text:str)->list[str]:
    if not text:return []
    result=[]; start=0
    while start<len(text):
        end=min(len(text),start+CHUNK_SIZE)
        if end<len(text):
            boundary=max(text.rfind("\n",start,end),text.rfind(". ",start,end))
            if boundary>start+CHUNK_SIZE//2:end=boundary+1
        result.append(text[start:end].strip())
        if end>=len(text):break
        start=max(start+1,end-CHUNK_OVERLAP)
    return [item for item in result if len(item)>=80]

def embed_texts(texts:list[str])->list[list[float]]:
    response=httpx.post(f"{settings.ollama_base_url.rstrip('/')}/api/embed",json={"model":settings.ollama_embedding_model,"input":texts},timeout=settings.ollama_embedding_timeout_seconds)
    response.raise_for_status(); vectors=response.json().get("embeddings",[])
    if len(vectors)!=len(texts) or any(len(vector)!=768 for vector in vectors):raise ValueError("Embedding provider returned an unexpected vector shape")
    return vectors

def ingest_pdf(db:Session,data:bytes,filename:str,title:str,audience:str,user_id:int)->KnowledgeDocument:
    if len(data)>MAX_PDF_BYTES:raise ValueError("PDF exceeds the 25 MB limit")
    if not data.startswith(b"%PDF-"):raise ValueError("The uploaded file is not a valid PDF")
    digest=hashlib.sha256(data).hexdigest()
    if db.query(KnowledgeDocument).filter_by(sha256=digest).first():raise ValueError("This PDF has already been uploaded")
    document=KnowledgeDocument(filename=filename,title=title.strip() or filename,sha256=digest,classification="Internal",audience=audience,status="Processing",original_file=data,uploaded_by=user_id)
    db.add(document);db.flush()
    try:
        reader=PdfReader(BytesIO(data)); pending=[]
        for page_number,page in enumerate(reader.pages,start=1):
            for index,content in enumerate(_chunks(_clean(page.extract_text() or ""))):pending.append((page_number,index,content))
        if not pending:raise ValueError("No extractable text was found. OCR is required for this PDF")
        for offset in range(0,len(pending),16):
            batch=pending[offset:offset+16]; vectors=embed_texts([item[2] for item in batch])
            for (page_number,index,content),vector in zip(batch,vectors):db.add(KnowledgeChunk(document_id=document.id,page_number=page_number,chunk_index=index,content=content,embedding=vector))
        document.page_count=len(reader.pages);document.chunk_count=len(pending);document.status="Approved" if audience=="customer" else "Internal"
        db.commit();db.refresh(document);return document
    except Exception as exc:
        db.rollback()
        failed=KnowledgeDocument(filename=filename,title=title.strip() or filename,sha256=digest,classification="Internal",audience=audience,status="Failed",page_count=0,chunk_count=0,original_file=data,uploaded_by=user_id,error_message=str(exc)[:1000])
        db.add(failed);db.commit()
        raise ValueError(f"PDF ingestion failed: {exc}") from exc

def retrieve_pdf_chunks(db:Session,query:str,audience:str="customer",limit:int=4):
    try:
        vector=embed_texts([query])[0]
        distance=KnowledgeChunk.embedding.cosine_distance(vector)
        rows=(db.query(KnowledgeChunk,KnowledgeDocument,distance.label("distance")).join(KnowledgeDocument,KnowledgeChunk.document_id==KnowledgeDocument.id).filter(KnowledgeDocument.status=="Approved",KnowledgeDocument.audience==audience).order_by(distance).limit(limit).all())
        return [{"id":chunk.id,"title":document.title,"category":"PDF Knowledge","content":chunk.content,"page":chunk.page_number,"document_id":document.id,"score":round(max(0,1-float(distance_value)),4)} for chunk,document,distance_value in rows if float(distance_value)<=0.55]
    except Exception:
        return []
