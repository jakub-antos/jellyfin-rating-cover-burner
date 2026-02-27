#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import re
import math
import shutil
import subprocess
import warnings
from pathlib import Path
from typing import Optional, Tuple, List, Dict

# Ukryj DeprecationWarning (np. z bibliotek) – docelowo i tak naprawiamy źródło
warnings.filterwarnings("ignore", category=DeprecationWarning)

# ============================================================
# Dependency bootstrap
# ============================================================

REQUIRED = [
    ("PIL", "pillow"),
    ("colorama", "colorama"),
]

DEPS_HINTS = {
    "pillow": "Pillow (moduł 'PIL') – obróbka obrazów / generowanie okładek",
    "colorama": "colorama – kolory w terminalu (Windows/ANSI)",
}


def _pip_install(pkgs: List[str]):
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", *pkgs])


def ensure_deps():
    missing = []
    for import_name, pip_name in REQUIRED:
        try:
            __import__(import_name)
        except Exception:
            missing.append((import_name, pip_name))

    if not missing:
        return

    pip_pkgs = [pip_name for _, pip_name in missing]
    cmd = "pip install " + " ".join(pip_pkgs)

    print("\nBrakuje bibliotek wymaganych do działania skryptu:")
    for import_name, pip_name in missing:
        hint = DEPS_HINTS.get(pip_name, pip_name)
        if pip_name == "pillow":
            print(f"  • {hint}")
            print("    (Uwaga: instalujesz 'pillow', ale import w kodzie jest jako 'PIL'.)")
        else:
            print(f"  • {hint}")

    if len(pip_pkgs) == 1:
        ans = input(f"Czy zainstalować ją teraz za pomocą '{cmd}'? [T/n]: ").strip().lower()
    else:
        ans = input(f"Czy zainstalować je teraz za pomocą '{cmd}'? [T/n]: ").strip().lower()

    if ans in ("n", "nie", "no"):
        print("OK. Zainstaluj ręcznie:")
        for _, pip_name in missing:
            print(f"  pip install {pip_name}")
        sys.exit(1)

    try:
        _pip_install(pip_pkgs)
    except Exception as e:
        print(f"Nie udało się zainstalować zależności: {e}")
        sys.exit(1)


ensure_deps()

from colorama import Style
from colorama import just_fix_windows_console
from PIL import Image, ImageDraw, ImageFont, ImageOps

just_fix_windows_console()

# ============================================================
# Constants / defaults
# ============================================================

TARGET_SIZE = (300, 450)
TARGET_DPI = (96, 96)
COVER_NAME = "folder.jpg"

EXIF_MARKER = "JF_RATING_BADGE_V6"

DEFAULT_HEX = "#FFC108"

# Default badge size is "old 85%" but we call it new 100%.
DEFAULTS = {
    "offset_right": 28,
    "offset_bottom": 28,
    "inner_pad_x": 12,
    "inner_pad_y": 9,
    "corner_radius": 10,
    "star_size": 24,
    "star_text_gap": 9,
    "font_size": 29,
    "bg_rgba": (0, 0, 0, 160),
}

BACKUP_PREFIX = "folder_backup"

AHASH_THRESHOLD_BITS = 80
HIST_THRESHOLD = 0.25

# ============================================================
# Console helpers + truecolor (HEX) using ANSI
# ============================================================

def ansi_fg_rgb(r: int, g: int, b: int) -> str:
    return f"\x1b[38;2;{r};{g};{b}m"


def ansi_reset() -> str:
    return "\x1b[0m"


def parse_hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    s = hex_color.strip()
    if not s.startswith("#"):
        s = "#" + s
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", s):
        raise ValueError("HEX must be #RRGGBB")
    return int(s[1:3], 16), int(s[3:5], 16), int(s[5:7], 16)


def color_hex_text(text: str, hex_color: str) -> str:
    try:
        r, g, b = parse_hex_to_rgb(hex_color)
        return ansi_fg_rgb(r, g, b) + text + ansi_reset()
    except Exception:
        return text


