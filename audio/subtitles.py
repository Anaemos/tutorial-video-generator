import json
import re

def generate_subtitles(audio_path: str, output_path: str) -> str:
    from faster_whisper import WhisperModel

    model = WhisperModel("base", device="cpu")
    segments, _ = model.transcribe(audio_path, word_timestamps=True)
    
    with open(output_path, "w") as f:
        for i, seg in enumerate(segments, 1):
            start = _format_time(seg.start)
            end = _format_time(seg.end)
            f.write(f"{i}\n{start} --> {end}\n{seg.text.strip()}\n\n")
    
    return output_path

def generate_subtitles_from_timings(timings_path: str, output_path: str) -> str:
    with open(timings_path, "r", encoding="utf-8") as f:
        timings = json.load(f)

    subtitle_index = 1
    with open(output_path, "w", encoding="utf-8") as f:
        for item in timings:
            sentences = _split_sentences(item["narration"])
            start = float(item["narration_start"])
            end = float(item["narration_end"])
            duration = end - start
            total_chars = sum(len(sentence) for sentence in sentences) or 1
            current = start

            for sentence in sentences:
                sentence_duration = duration * (len(sentence) / total_chars)
                sentence_end = end if sentence == sentences[-1] else current + sentence_duration
                f.write(f"{subtitle_index}\n")
                f.write(f"{_format_time(current)} --> {_format_time(sentence_end)}\n")
                f.write(f"{sentence}\n\n")
                subtitle_index += 1
                current = sentence_end

    return output_path

def _split_sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]

def _format_time(seconds: float) -> str:
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{hrs:02}:{mins:02}:{secs:02},{ms:03}"
