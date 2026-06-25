import re

with open(r"d:\maritime_web_codex\backend\backend.log", "r", encoding="utf-8") as f:
    for line in f:
        if "GPU URL=" in line or "GPU Response" in line or "process_video_from_bytes" in line or "Sending video" in line:
            print(line.strip())
