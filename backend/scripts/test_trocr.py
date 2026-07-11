"""
Standalone test script for TrOCR (Microsoft's handwriting-recognition
transformer model) against ONE real cropped image from your timesheet,
before we wire it into the full pipeline. This lets you verify actual
accuracy on your machine — the sandbox this was developed in has no
network access to Hugging Face's model hub, so this hasn't been verified
by Claude directly; you're the first real test.

Usage:
    cd backend
    .\venv\Scripts\Activate.ps1
    pip install torch transformers pillow
    python scripts/test_trocr.py path\to\a\cropped\iqama\image.png

The first run will download the model (~1.3GB) — this can take a few
minutes depending on your connection, and only happens once (cached
afterward under your user profile).
"""
import os
os.environ["HF_HOME"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hf_cache")
os.makedirs(os.environ["HF_HOME"], exist_ok=True)
import sys
import time
from pathlib import Path

from PIL import Image


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_trocr.py <path_to_cropped_image.png>")
        sys.exit(1)

    image_path = Path(sys.argv[1])
    if not image_path.exists():
        print(f"File not found: {image_path}")
        sys.exit(1)

    print("Loading TrOCR model (first run downloads ~1.3GB, please wait)...")
    t0 = time.time()
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel

    from transformers import RobertaTokenizer, ViTImageProcessor

    # Load components explicitly with the "slow" (pure-Python) tokenizer,
    # sidestepping the fast-tokenizer auto-conversion path that failed
    # earlier — TrOCR's tokenizer is RoBERTa-based BPE, not sentencepiece,
    # so the slow tokenizer works fine and needs no Rust-compiled library.
    image_processor = ViTImageProcessor.from_pretrained("microsoft/trocr-base-handwritten")
    tokenizer = RobertaTokenizer.from_pretrained("microsoft/trocr-base-handwritten")
    processor = TrOCRProcessor(image_processor=image_processor, tokenizer=tokenizer)
    model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-handwritten")
    print(f"Model loaded in {time.time() - t0:.1f}s")

    image = Image.open(image_path).convert("RGB")

    t0 = time.time()
    pixel_values = processor(images=image, return_tensors="pt").pixel_values
    generated_ids = model.generate(pixel_values)
    text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
    elapsed = time.time() - t0

    print(f"\nInference time: {elapsed:.2f}s")
    print(f"TrOCR result: {text!r}")
    print("\nCompare this to what you know the actual value should be.")


if __name__ == "__main__":
    main()