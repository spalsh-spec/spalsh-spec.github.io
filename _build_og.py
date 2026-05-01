"""Generate og-image.png for spalsh-spec.github.io social previews.

1200x630 px (OG standard). Matches the personal page aesthetic:
  - Background #fbf8f3 (paper)
  - Body text #1a1a1a (ink) in Georgia
  - Accent #8b3a1f (terracotta)
  - Devanagari epigraph in Devanagari Sangam MN

Run: python3 _build_og.py
"""
from PIL import Image, ImageDraw, ImageFont
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "og-image.png")
W, H = 1200, 630

PAPER = (251, 248, 243)
INK = (26, 26, 26)
INK_SOFT = (61, 61, 61)
INK_FAINT = (122, 122, 122)
ACCENT = (139, 58, 31)
RULE = (217, 210, 195)

GEORGIA = "/System/Library/Fonts/Supplemental/Georgia.ttf"
GEORGIA_ITALIC = "/System/Library/Fonts/Supplemental/Georgia Italic.ttf"
GEORGIA_BOLD = "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"
DEVA = "/System/Library/Fonts/Supplemental/Devanagari Sangam MN.ttc"

img = Image.new("RGB", (W, H), PAPER)
d = ImageDraw.Draw(img)

# Top accent rule
d.rectangle([(80, 80), (180, 84)], fill=ACCENT)

# Name
name_font = ImageFont.truetype(GEORGIA_BOLD, 72)
d.text((80, 110), "Sparsh Sharma", font=name_font, fill=INK)

# Tagline
tag_font = ImageFont.truetype(GEORGIA_ITALIC, 34)
d.text((80, 210), "Falsification methodology for retrieval;", font=tag_font, fill=INK_SOFT)
d.text((80, 256), "cross-cultural Sanskrit–Dravidian engines.", font=tag_font, fill=INK_SOFT)

# Artifact card
card_y = 350
card_h = 130
d.rectangle([(80, card_y), (W - 80, card_y + card_h)], outline=RULE, width=2)

art_title = ImageFont.truetype(GEORGIA_BOLD, 30)
art_body = ImageFont.truetype(GEORGIA, 22)
d.text((110, card_y + 20), "falsify-eval  v0.1.1", font=art_title, fill=INK)
d.text((110, card_y + 64), "Four-null gate (incl. gold marginal-matched random) +", font=art_body, fill=INK_SOFT)
d.text((110, card_y + 92), "cryptographic state lock.  Apache-2.0.  Pure stdlib + numpy.", font=art_body, fill=INK_SOFT)

# Bottom row: URL + epigraph
url_font = ImageFont.truetype(GEORGIA, 22)
d.text((80, H - 70), "spalsh-spec.github.io", font=url_font, fill=INK_FAINT)

# Devanagari epigraph (right-aligned)
deva_font = ImageFont.truetype(DEVA, 38)
deva_text = "नेति  नेति"
bbox = d.textbbox((0, 0), deva_text, font=deva_font)
deva_w = bbox[2] - bbox[0]
d.text((W - 80 - deva_w, H - 95), deva_text, font=deva_font, fill=INK_SOFT)

iast_font = ImageFont.truetype(GEORGIA_ITALIC, 18)
iast_text = 'neti neti  —  "not this, not this"'
bbox = d.textbbox((0, 0), iast_text, font=iast_font)
iast_w = bbox[2] - bbox[0]
d.text((W - 80 - iast_w, H - 50), iast_text, font=iast_font, fill=INK_FAINT)

img.save(OUT, "PNG", optimize=True)
print(f"wrote {OUT}  ({os.path.getsize(OUT)/1024:.1f} KB)")
