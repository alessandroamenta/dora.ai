import logging
from openai import OpenAI
from pydub import AudioSegment
import os
from dotenv import load_dotenv
from elevenlabs import generate, play, Voice, VoiceSettings
import anthropic

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize final_audio as a silent segment of zero duration
final_audio = AudioSegment.silent(duration=0)

# Load environment variables from .env file
load_dotenv()

#ElevenLabs setup
ELEVEN_API_KEY = os.getenv('ELEVENLABS_API_KEY')

# Ask the user which AI provider they want to use for meditation script generation
ai_provider = input("Choose your AI provider for script generation (type 'openai' or 'anthropic', default is 'openai'): ").lower() or "openai"

# Initialize clients
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
anthropic_client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY')) 

# Ask the user which TTS provider they want to use
tts_provider = input("Choose your TTS provider (type 'openai' or 'elevenlabs', default is 'openai'): ").lower() or "openai"

# Define a mapping of voice names to each TTS provider's voice IDs
openai_voice_options = {
    "Alloy": "alloy",
    "Echo": "echo",
    "Fable": "fable",
    "Onyx": "onyx",
    "Nova": "nova",
    "Shimmer": "shimmer"
}
elevenlabs_voice_options = {
    "Vincent": "Qe9WSybioZxssVEwlBSo",
    "Joanne": "RrkF2QZOPA1PyW4EamJj",
    "Stella": "h9wTb50iJC9oQuw5A37H",
    "Javier": "h415g7h7bSwQrn1qw4ar",
    "Gemma": "fqQpqTuOIBHOwbVaVZP3",
    "Tim": "XPzm47Wm41jCR5gentJy",
}

# Choose the correct voice options based on TTS provider
voice_options = openai_voice_options if tts_provider == "openai" else elevenlabs_voice_options

# Prompt the user to select a voice based on TTS provider
print(f"Please select a voice for the meditation from {tts_provider.title()}:")
for name in voice_options.keys():
    print(name)
selected_voice_name = input("Enter the voice name: ")

# Validate user input and get the corresponding voice ID or name
if selected_voice_name in voice_options:
    selected_voice = voice_options[selected_voice_name]
else:
    logging.error(f"Invalid voice name. Please select from the available options: {list(voice_options.keys())}")
    exit(1)  # Exit the script if the voice name is invalid

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

if ai_provider == "openai":
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY')) 
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

elif ai_provider == "anthropic":
    # Anthropic API Setup
    client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

    # Generate the meditation script with Anthropic
    response = client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=4000,  # You might need to adjust this for the script length
        temperature=0,
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

# Logging which AI provider was used and that the script was generated successfully
logging.info(f"Meditation script generated successfully using {ai_provider.upper()} and {selected_voice_name.upper()} voice.")

# Log the generated meditation script to the terminal
logging.info("Generated Meditation Script:\n" + meditation_script)

# Split the script into segments at each pause marker
segments = meditation_script.split('---PAUSE---')

# Logging the start of audio processing
logging.info("Starting audio processing for segments...")

# Define a one-minute pause
one_minute_silence = AudioSegment.silent(duration=60000)  # 60,000 milliseconds

# Generate and combine segments with pauses based on TTS provider
for i, segment in enumerate(segments):
    logging.info(f"Processing segment {i+1} with {tts_provider.title()} TTS...")

    if tts_provider == "openai":
        # Generate the audio using OpenAI's text-to-speech
        response = openai_client.audio.speech.create(
            model="tts-1",
            voice=selected_voice,
            input=segment,
            response_format="mp3",
            speed=0.9  # You can adjust this speed parameter as needed
        )
        # Define the path for temporary audio file
        temp_audio_file_path = f"./segment_{i}.mp3"
        # Stream the audio to a file
        response.stream_to_file(temp_audio_file_path)

    elif tts_provider == "elevenlabs":
        # Import ElevenLabs generate function only if needed
        from elevenlabs import generate
        # Generate the audio using ElevenLabs' text-to-speech
        audio_response = generate(
            api_key=os.getenv('ELEVENLABS_API_KEY'),
            text=segment,
            voice=Voice(
                voice_id=selected_voice,  # selected_voice here is the voice ID from elevenlabs
                settings=VoiceSettings(speaking_rate=0.8, stability=0.71, similarity_boost=0.5, style=0.0, use_speaker_boost=True)
            ),
            model="eleven_monolingual_v1",
            output_format="mp3_44100_128"
        )
        # Define the path for temporary audio file
        temp_audio_file_path = f"./segment_{i}.mp3"
        # Save the audio data to a file
        with open(temp_audio_file_path, "wb") as f:
            f.write(audio_response)

    # Load the segment audio and append to the final audio
    segment_audio = AudioSegment.from_file(temp_audio_file_path, format="mp3")
    final_audio += segment_audio

    # Add a pause after each segment except the last one
    if i < len(segments) - 1:
        final_audio += one_minute_silence

    # Clean up the temporary file
    os.remove(temp_audio_file_path)

# Logging the completion of audio processing
logging.info("Audio processing completed successfully.")

# Export the final audio file
final_audio.export("meditation_sesh_audio.mp3", format="mp3")

# Logging the successful creation of the final audio file
logging.info("Meditation audio with pauses created and exported successfully.")