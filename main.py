from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import json
from datetime import datetime
import shutil
from measure import tag_and_measure

METADATA_FILE = 'file_metadata.json'
UPLOAD_DIR = 'uploaded_objs'
os.makedirs(UPLOAD_DIR, exist_ok=True)

def load_metadata():
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_metadata(metadata):
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f, indent=2)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],  # Change to your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/files", StaticFiles(directory=UPLOAD_DIR), name="files")

@app.post("/upload")
async def upload_obj(file: UploadFile = File(...)):
    if not file.filename.endswith('.obj'):
        return JSONResponse({"error": "Only .obj files allowed"}, status_code=400)
    
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"{timestamp}_{file.filename}"
    path = os.path.join(UPLOAD_DIR, filename)
    
    content = await file.read()
    with open(path, 'wb') as f:
        f.write(content)
    
    metadata = load_metadata()
    upload_time = datetime.now().isoformat()
    metadata[filename] = {
        "original_name": file.filename,
        "upload_time": upload_time,
        "file_size": len(content)
    }
    save_metadata(metadata)
    
    return {
        "filename": filename,
        "url": f"/files/{filename}",
        "upload_time": upload_time,
        "original_name": file.filename
    }

@app.get("/files")
async def list_files():
    metadata = load_metadata()
    files = []
    
    for fname in os.listdir(UPLOAD_DIR):
        if fname.endswith('.obj'):
            file_info = {
                "filename": fname,
                "url": f"/files/{fname}",
                "download_url": f"/download/{fname}"
            }
            
            if fname in metadata:
                file_info.update({
                    "upload_time": metadata[fname]["upload_time"],
                    "original_name": metadata[fname]["original_name"],
                    "file_size": metadata[fname]["file_size"]
                })
            else:
                file_info.update({
                    "upload_time": datetime.now().isoformat(),
                    "original_name": fname,
                    "file_size": 0
                })
            
            files.append(file_info)
    
    files.sort(reverse=True, key=lambda x: x["upload_time"])
    return files

@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(file_path):
        metadata = load_metadata()
        original_name = metadata.get(filename, {}).get("original_name", filename)
        return FileResponse(
            path=file_path,
            filename=original_name,
            media_type='application/octet-stream'
        )
    return JSONResponse({"error": "File not found"}, status_code=404)

@app.get("/measure/{filename}")
async def measure_obj_file(filename: str):
    if ".." in filename or filename.startswith("/") or not filename.endswith(".obj"):
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    obj_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(obj_path):
        raise HTTPException(status_code=404, detail="OBJ file not found")
    
    base_name = os.path.splitext(filename)[0]
    ply_filename = f"{base_name}_colored_planes.ply"
    ply_path = os.path.join(UPLOAD_DIR, ply_filename)

    try:
        measurements = tag_and_measure(obj_path, ply_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Measurement processing failed: {str(e)}")
    
    ply_url = f"/files/{ply_filename}"
    return {
        "measurements": measurements,
        "ply_file_url": ply_url
    }

@app.get("/")
async def root():
    return {"message": "OBJ Upload API is running"}