def info(msg: str):
    print(color_hex_text(msg, "#00D7FF"))


def ok(msg: str):
    print(color_hex_text(msg, "#33DD66"))


def warn(msg: str):
    print(color_hex_text(msg, "#FFD166"))


def err(msg: str):
    print(color_hex_text(msg, "#FF5C5C"))


def question(msg: str):
    print(color_hex_text(msg, "#FF8C00"))


# ============================================================
# Input parsing
# ============================================================

def parse_int(prompt: str, default: int, min_v: Optional[int] = None, max_v: Optional[int] = None) -> int:
    s = input(f"{prompt} [{default}]: ").strip()
    if not s:
        v = default
    else:
        try:
            v = int(s)
        except Exception:
            warn("Niepoprawna liczba. Używam wartości domyślnej.")
            v = default
    if min_v is not None:
        v = max(min_v, v)
    if max_v is not None:
        v = min(max_v, v)
    return v


def parse_float(prompt: str, default: float, min_v: Optional[float] = None, max_v: Optional[float] = None) -> float:
    s = input(f"{prompt} [{default}]: ").strip().replace(",", ".")
    if not s:
        v = default
    else:
        try:
            v = float(s)
        except Exception:
            warn("Niepoprawna liczba. Używam wartości domyślnej.")
            v = default
    if min_v is not None:
        v = max(min_v, v)
    if max_v is not None:
        v = min(max_v, v)
    return v


def normalize_hex(s: str, default_hex: str) -> str:
    s = (s or "").strip()
    if not s:
        return default_hex
    if not s.startswith("#"):
        s = "#" + s
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", s):
        warn("Niepoprawny HEX (oczekuję #RRGGBB). Używam domyślnego.")
        return default_hex
    return s.upper()


def ask_hex(prompt: str, default_hex: str) -> str:
    star_default = color_hex_text(DEFAULT_HEX, DEFAULT_HEX)
    s = input(f"{prompt} [{default_hex}]: ").strip()
    return normalize_hex(s, default_hex)


def ask_rating_field_global() -> str:
    print("\n" + color_hex_text("═" * 60, "#FF8C00"))
    question("Z którego pola NFO pobrać ocenę? (wybór globalny na cały przebieg)")
    print("  1) <rating>")
    print("  2) <criticrating>")
    choice = input(color_hex_text("Wybór [1/2] (domyślnie 1): ", "#FF8C00")).strip()
    print(color_hex_text("═" * 60, "#FF8C00"))
    return "criticrating" if choice == "2" else "rating"


# ============================================================
# Rating extraction (with fallback + info)
# ============================================================

def round_half_up_1_decimal(x: float) -> float:
    """Zaokrąglanie do 1 miejsca po przecinku: 5 i wyżej w górę"""
    return round(x, 1)


def format_1_decimal(x: float) -> str:
    return f"{round_half_up_1_decimal(x):.1f}"


def _parse_float_text(s: str) -> Optional[float]:
    if not s:
        return None
    s = s.strip().replace(",", ".")
    m = re.search(r"(\d+(?:\.\d+)?)", s)
    if not m:
        return None
    try:
        return float(m.group(1))
    except Exception:
        return None


def _read_field_from_nfo_xml(text: str, field: str) -> Optional[float]:
    import xml.etree.ElementTree as ET
    root = ET.fromstring(text)

    if field == "criticrating":
        return _parse_float_text(root.findtext("criticrating"))

    direct = _parse_float_text(root.findtext("rating"))
    if direct is not None:
        return direct

    candidates = []
    for rating_node in root.findall(".//ratings//rating"):
        name = rating_node.attrib.get("name") if hasattr(rating_node, "attrib") else None
        val_text = (rating_node.text or "").strip()
        val_node = rating_node.find("value")
        if val_node is not None and (val_node.text or "").strip():
            val_text = (val_node.text or "").strip()
        if val_text:
            candidates.append((name, val_text))

    for name, val in candidates:
        if name and name.strip().lower() == "imdb":
            ff = _parse_float_text(val)
            if ff is not None:
                return ff
    for _, val in candidates:
        ff = _parse_float_text(val)
        if ff is not None:
            return ff

    return None


