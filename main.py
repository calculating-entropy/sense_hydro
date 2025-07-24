from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from datetime import datetime

import json
from pathlib import Path
from fastapi.responses import FileResponse

# Add this near the top with other constants
METADATA_FILE = 'file_metadata.json'

def load_metadata():
    """Load file metadata from JSON file"""
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_metadata(metadata):
    """Save file metadata to JSON file"""
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f, indent=2)



# Create upload directory
UPLOAD_DIR = 'uploaded_objs'
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI()

# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# Serve uploaded files as static files
app.mount("/files", StaticFiles(directory=UPLOAD_DIR), name="files")

@app.post("/upload")
async def upload_obj(file: UploadFile = File(...)):
    if not file.filename.endswith('.obj'):
        return JSONResponse({"error": "Only .obj files allowed"}, status_code=400)
    
    # Create unique filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"{timestamp}_{file.filename}"
    path = os.path.join(UPLOAD_DIR, filename)
    
    # Save file to disk
    with open(path, 'wb') as f:
        content = await file.read()
        f.write(content)
    
    # Store metadata
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
            
            # Add metadata if available
            if fname in metadata:
                file_info.update({
                    "upload_time": metadata[fname]["upload_time"],
                    "original_name": metadata[fname]["original_name"],
                    "file_size": metadata[fname]["file_size"]
                })
            else:
                # Fallback for files uploaded before metadata tracking
                file_info.update({
                    "upload_time": datetime.now().isoformat(),
                    "original_name": fname,
                    "file_size": 0
                })
            
            files.append(file_info)
    
    # Sort files by upload time (newest first)
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

@app.get("/")
async def root():
    return {"message": "OBJ Upload API is running"}

