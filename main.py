import os
import logging
from fastapi import FastAPI, HTTPException
from pydub import AudioSegment
import uvicorn
from app import generate_meditation_audio
from dotenv import load_dotenv
from supabase import create_client, Client

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

# Initialize the Supabase client
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# Set the storage bucket name
STORAGE_BUCKET_NAME = "meditations"

app = FastAPI()

@app.get("/generate_meditation")
async def generate_meditation():
    try:
        logging.info("Generating meditation audio...")
        final_audio = generate_meditation_audio()

        file_name = "meditation_sesh_audio.mp3"
        final_audio.export(file_name, format="mp3")
        logging.info(f"Uploading {file_name} to Supabase storage...")

        with open(file_name, "rb") as f:
            file_content = f.read()

        file_path = f"meditations/{file_name}"
        response = supabase.storage.from_(STORAGE_BUCKET_NAME).upload(file_path, file_content, {"content-type": "audio/mpeg"})

        # Check the response for an error
        if response.get('error'):
            logging.error(f"Error during file upload: {response['error']}")
            raise Exception(response['error'])

        logging.info(f"Inserting {file_name} information into Supabase table...")
        table_response = supabase.table("meditations").insert({"file_name": file_name}).execute()

        if table_response.get('error'):
            raise Exception(table_response['error']['message'])

        os.remove(file_name)
        logging.info("Meditation audio generated and saved to Supabase.")
        return {"message": "Meditation audio generated and saved to Supabase."}

    except Exception as e:
        # Log the full error details
        logging.error(f"Exception occurred: {e}")
        # If the response object is available, log the full response
        if hasattr(e, 'response') and e.response:
            logging.error(f"Supabase response: {e.response.json()}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)