import edge_tts
import asyncio

def generate_tts(text: str, output_path: str) -> str:
    async def _generate():
        communicate = edge_tts.Communicate(text, voice="en-US-GuyNeural")
        await communicate.save(output_path)
    
    asyncio.run(_generate())
    return output_path