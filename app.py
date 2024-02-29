from openai import OpenAI
from pydub import AudioSegment
import os
from dotenv import load_dotenv

# Initialize final_audio as a silent segment of zero duration
final_audio = AudioSegment.silent(duration=0)

# Load environment variables from .env file
load_dotenv()

# OpenAI API Setup
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY')) 

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

# Print the entire generated meditation script
print("Generated Meditation Script:")
print(meditation_script)
print("\n")

# Split the script into segments at each pause marker
segments = meditation_script.split('---PAUSE---')

# Print each segment individually
for i, segment in enumerate(segments):
    print(f"Segment {i+1}:")
    print(segment.strip())
    print("\n")

# Define a one-minute pause
one_minute_silence = AudioSegment.silent(duration=60000)  # 60,000 milliseconds

# Generate and combine segments with pauses
for i, segment in enumerate(segments):
    # Generate the audio using OpenAI's text-to-speech
    response = client.audio.speech.create(
        model="tts-1",
        voice="onyx", 
        input=segment,
        speed=0.9,
    )

    # Save and load each segment
    temp_audio_file = f"segment_{i}.mp3"
    with open(temp_audio_file, "wb") as f:
        f.write(response.content) 

    segment_audio = AudioSegment.from_file(temp_audio_file)
    final_audio += segment_audio

    # Add pause after each segment except the last one
    if i < len(segments) - 1:
        final_audio += one_minute_silence

    # Clean up the temporary file
    os.remove(temp_audio_file)

# Export the final audio file
final_audio.export("audio.mp3", format="mp3")

print("Audio with pauses created successfully!")