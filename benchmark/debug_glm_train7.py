import time, torch, logging
logging.basicConfig(level=logging.INFO)
from pathlib import Path
from transformers import AutoProcessor, GlmOcrForConditionalGeneration

img = Path("/app/benchmark/ocr/data/xfund_pt/pt_train_7.jpg")
print(f"image size: {img.stat().st_size} bytes")

proc = AutoProcessor.from_pretrained("zai-org/GLM-OCR")
model = GlmOcrForConditionalGeneration.from_pretrained(
    "zai-org/GLM-OCR", torch_dtype=torch.bfloat16, device_map="auto"
).eval()

messages = [{"role":"user","content":[
    {"type":"image","url":str(img)},
    {"type":"text","text":"Text Recognition:"},
]}]
inputs = proc.apply_chat_template(messages, tokenize=True, add_generation_prompt=True,
    return_dict=True, return_tensors="pt").to(model.device)
print(f"input_ids shape: {inputs['input_ids'].shape}")

for mnt in [1024, 2048, 4096]:
    t=time.time()
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=mnt, do_sample=False)
    gen = out[0][inputs["input_ids"].shape[1]:]
    txt = proc.decode(gen, skip_special_tokens=True)
    txt_raw = proc.decode(gen, skip_special_tokens=False)
    dt=time.time()-t
    print(f"\n=== max_new_tokens={mnt} latency={dt:.1f}s gen_tokens={gen.shape[0]} ===")
    print(f"len(decoded)={len(txt)} len(raw)={len(txt_raw)}")
    print(f"first 500 chars RAW: {txt_raw[:500]!r}")
    print(f"first 500 chars CLEAN: {txt[:500]!r}")
    print(f"last 200 chars RAW: {txt_raw[-200:]!r}")
