import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
FONTS_DIR = BASE_DIR / "fonts"
WORD_TEMPLATE_PATH = TEMPLATES_DIR / "word_template.docx"

DEFAULT_FONT_NAME = "SourceHanSansCN"
DEFAULT_FONT_PATH = FONTS_DIR / "SourceHanSansCN.ttf"


def get_project_root() -> Path:
    return BASE_DIR


def ensure_directories():
    for d in [TEMPLATES_DIR, FONTS_DIR]:
        d.mkdir(parents=True, exist_ok=True)
