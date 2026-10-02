from __future__ import annotations

import json
import plistlib
import re
import struct
import sys
import zlib
from pathlib import Path


def png_chunk(kind: bytes, data: bytes) -> bytes:
    payload = kind + data
    return struct.pack(">I", len(data)) + payload + struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF)


def write_icon(path: Path, size: int) -> None:
    bg = (23, 25, 27)
    blue = (22, 136, 255)
    white = (242, 242, 242)
    dark = (36, 39, 42)

    pixels = [list(bg) for _ in range(size * size)]

    margin = max(1, round(size * 0.19))
    gap = max(1, round(size * 0.055))
    mark = size - margin * 2
    cell = (mark - gap) // 2
    x0 = margin
    y0 = margin

    def fill_rect(x: int, y: int, w: int, h: int, color: tuple[int, int, int]) -> None:
        for yy in range(max(0, y), min(size, y + h)):
            row = yy * size
            for xx in range(max(0, x), min(size, x + w)):
                pixels[row + xx] = list(color)

    fill_rect(x0, y0, cell, cell, blue)
    fill_rect(x0 + cell + gap, y0, cell, cell, white)
    fill_rect(x0, y0 + cell + gap, cell, cell, white)
    fill_rect(x0 + cell + gap, y0 + cell + gap, cell, cell, dark)

    bx = x0 + cell + gap
    by = y0 + cell + gap
    border = max(1, round(size * 0.012))
    fill_rect(bx, by, cell, border, white)
    fill_rect(bx, by + cell - border, cell, border, white)
    fill_rect(bx, by, border, cell, white)
    fill_rect(bx + cell - border, by, border, cell, white)

    raw = bytearray()
    for y in range(size):
        raw.append(0)
        for x in range(size):
            raw.extend(pixels[y * size + x])

    data = b"\x89PNG\r\n\x1a\n"
    data += png_chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
    data += png_chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    data += png_chunk(b"IEND", b"")
    path.write_bytes(data)


def configure_icons(host: Path) -> None:
    icon_dir = host / "ios" / "Runner" / "Assets.xcassets" / "AppIcon.appiconset"
    icon_dir.mkdir(parents=True, exist_ok=True)

    specs = [
        ("iphone", "20x20", "2x", 40),
        ("iphone", "20x20", "3x", 60),
        ("iphone", "29x29", "2x", 58),
        ("iphone", "29x29", "3x", 87),
        ("iphone", "40x40", "2x", 80),
        ("iphone", "40x40", "3x", 120),
        ("iphone", "60x60", "2x", 120),
        ("iphone", "60x60", "3x", 180),
        ("ipad", "20x20", "1x", 20),
        ("ipad", "20x20", "2x", 40),
        ("ipad", "29x29", "1x", 29),
        ("ipad", "29x29", "2x", 58),
        ("ipad", "40x40", "1x", 40),
        ("ipad", "40x40", "2x", 80),
        ("ipad", "76x76", "1x", 76),
        ("ipad", "76x76", "2x", 152),
        ("ipad", "83.5x83.5", "2x", 167),
        ("ios-marketing", "1024x1024", "1x", 1024),
    ]

    images = []
    for idiom, logical_size, scale, pixels in specs:
        safe_size = logical_size.replace(".", "_")
        name = f"NEXO-{idiom}-{safe_size}-{scale}.png"
        write_icon(icon_dir / name, pixels)
        images.append({
            "size": logical_size,
            "idiom": idiom,
            "filename": name,
            "scale": scale,
        })

    contents = {
        "images": images,
        "info": {"version": 1, "author": "xcode"},
    }
    (icon_dir / "Contents.json").write_text(json.dumps(contents, indent=2), encoding="utf-8")


def configure_plist(host: Path) -> None:
    plist_path = host / "ios" / "Runner" / "Info.plist"
    with plist_path.open("rb") as f:
        data = plistlib.load(f)

    data["CFBundleDisplayName"] = "NEXO"
    data["CFBundleName"] = "NEXO"
    data["NSCameraUsageDescription"] = "NEXO uses the camera to scan the pairing QR code shown on your computer."
    data["NSBluetoothAlwaysUsageDescription"] = "NEXO uses Bluetooth to connect to your computer when Bluetooth mode is selected."
    data["NSBluetoothPeripheralUsageDescription"] = "NEXO uses Bluetooth to connect to your computer."
    data["NSLocalNetworkUsageDescription"] = "NEXO uses your local network to find and connect to your computer."
    data["ITSAppUsesNonExemptEncryption"] = False
    data["UISupportedInterfaceOrientations"] = [
        "UIInterfaceOrientationPortrait",
        "UIInterfaceOrientationLandscapeLeft",
        "UIInterfaceOrientationLandscapeRight",
    ]
    data["UISupportedInterfaceOrientations~ipad"] = [
        "UIInterfaceOrientationPortrait",
        "UIInterfaceOrientationPortraitUpsideDown",
        "UIInterfaceOrientationLandscapeLeft",
        "UIInterfaceOrientationLandscapeRight",
    ]

    with plist_path.open("wb") as f:
        plistlib.dump(data, f, sort_keys=False)


def configure_xcode(host: Path) -> None:
    project = host / "ios" / "Runner.xcodeproj" / "project.pbxproj"
    text = project.read_text(encoding="utf-8")
    text = text.replace("com.example.nexo", "com.nexo.remote")
    text = re.sub(
        r"IPHONEOS_DEPLOYMENT_TARGET = [^;]+;",
        "IPHONEOS_DEPLOYMENT_TARGET = 15.0;",
        text,
    )
    project.write_text(text, encoding="utf-8")

    podfile = host / "ios" / "Podfile"
    if podfile.exists():
        text = podfile.read_text(encoding="utf-8")
        if re.search(r"^\s*#?\s*platform :ios,", text, flags=re.MULTILINE):
            text = re.sub(
                r"^\s*#?\s*platform :ios,\s*'[^']+'",
                "platform :ios, '15.0'",
                text,
                count=1,
                flags=re.MULTILINE,
            )
        else:
            text = "platform :ios, '15.0'\n" + text
        podfile.write_text(text, encoding="utf-8")


def main() -> None:
    host = Path(sys.argv[1] if len(sys.argv) > 1 else "build-ios").resolve()
    if not (host / "ios").exists():
        raise SystemExit(f"iOS host not found: {host}")

    configure_plist(host)
    configure_xcode(host)
    configure_icons(host)
    print(f"Configured NEXO iOS host: {host}")


if __name__ == "__main__":
    main()
