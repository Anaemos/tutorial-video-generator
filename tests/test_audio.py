import asyncio
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import edge_tts
from audio.subtitles import generate_subtitles_from_timings
from pydub import AudioSegment

steps = [
    {
        "step": 1,
        "narration": "Welcome to this Python calculator tutorial. Today we'll build a fully functional calculator from scratch. We'll cover addition, subtraction, multiplication, division, and even handle errors like dividing by zero. Let's start by creating a new Python file called calculator dot py.",
        "code": "# calculator.py\n# A simple calculator in Python"
    },
    {
        "step": 2,
        "narration": "First, let's implement the addition function. It takes two numbers as parameters and returns their sum. This is the simplest operation, but we'll follow the same pattern for all our functions.",
        "code": "def add(a, b):\n    return a + b"
    },
    {
        "step": 3,
        "narration": "Next, subtraction. The subtract function takes two parameters: a and b, and returns a minus b. Notice how we're documenting every function with a docstring — this is good Python practice.",
        "code": "def subtract(a, b):\n    return a - b"
    },
    {
        "step": 4,
        "narration": "Now let's add multiplication. The multiply function returns the product of a and b. Python uses the asterisk symbol for multiplication. Again, we keep it clean and simple.",
        "code": "def multiply(a, b):\n    return a * b"
    },
    {
        "step": 5,
        "narration": "Division needs special care. If someone tries to divide by zero, Python will raise a ZeroDivisionError. We handle that with a try-except block and return None to signal that the operation failed.",
        "code": "def divide(a, b):\n    try:\n        return a / b\n    except ZeroDivisionError:\n        return None"
    },
    {
        "step": 6,
        "narration": "Now let's bring everything together with a calculate function. It takes an operator string and two numbers, then calls the right function based on the operator. If the operator isn't recognised, we return None and print a helpful message.",
        "code": "def calculate(operator, a, b):\n    if operator == '+':\n        return add(a, b)\n    elif operator == '-':\n        return subtract(a, b)"
    },
    {
        "step": 7,
        "narration": "Let's test each function to make sure they work correctly. We'll call each one and print the result. Run this file and you should see the correct output for all four operations.",
        "code": "print(add(10, 5))\nprint(subtract(10, 5))\nprint(multiply(10, 5))\nprint(divide(10, 5))"
    },
    {
        "step": 8,
        "narration": "Now let's build an interactive loop so a user can type in their own calculations. We use a while True loop that keeps running until the user types quit. We also use a try-except to handle invalid number inputs gracefully.",
        "code": "def run_calculator():\n    while True:\n        user_input = input('Enter calculation: ').strip()\n        if user_input.lower() == 'quit':\n            break"
    },
    {
        "step": 9,
        "narration": "Let's wire up the entry point. We call run underscore calculator only when the script is run directly, not when it's imported. This is the standard Python idiom using the name equals main guard.",
        "code": "if __name__ == '__main__':\n    run_calculator()"
    },
    {
        "step": 10,
        "narration": "And that's our complete Python calculator! We covered four arithmetic operations, zero division handling, invalid input handling, and an interactive user loop. The full source is clean, well-documented, and easy to extend. Try adding a power operator or a modulo operator as a next step. Thanks for watching!",
        "code": "# End of tutorial"
    }
]

async def generate_step_audio(narration: str, output_path: str):
    communicate = edge_tts.Communicate(narration, voice="en-US-GuyNeural")
    await communicate.save(output_path)

def get_audio_duration(path: str) -> float:
    audio = AudioSegment.from_mp3(path)
    return len(audio) / 1000.0  # milliseconds to seconds

def get_code_pause(code: str) -> float:
    lines = [line for line in code.strip().split("\n") if line.strip()]
    return max(2.0, len(lines) * 1.5)

def build_pipeline():
    os.makedirs("output/audio/steps", exist_ok=True)
    os.makedirs("output/subtitles", exist_ok=True)

    combined = AudioSegment.empty()
    timings = []
    current_time = 0.0

    for step in steps:
        print(f"Processing step {step['step']}...")

        # Generate audio for this step
        step_path = f"output/audio/steps/step_{step['step']}.mp3"
        asyncio.run(generate_step_audio(step["narration"], step_path))

        # Measure duration
        duration = get_audio_duration(step_path)

        # Calculate pause based on code length
        code_pause = get_code_pause(step["code"])

        # Add to timings
        timings.append({
            "step": step["step"],
            "narration": step["narration"],
            "code": step["code"],
            "narration_start": round(current_time, 3),
            "narration_end": round(current_time + duration, 3),
            "code_start": round(current_time + duration, 3),
            "code_end": round(current_time + duration + code_pause, 3)
        })

        # Add narration audio + silence for code typing
        combined += AudioSegment.from_mp3(step_path)
        combined += AudioSegment.silent(duration=int(code_pause * 1000))

        current_time += duration + code_pause
        print(f"  Step {step['step']}: narration={round(duration,2)}s | code pause={round(code_pause,2)}s")

    # Save full audio
    combined.export("output/audio/calculator_narration.mp3", format="mp3")
    print("\nFull audio saved -> output/audio/calculator_narration.mp3")

    # Save timings
    with open("output/timings.json", "w") as f:
        json.dump(timings, f, indent=2)
    print("Timings saved -> output/timings.json")

    # Generate subtitles from full audio
    print("\nGenerating subtitles...")
    generate_subtitles_from_timings(
        "output/timings.json",
        "output/subtitles/calculator_subtitles.srt"
    )
    print("Subtitles saved -> output/subtitles/calculator_subtitles.srt")

if __name__ == "__main__":
    build_pipeline()
