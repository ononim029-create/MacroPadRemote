from pathlib import Path

path = Path(__file__).resolve().parents[1] / 'src/mobile/macropad_mobile/lib/main.dart'
text = path.read_text(encoding='utf-8')
old = "        height: vertical ? 104 : double.infinity,"
new = "        height: vertical ? 104 : (navDock == ProfileDockSide.bottom ? navBottomHeight : 48),"
if text.count(old) != 1:
    raise RuntimeError(f'v1.2.1 nav sizing: expected one match, got {text.count(old)}')
path.write_text(text.replace(old, new, 1), encoding='utf-8')
print(f'Fixed v1.2.1 dock sizing: {path}')
