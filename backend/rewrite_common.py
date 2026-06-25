import re

with open(r"microservices\common.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("import cv2\n", "")
content = content.replace("import numpy as np\n", "")

new_fe = """async def build_frame_extraction(payload: dict[str, Any]) -> dict[str, Any]:
    return {"error": "GPU models must run remotely. This endpoint is disabled locally."}"""
content = re.sub(r'async def build_frame_extraction.*?return \{.*?\}', new_fe, content, flags=re.DOTALL)

new_cl = """async def build_classification(payload: dict[str, Any]) -> dict[str, Any]:
    return {"error": "GPU models must run remotely. This endpoint is disabled locally."}"""
content = re.sub(r'async def build_classification.*?return \{.*?\}', new_cl, content, flags=re.DOTALL)

new_dd = """async def build_defect_detection(payload: dict[str, Any]) -> dict[str, Any]:
    return {"error": "GPU models must run remotely. This endpoint is disabled locally."}"""
content = re.sub(r'async def build_defect_detection.*?return \{.*?\}', new_dd, content, flags=re.DOTALL)

with open(r"microservices\common.py", "w", encoding="utf-8") as f:
    f.write(content)

print("common.py rewrite successful")