def _read_field_from_nfo_regex(text: str, field: str) -> Optional[float]:
    if field == "criticrating":
        m = re.search(r"<criticrating[^>]*>\s*([0-9]+(?:[.,][0-9]+)?)\s*</criticrating>", text, flags=re.IGNORECASE)
        return float(m.group(1).replace(",", ".")) if m else None

    m = re.search(r"<rating[^>]*>\s*([0-9]+(?:[.,][0-9]+)?)\s*</rating>", text, flags=re.IGNORECASE)
    return float(m.group(1).replace(",", ".")) if m else None


def read_rating_from_nfo(nfo_path: Path, preferred_field: str, fallback: bool = True) -> Optional[Tuple[float, str, bool]]:
    try:
        text = nfo_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None

    fields = [preferred_field]
    if fallback:
        other = "criticrating" if preferred_field == "rating" else "rating"
        fields.append(other)

    for idx, field in enumerate(fields):
        try:
            v = _read_field_from_nfo_xml(text, field)
            if v is not None and v > 0:  # Pomijamy 0.0 i wartości <= 0
                return (v, field, idx == 1)
        except Exception:
            pass

        try:
            v = _read_field_from_nfo_regex(text, field)
            if v is not None and v > 0:  # Pomijamy 0.0 i wartości <= 0
                return (v, field, idx == 1)
        except Exception:
            pass

    return None


def find_any_nfo_with_rating(d: Path, preferred_field: str) -> Optional[Tuple[Path, float, str, bool]]:
    candidates = []
    preferred = [d / "movie.nfo", d / "tvshow.nfo"]
    for p in preferred:
        if p.exists() and p.is_file():
            candidates.append(p)

    for p in sorted(d.glob("*.nfo")):
        if p.is_file() and p not in candidates:
            candidates.append(p)

    for p in candidates:
        out = read_rating_from_nfo(p, preferred_field=preferred_field, fallback=True)
        if out is not None:
            v, used_field, used_fallback = out
            return p, v, used_field, used_fallback

    return None


# ============================================================
# EXIF marker helpers
# ============================================================

def _exif_get_desc(img: Image.Image) -> str:
    try:
        exif = img.getexif()
        return str(exif.get(270, "") or "")
    except Exception:
        return ""


def image_has_marker(path: Path) -> bool:
    try:
        img = Image.open(path)
        desc = _exif_get_desc(img)
        return EXIF_MARKER in desc
    except Exception:
        return False


def exif_set_marker(exif, extra: str = ""):
    try:
        current = str(exif.get(270, "") or "")
        if EXIF_MARKER not in current:
            new_val = (current + " " + EXIF_MARKER + (" " + extra if extra else "")).strip()
            exif[270] = new_val
    except Exception:
        pass
    return exif


# ============================================================
# Image similarity (structure + color distribution)
# ============================================================

def average_hash_16x16(path: Path) -> Optional[int]:
    """
    Uses get_flattened_data() instead of deprecated getdata()
    """
    try:
        img = Image.open(path).convert("L")
        img = ImageOps.fit(img, (16, 16), method=Image.Resampling.LANCZOS)

        # Pillow: getdata() deprecated -> get_flattened_data()
        pixels = list(img.get_flattened_data())
        avg = sum(pixels) / len(pixels)

        bits = 0
        for p in pixels:
            bits = (bits << 1) | (1 if p >= avg else 0)
        return bits
    except Exception:
        return None


