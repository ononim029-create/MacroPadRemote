from pathlib import Path

path = Path(__file__).resolve().parents[1] / 'src/mobile/macropad_mobile/lib/v12_workspace.dart'
text = path.read_text(encoding='utf-8')

# _KeySpec uses optional positional args; v1.2 helper originally passed modifier as a named arg.
text = text.replace(', modifier: true)', ', true)')

# PhysicalKeyboardKey has custom equality/hashCode and therefore cannot be used as a key in a const map.
text = text.replace('    const letters = <PhysicalKeyboardKey, String>{', '    final letters = <PhysicalKeyboardKey, String>{')
text = text.replace('    const digits = <PhysicalKeyboardKey, String>{', '    final digits = <PhysicalKeyboardKey, String>{')

path.write_text(text, encoding='utf-8')
print(f'Fixed Flutter v1.2 helpers: {path}')
