import logging
from openai import OpenAI
from pydub import AudioSegment
import os
from dotenv import load_dotenv
from elevenlabs import generate, play, Voice, VoiceSettings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize final_audio as a silent segment of zero duration
final_audio = AudioSegment.silent(duration=0)

# Load environment variables from .env file
load_dotenv()

#ElevenLabs setup
ELEVEN_API_KEY = os.getenv('ELEVENLABS_API_KEY')

# OpenAI API Setup
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY')) 

# Logging the start of script generation
logging.info("Starting meditation script generation...")

# Define the prompt for meditation text generation, aiming for a specific length
prompt = (
    "Create a script for a 5-minute cohesive meditation session, with a strict focus on mindfulness and breath control. The script must meticulously adhere to approximately 4000 characters, aligning precisely with the session's duration. "
    "Crucially, it is imperative to include '---PAUSE---' markers at carefully considered transition points, ensuring a seamless flow into periods of silent reflection or focused breathing exercises. "
    "Prior to each '---PAUSE---' marker, the script should naturally and gently guide the listener toward the pause, facilitating a smooth transition without any abruptness. For instance, use phrases such as 'Let's now gently turn our attention to our breath, allowing ourselves to fully experience the rhythm of each inhale and exhale,' or 'At this moment, let's simply be with our breath, feeling the calmness with each breath cycle.' "
    "These guiding phrases are essential, serving as soft introductions to the '---PAUSE---' markers and are vital for the meditation's integrity, ensuring participants are thoughtfully led into each pause. "
    "The script’s length, closely adhering to the 4000 character guideline, and the strategic, gentle introduction of '---PAUSE---' markers are both crucial. They work together to create a meditation experience that is both impactful and seamlessly executed from start to finish, providing natural intervals for reflection or breathing without sudden interruptions. "
    "Please ensure the language used throughout the script is simple, clear, and approachable, making the meditation accessible and engaging for everyone."
)


# Generate the meditation script
response = client.chat.completions.create(
    model="gpt-4-turbo-preview",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": prompt},
    ],
    temperature=0.7,
)

# Extract the generated script
meditation_script = response.choices[0].message.content

# Logging the generated meditation script
logging.info("Meditation script generated successfully.")

# Split the script into segments at each pause marker
segments = meditation_script.split('---PAUSE---')

# Logging the start of audio processing
logging.info("Starting audio processing for segments...")

# Define a one-minute pause
one_minute_silence = AudioSegment.silent(duration=60000)  # 60,000 milliseconds

# Generate and combine segments with pauses
for i, segment in enumerate(segments):
    # Logging the processing of each segment with TTS
    logging.info(f"Processing segment {i+1} with TTS...")

    # Generate the audio using ElevenLabs' text-to-speech
    audio_response = generate(
        api_key=ELEVEN_API_KEY,
        text=segment,
        voice=Voice(
            voice_id='RrkF2QZOPA1PyW4EamJj',
            settings=VoiceSettings(speaking_rate=0.8, stability=0.71, similarity_boost=0.5, style=0.0, use_speaker_boost=True)
        ),
        model="eleven_monolingual_v1",
        output_format="mp3_44100_128"  # Specify MP3 as the output format
    )

    # Save the audio data to a file, using MP3 format directly
    temp_audio_file = f"segment_{i}.mp3"
    with open(temp_audio_file, "wb") as f:
        f.write(audio_response)

    # Load the segment audio and append to the final audio
    segment_audio = AudioSegment.from_file(temp_audio_file, format="mp3")
    final_audio += segment_audio

    # Add pause after each segment except the last one
    if i < len(segments) - 1:
        final_audio += one_minute_silence

    # Clean up the temporary file
    os.remove(temp_audio_file)

# Logging the completion of audio processing
logging.info("Audio processing completed successfully.")

# Export the final audio file
final_audio.export("meditation_sesh_audio.mp3", format="mp3")

# Logging the successful creation of the final audio file
logging.info("Meditation audio with pauses created and exported successfully.")