def hamming_distance(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def normalized_rgb_hist(path: Path, bins_per_channel: int = 16) -> Optional[List[float]]:
    try:
        img = Image.open(path).convert("RGB")
        img = ImageOps.fit(img, (256, 256), method=Image.Resampling.LANCZOS)
        h = img.histogram()
        if len(h) != 768:
            return None

        def downbin(channel_hist_256):
            step = 256 // bins_per_channel
            out = []
            for i in range(0, 256, step):
                out.append(sum(channel_hist_256[i:i + step]))
            return out

        r = downbin(h[0:256])
        g = downbin(h[256:512])
        b = downbin(h[512:768])
        vec = r + g + b
        s = float(sum(vec))
        if s <= 0:
            return None
        return [v / s for v in vec]
    except Exception:
        return None


def hist_l1_distance(a: List[float], b: List[float]) -> float:
    return sum(abs(x - y) for x, y in zip(a, b)) / 2.0


def images_very_different(a_path: Path, b_path: Path) -> bool:
    ha = average_hash_16x16(a_path)
    hb = average_hash_16x16(b_path)
    if ha is not None and hb is not None:
        if hamming_distance(ha, hb) >= AHASH_THRESHOLD_BITS:
            return True

    ah = normalized_rgb_hist(a_path)
    bh = normalized_rgb_hist(b_path)
    if ah is not None and bh is not None and len(ah) == len(bh):
        if hist_l1_distance(ah, bh) >= HIST_THRESHOLD:
            return True

    return False


# ============================================================
# Drawing
# ============================================================

def load_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\calibrib.ttf",
        r"C:\Windows\Fonts\calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    for p in candidates:
        try:
            if Path(p).exists():
                return ImageFont.truetype(p, size=size)
        except Exception:
            pass
    return ImageFont.load_default()


def star_polygon(cx: float, cy: float, r_outer: float, r_inner: float, points: int = 5):
    pts = []
    angle = -math.pi / 2.0
    step = math.pi / points
    for i in range(points * 2):
        r = r_outer if i % 2 == 0 else r_inner
        x = cx + math.cos(angle) * r
        y = cy + math.sin(angle) * r
        pts.append((x, y))
        angle += step
    return pts


def scaled_int(v: int, scale: float, min_v: int = 1) -> int:
    return max(min_v, int(round(v * scale)))


def parse_hex_rgba(hex_color: str) -> Tuple[int, int, int, int]:
    r, g, b = parse_hex_to_rgb(hex_color)
    return (r, g, b, 255)


def draw_badge_bottom_right(base_rgb: Image.Image, rating_text: str, cfg: Dict) -> Image.Image:
    base_rgba = base_rgb.convert("RGBA")
    overlay = Image.new("RGBA", base_rgba.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)

    font = load_font(cfg["font_size"])
    bbox = d.textbbox((0, 0), rating_text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    badge_h = max(cfg["star_size"], text_h) + 2 * cfg["inner_pad_y"]
    badge_w = cfg["star_size"] + cfg["star_text_gap"] + text_w + 2 * cfg["inner_pad_x"]

    x2 = base_rgba.width - cfg["offset_right"]
    y2 = base_rgba.height - cfg["offset_bottom"]
    x1 = x2 - badge_w
    y1 = y2 - badge_h

    if x1 < 0:
        x1, x2 = 0, badge_w
    if y1 < 0:
        y1, y2 = 0, badge_h

    # Ustawianie rogów na podstawie konfiguracji użytkownika
    # Kolejność w Pillow to: (lewy-górny, prawy-górny, prawy-dolny, lewy-dolny)
    corners_config = (
        cfg["round_left"],   # lewy górny
        cfg["round_right"],  # prawy górny
        cfg["round_right"],  # prawy dolny
        cfg["round_left"]    # lewy dolny
    )

    d.rounded_rectangle(
        [x1, y1, x2, y2], 
        radius=cfg["corner_radius"], 
        fill=cfg["bg_rgba"],
        corners=corners_config
    )

    star_cx = x1 + cfg["inner_pad_x"] + cfg["star_size"] / 2.0
    star_cy = y1 + badge_h / 2.0
    pts = star_polygon(
        star_cx, star_cy,
        r_outer=cfg["star_size"] * 0.50,
        r_inner=cfg["star_size"] * 0.22,
        points=5
    )
    d.polygon(pts, fill=cfg["star_color"])

    tx = x1 + cfg["inner_pad_x"] + cfg["star_size"] + cfg["star_text_gap"]
    ty = y1 + (badge_h - text_h) / 2.0 - bbox[1]
    d.text((tx, ty), rating_text, font=font, fill=cfg["text_color"])

    composed = Image.alpha_composite(base_rgba, overlay)
    return composed.convert("RGB")


# ============================================================
# Backup selection / creation
# ============================================================

def backup_candidates(d: Path) -> List[Path]:
    pats = [d / f"{BACKUP_PREFIX}.jpg", *sorted(d.glob(f"{BACKUP_PREFIX}_*.jpg"))]
    out = []
    for p in pats:
        if p.exists() and p.is_file():
            out.append(p)
    for p in sorted(d.glob(f"{BACKUP_PREFIX}*.jpg")):
        if p.exists() and p.is_file() and p not in out:
            out.append(p)
    return out


def newest_clean_backup(d: Path) -> Optional[Path]:
    cands = [p for p in backup_candidates(d) if not image_has_marker(p)]
    cands.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return cands[0] if cands else None


def timestamped_backup_name(d: Path) -> Path:
    import datetime
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    return d / f"{BACKUP_PREFIX}_{ts}.jpg"


def create_new_clean_backup_from_current(d: Path, cover: Path) -> Optional[Path]:
    if not cover.exists() or image_has_marker(cover):
        return None

    primary = d / f"{BACKUP_PREFIX}.jpg"
    if not primary.exists():
        shutil.copy2(cover, primary)
        ok(f"[{d}] Backup (oryginalny): {cover.name} -> {primary.name}")
        return primary

    p = timestamped_backup_name(d)
    shutil.copy2(cover, p)
    ok(f"[{d}] Backup (nowa okładka): {cover.name} -> {p.name}")
    return p


def pick_base_cover_for_render(d: Path, cover: Path) -> Optional[Path]:
    b = newest_clean_backup(d)
    if b:
        return b
    if cover.exists() and cover.is_file() and not image_has_marker(cover):
        created = create_new_clean_backup_from_current(d, cover)
        return created if created else cover
    return None


def maybe_refresh_backup_if_cover_changed(d: Path, cover: Path) -> Optional[Path]:
    if not cover.exists() or image_has_marker(cover):
        return None

    b = newest_clean_backup(d)
    if not b:
        return create_new_clean_backup_from_current(d, cover)

    if images_very_different(cover, b):
        warn(f"[{d}] Wykryto dużą różnicę folder.jpg vs backup ({b.name}) → robię nowy backup.")
        return create_new_clean_backup_from_current(d, cover)

    return None


# ============================================================
# Cover open/save
# ============================================================

def open_fit_cover(path: Path) -> Image.Image:
    img = Image.open(path).convert("RGB")
    img = ImageOps.fit(img, TARGET_SIZE, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    return img


def save_cover_with_marker(img_rgb: Image.Image, cover: Path, marker_extra: str = ""):
    exif = img_rgb.getexif()
    exif = exif_set_marker(exif, marker_extra)
    img_rgb.save(
        cover,
        format="JPEG",
        quality=95,
        subsampling=0,
        dpi=TARGET_DPI,
        optimize=True,
        exif=exif.tobytes()
    )


# ============================================================
# Processing
# ============================================================

def process_dir(d: Path, cfg: Dict, preferred_field: str) -> bool:
    cover = d / COVER_NAME
    if not cover.exists() or not cover.is_file():
        return False

    found = find_any_nfo_with_rating(d, preferred_field=preferred_field)
    if not found:
        return False

    nfo_path, rating, used_field, used_fallback = found
    rating_text = format_1_decimal(rating)  # Prawidłowe zaokrąglanie

    maybe_refresh_backup_if_cover_changed(d, cover)

    base = pick_base_cover_for_render(d, cover)
    if base is None:
        warn(f"[{d}] Brak czystej okładki do generowania (folder.jpg ma marker, a backupu bez markera brak).")
        warn("Pomijam, żeby nie nakładać oceny na ocenę.")
        return False

    info(f"[{d}] Źródło: {nfo_path.name} | preferowane: <{preferred_field}>")
    if used_fallback:
        warn(f"[{d}] Brak <{preferred_field}> w NFO → użyłem <{used_field}> jako fallback.")
    info(f"[{d}] Ocena: {rating} -> {rating_text} | Baza: {base.name}")

    img = open_fit_cover(base)
    img = draw_badge_bottom_right(img, rating_text, cfg)
    save_cover_with_marker(img, cover, marker_extra=f"field={used_field};rating={rating_text}")
    ok(f"[{d}] Zapisano: {cover.name}")
    return True


def restore_cover(d: Path) -> bool:
    cover = d / COVER_NAME
    if not cover.exists():
        return False
    b = newest_clean_backup(d)
    if not b:
        return False
    shutil.copy2(b, cover)
    ok(f"[{d}] Przywrócono {cover.name} z {b.name}")
    return True


def iter_target_dirs(root: Path, recursive: bool):
    if recursive:
        yield root
        for p in root.rglob("*"):
            if p.is_dir():
                yield p
    else:
        yield root


# ============================================================
# Config from user
# ============================================================

def build_cfg_from_user() -> Dict:
    print("\n" + color_hex_text("═" * 60, "#FF8C00"))
    question("Wskazówka: naciśnij Enter, aby zaakceptować wartość domyślną w nawiasie [].")
    print(color_hex_text("═" * 60, "#FF8C00"))

    star_default = color_hex_text(DEFAULT_HEX, DEFAULT_HEX)
    star_hex = ask_hex(f"Kolor gwiazdki HEX (#RRGGBB) (domyślnie {star_default})", DEFAULT_HEX)

    text_default = color_hex_text(DEFAULT_HEX, DEFAULT_HEX)
    text_hex = ask_hex(f"Kolor oceny HEX (#RRGGBB) (domyślnie {text_default})", DEFAULT_HEX)

    opacity_alpha = parse_int(
        "Przezroczystość tła (alpha 0-255; 0=przezroczyste, 255=pełne)",
        DEFAULTS["bg_rgba"][3],
        min_v=0,
        max_v=255
    )

    scale_percent = parse_float("Rozmiar oceny w skali:", 100.0, min_v=10.0, max_v=400.0)
    scale = scale_percent / 100.0

    offset_right = parse_int("O ile px odsunąć od prawej krawędzi?", DEFAULTS["offset_right"], min_v=0, max_v=10000)
    offset_bottom = parse_int("O ile px odsunąć od dołu?", DEFAULTS["offset_bottom"], min_v=0, max_v=10000)

    ans_left = input("Czy zaokrąglić lewe boki tła? [T/n]: ").strip().lower()
    round_left = ans_left not in ("n", "nie", "no")

    ans_right = input("Czy zaokrąglić prawe boki tła? [T/n]: ").strip().lower()
    round_right = ans_right not in ("n", "nie", "no")

    cfg = {
        "offset_right": offset_right,
        "offset_bottom": offset_bottom,
        "inner_pad_x": max(1, int(round(DEFAULTS["inner_pad_x"] * scale))),
        "inner_pad_y": max(1, int(round(DEFAULTS["inner_pad_y"] * scale))),
        "corner_radius": max(1, int(round(DEFAULTS["corner_radius"] * scale))),
        "star_size": max(1, int(round(DEFAULTS["star_size"] * scale))),
        "star_text_gap": max(1, int(round(DEFAULTS["star_text_gap"] * scale))),
        "font_size": max(1, int(round(DEFAULTS["font_size"] * scale))),
        "bg_rgba": (0, 0, 0, int(opacity_alpha)),
        "star_color": (*parse_hex_to_rgb(star_hex), 255),
        "text_color": (*parse_hex_to_rgb(text_hex), 255),
        "round_left": round_left,
        "round_right": round_right,
    }
    return cfg


# ============================================================
# Main
# ============================================================

def ask_root_path_required(default_path: Optional[Path] = None) -> Path:
    while True:
        prompt = "Wklej adres! Podaj ścieżkę startową do przeszukiwania"
        if default_path:
            prompt += f" (Enter = {default_path})"
        prompt += ": "
        
        s = input(color_hex_text(prompt, "#FF8C00")).strip()
        
        if not s and default_path:
            return default_path
            
        if not s:
            warn("Wklej adres!")
            continue

        # ułatwienie: ścieżka w cudzysłowie z Exploratora
        s = s.strip().strip('"').strip("'")
        p = Path(s)

        if not p.exists():
            err("Podana ścieżka nie istnieje. Spróbuj ponownie.")
            continue
        if not p.is_dir():
            err("Podana ścieżka nie jest katalogiem. Spróbuj ponownie.")
            continue

        return p


def main():
    print(Style.BRIGHT + "Wypalanie oceny w okładce." + Style.RESET_ALL)
    last_root = None

    while True:
        print("\n" + color_hex_text("═" * 60, "#FF8C00"))
        question("Co chcesz zrobić?")
        print("  1) Umieścić / odświeżyć ocenę na okładkach (folder.jpg)")
        print("  2) Przywrócić okładki z najnowszej czystej kopii (backup) – bez oceny")
        print(color_hex_text("═" * 60, "#FF8C00"))
        choice = input(color_hex_text("Wybór [1/2]: ", "#FF8C00")).strip()

        if choice not in ("1", "2"):
            err("Nieprawidłowy wybór.")
            continue

        root = ask_root_path_required(last_root)
        last_root = root

        recursive_str = input(color_hex_text("Przetwarzać rekursywnie podkatalogi? [T/n]: ", "#FF8C00")).strip().lower()
        recursive = recursive_str not in ("n", "nie", "no")

        info(f"Katalog startowy: {root}")

        if choice == "2":
            restored = 0
            checked = 0
            for d in iter_target_dirs(root, recursive):
                checked += 1
                try:
                    if restore_cover(d):
                        restored += 1
                except Exception as e:
                    err(f"[{d}] Błąd przy przywracaniu: {e}")
            
            ok(f"Gotowe. Przywrócono w {restored} katalogach (sprawdzono {checked}).")
            try:
                input("\nNaciśnij Enter, aby powrócić do menu lub zamknij okno skryptu...")
            except Exception:
                pass
            continue

        if choice == "1":
            preferred_field = ask_rating_field_global()
            cfg = build_cfg_from_user()

            processed = 0
            checked = 0
            skipped_no_cover = 0
            skipped_no_nfo = 0

            for d in iter_target_dirs(root, recursive):
                checked += 1
                cover = d / COVER_NAME
                if not cover.exists():
                    skipped_no_cover += 1
                    continue

                try:
                    did = process_dir(d, cfg, preferred_field=preferred_field)
                    if did:
                        processed += 1
                    else:
                        skipped_no_nfo += 1
                except Exception as e:
                    err(f"[{d}] Błąd: {e}")

            print()
            ok(f"Wynik: przerobiono {processed} katalogów.")
            info(f"Sprawdzono: {checked}. Bez folder.jpg: {skipped_no_cover}. Bez NFO z oceną: {skipped_no_nfo}.")
            
            # Wymagany przez Ciebie komunikat testowania i możliwości ponowienia
            print("\n" + color_hex_text("═" * 60, "#33DD66"))
            print(color_hex_text("Odśwież Jellyfin i zweryfikuj poprawne umiejscowienie.", "#33DD66"))
            print(color_hex_text("W przypadku chęci zmiany naciśnij Enter (rozpocznie proces od nowa),", "#33DD66"))
            print(color_hex_text("lub zamknij skrypt (np. krzyżykiem).", "#33DD66"))
            print(color_hex_text("═" * 60, "#33DD66"))
            
            try:
                input()
            except Exception:
                pass


if __name__ == "__main__":
    main()
