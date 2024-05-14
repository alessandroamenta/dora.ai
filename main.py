import logging
from fastapi import FastAPI, HTTPException, BackgroundTasks, Header
from pydantic import BaseModel
from pydub import AudioSegment
from pydub.generators import Sine
from openai import OpenAI
import anthropic
from elevenlabs.client import ElevenLabs
from elevenlabs import Voice, VoiceSettings, play
import os
import tempfile
import uuid
from fastapi.responses import StreamingResponse
import io
from dotenv import load_dotenv

app = FastAPI()
load_dotenv()

anthropic.api_key = os.getenv("ANTHROPIC_API_KEY")
elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MeditationRequest(BaseModel):
    aiProvider: str
    duration: str
    guidanceLevel: str
    ttsProvider: str
    voice: str
    meditationFocus: str

audio_data = None
audio_generation_failed = False

@app.post("/generate")
async def generate_meditation(request: MeditationRequest, background_tasks: BackgroundTasks, x_secret_token: str = Header(None)):
    if x_secret_token != os.getenv("SECRET_TOKEN"):
        raise HTTPException(status_code=401, detail="Invalid secret token")
    else:
        logging.info("Secret token is correct")
    global audio_generation_failed
    audio_generation_failed = False
    logging.info("Received request to generate meditation")
    logging.info(f"Request parameters: {request}")
    ai_provider = request.aiProvider
    duration = request.duration
    guidance_level = request.guidanceLevel
    tts_provider = request.ttsProvider
    voice = request.voice
    meditation_focus = request.meditationFocus

    duration_options = {"2-5min": 4, "5-10min": 7, "10+min": 10}
    heuristics = {
        "4low": [1000, 2, 90],
        "4medium": [2000, 2, 60],
        "4high": [2000, 4, 30],
        "7low": [2000, 2, 165],
        "7medium": [3500, 4, 60],
        "7high": [4000, 6, 40],
        "10low": [2500, 3, 180],
        "10medium": [4000, 5, 85],
        "10high": [7000, 7, 50],
    }

    average_duration = duration_options[duration]
    heuristic_key = f"{average_duration}{guidance_level}"
    char_count, pause_count, pause_length = heuristics[heuristic_key]
    section_count = pause_count + 1
    pause_length_ms = pause_length * 1000

    prompt = f"""
    Your task is to create a script for a {average_duration} minutes guided meditation session focusing on {meditation_focus}.
    The meditation should have {section_count} sections and {pause_count} pauses total. Please follow these specific guidelines:
    1. VERY IMPORTANT: The output should ONLY contain the meditation script, without any additional commentary whatsoever, meditation script only!!!!!!
    2. Use ellipses (...) and commas strategically throughout the script to create natural pauses and a slower pace, with a particular emphasis on the beginning and end of the meditation. It is crucial to add a significant number of ellipses and commas, especially when starting the meditation script, to establish a slower and more relaxed pace. Additionally, when providing instructions related to breathing or other focus-specific techniques, use at least twice as many ellipses to allow ample time for the listener to follow along. For example:
        'Take a deep breath in..............................................and slowly exhale.......................................'
        'As you settle into a comfortable position.............................., allow your body to relax............................., letting go of any tension or stress............................................'
        'Without trying to change it......................, simply observe......................... how your chest or belly rises........................ and falls.......................... with each breath.............................. Feel the air entering through your nostrils......................., cool and refreshing........................, and then warming as it exits.................................... Let's fully immerse in this sensation of breathing for a moment........................................................'
        Intelligently determine the appropriate number of ellipses to add based on the specific scenario and instructions being given, ensuring a consistently slow and relaxed pace throughout the entire meditation script, with extra emphasis on the beginning, end, and focus-specific instructions.
    3. The script should be {char_count} characters long to align with the {average_duration} minutes duration of the session.
    4. Include a total of {pause_count} '---PAUSE---' markers at carefully considered transition points to create periods of silent reflection or focused breathing exercises.
        These pauses are crucial for the meditation's structure and flow. There should be a total of {pause_count} '---PAUSE---' markers. One for each pause.
    5. Before each '---PAUSE---' marker, gently guide the listener into the pause using phrases that encourage a smooth transition.
        For example:
        - 'Let's now gently turn our attention to our breath, allowing ourselves to fully experience the rhythm of each inhale and exhale.'
        - 'At this moment, let's simply be with our breath, feeling the calmness with each breath cycle.'
        - 'Now, let's take a moment to extend this feeling of warmth and compassion to ourselves and others...'
        - 'As we rest in this space of loving-kindness, allow yourself to be enveloped by a sense of peace and connection...'
        These guiding phrases should serve as soft introductions to the '---PAUSE---' markers, ensuring participants are thoughtfully led into each pause without abruptness, while maintaining relevance to the chosen focus.
    6. Use simple, clear, and approachable language throughout the script to make the meditation accessible, engaging and relaxing for everyone.
    7. The script should provide '{guidance_level}' level guidance, adjust the depth of instructions to guide the listener accordingly.
    8. The final section will gently conclude the session, guiding towards reawakening and reconnection with the surroundings. This closing section should include instructions for slowly opening the eyes, feeling the body, and becoming aware of the sounds and sensations in the environment, signaling the end of the meditation, while tying back to the main theme of the selected focus.
    Remember, the script's strict adherence to the {char_count} character count, it should be {section_count} sections total, and the strategic placement of {pause_count} '---PAUSE---' markers with gentle introductory phrases are essential for creating an impactful and seamless meditation experience. The use of ellipses and commas, especially at the beginning, will further enhance the slow and calming nature of the meditation.
    """
    try:
        logging.info("Generating meditation script")
        meditation_script = ""

        if ai_provider == "openai":
            client = OpenAI(api_key=os.getenv('OPENAI_API_KEY')) 
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert meditation guide."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=char_count,
                temperature=0.5,
            )
            meditation_script = response.choices[0].message.content
        elif ai_provider == "anthropic":
            anthropic_client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY')) 
            response = anthropic_client.messages.create(
                model="claude-3-haiku-20240307",
                system="You are an expert meditation guide.",
                max_tokens=4000,
                temperature=0.3,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )
            meditation_script = response.content[0].text
        else:
            raise HTTPException(status_code=400, detail="Invalid AI provider")

        logging.info("Meditation script generated successfully")
        logging.info(f"Generated meditation script:\n{meditation_script}")

        background_tasks.add_task(generate_audio, meditation_script, tts_provider, voice, pause_length_ms)

        return {"message": "Meditation generation in progress"}

    except Exception as e:
        logging.error(f"Error generating meditation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def generate_audio(meditation_script: str, tts_provider: str, voice: str, pause_length_ms: int):
    global audio_data, audio_generation_failed, audio_duration
    try:
        logging.info("Generating audio segments")
        segments = meditation_script.split("---PAUSE---")
        audio_files = []

        for i, segment in enumerate(segments):
            temp_audio_file_path = f"temp_audio_{i}.mp3"
            logging.info(f"Generating audio for segment {i+1}/{len(segments)}")

            if tts_provider == "openai":
                client = OpenAI(api_key=os.getenv('OPENAI_API_KEY')) 
                response = client.audio.speech.create(
                    model="tts-1",
                    input=segment,
                    response_format="mp3",
                    voice=voice,
                )
                response.stream_to_file(temp_audio_file_path)
            elif tts_provider == "elevenlabs":
                client = ElevenLabs(api_key=elevenlabs_api_key)
                voice_obj = Voice(voice_id=voice)
                audio_generator = client.generate(
                    text=segment,
                    voice=voice_obj,
                    model="eleven_monolingual_v1",
                    output_format="mp3_44100_128"
                )
                audio_data = b"".join(audio_generator)
                with open(temp_audio_file_path, "wb") as f:
                    f.write(audio_data)
            else:
                raise HTTPException(status_code=400, detail="Invalid TTS provider")

            audio_files.append(temp_audio_file_path)
            logging.info(f"Audio segment {i+1}/{len(segments)} generated successfully")

        logging.info("All audio segments generated successfully")

        logging.info("Generating silent segments")
        silent_segment = AudioSegment.silent(duration=pause_length_ms)
        silent_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        silent_segment.export(silent_file.name, format="mp3")

        logging.info("Combining audio segments")
        combined_audio = AudioSegment.empty()
        for i, audio_file in enumerate(audio_files):
            segment_audio = AudioSegment.from_mp3(audio_file)
            combined_audio += segment_audio
            if i < len(audio_files) - 1:
                combined_audio += AudioSegment.from_mp3(silent_file.name)
            logging.info(f"Audio segment {i+1}/{len(audio_files)} combined")

        output_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        combined_audio.export(output_file.name, format="mp3")
        logging.info("Combined audio exported successfully")

        with open(output_file.name, "rb") as file:
            audio_data = file.read()
        
        # Calculate the duration of the audio in seconds
        audio_duration_seconds = combined_audio.duration_seconds

        # Convert seconds to minutes and seconds format (M:SS or MM:SS)
        minutes, seconds = divmod(int(audio_duration_seconds), 60)
        if minutes < 10:
            audio_duration = f"{minutes}:{seconds:02d}"
        else:
            audio_duration = f"{minutes:02d}:{seconds:02d}"

        for audio_file in audio_files:
            os.unlink(audio_file)
        os.unlink(silent_file.name)
        os.unlink(output_file.name)

        logging.info("Audio generation completed successfully")
        return audio_duration

    except Exception as e:
        logging.error(f"Error generating audio: {str(e)}")
        audio_generation_failed = True
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/audio")
async def get_audio():
    global audio_duration
    if audio_generation_failed:
        logging.warning("Audio generation failed")
        return {"message": "Audio generation failed"}
    elif audio_data:
        logging.info("Returning generated audio")
        return StreamingResponse(io.BytesIO(audio_data), media_type="audio/mpeg", headers={"X-Audio-Duration": str(audio_duration)})
    else:
        logging.info("Audio not ready yet")
        return {"message": "Audio not ready yet"}