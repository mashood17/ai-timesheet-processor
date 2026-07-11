"""
Standalone test script for PaddleOCR against ONE real cropped image from
your timesheet, before wiring it into the full pipeline.
"""
import os

_project_dir = os.path.dirname(os.path.abspath(__file__))
_fake_home = os.path.join(_project_dir, "..", "paddle_cache")
os.makedirs(_fake_home, exist_ok=True)

# BUGFIX: paddle's underlying framework tries to create a dataset cache
# under the real Windows user profile (~/.cache/paddle), which is denied
# on this machine (same root issue as the earlier Hugging Face permission
# error). Overriding USERPROFILE for this process only redirects Python's
# home-directory resolution to a folder we know is writable, without
# touching the real Windows user profile at all.
os.environ["USERPROFILE"] = os.path.abspath(_fake_home)
os.environ["PADDLE_PDX_CACHE_HOME"] = os.path.abspath(_fake_home)
import sys
import time
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_paddleocr.py <path_to_cropped_image.png>")
        sys.exit(1)

    image_path = Path(sys.argv[1])
    if not image_path.exists():
        print(f"File not found: {image_path}")
        sys.exit(1)

    print("Loading PaddleOCR (first run downloads ~200-400MB of models)...")
    t0 = time.time()
    from paddleocr import PaddleOCR

    ocr = PaddleOCR(use_textline_orientation=True, lang="en")
    print(f"Loaded in {time.time() - t0:.1f}s")

    t0 = time.time()
    result = ocr.ocr(str(image_path))
    elapsed = time.time() - t0

    print(f"\nInference time: {elapsed:.2f}s")
    print("Raw result:")
    for line in result:
        print(" ", line)

    # Flatten just the recognized text strings for a quick readable summary.
    print("\nRecognized text (in order found):")
    if result and result[0]:
        for detection in result[0]:
            text, confidence = detection[1]
            print(f"  {text!r}  (confidence: {confidence:.2f})")
    else:
        print("  (nothing detected)")

    print("\nCompare this to what you know the actual value should be.")


if __name__ == "__main__":
    main()