"""Crop a rectangle from the ASHEN VEIL environment atlas.

Usage:
    python tools/crop_atlas.py x y width height output.png
Coordinates refer to the original 1672x941 atlas.
"""
from pathlib import Path
import argparse
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ATLAS = ROOT / "assets" / "environment" / "ashen_village_atlas.png"

parser = argparse.ArgumentParser()
parser.add_argument("x", type=int)
parser.add_argument("y", type=int)
parser.add_argument("width", type=int)
parser.add_argument("height", type=int)
parser.add_argument("output", help="Output PNG path")
args = parser.parse_args()

image = Image.open(ATLAS).convert("RGBA")
box = (args.x, args.y, args.x + args.width, args.y + args.height)
if box[0] < 0 or box[1] < 0 or box[2] > image.width or box[3] > image.height:
    raise SystemExit(f"Crop rectangle outside atlas bounds {image.size}")

target = Path(args.output)
target.parent.mkdir(parents=True, exist_ok=True)
image.crop(box).save(target)
print(f"Saved: {target}")
