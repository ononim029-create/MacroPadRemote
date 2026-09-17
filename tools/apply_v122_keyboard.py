from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def replace_between(text: str, start_marker: str, end_marker: str, replacement: str, label: str) -> str:
    start = text.find(start_marker)
    if start < 0:
        raise RuntimeError(f"{label}: start marker not found")
    end = text.find(end_marker, start)
    if end < 0:
        raise RuntimeError(f"{label}: end marker not found")
    return text[:start] + replacement + text[end:]

def main() -> None:
    path = ROOT / "src/mobile/macropad_mobile/lib/main.dart"
    text = path.read_text(encoding="utf-8")

    start_marker = "class _KeyboardKeySpec {"
    end_marker = "\nclass _SharpNavItem {"

    keyboard = r'''class _KeyboardKeySpec {
  final String token;
  final String en;
  final String ru;
  final String enShift;
  final String ruShift;
  final int flex;

  const _KeyboardKeySpec(
    this.token,
    this.en, {
    this.ru = '',
    this.enShift = '',
    this.ruShift = '',
    this.flex = 10,
  });
}

class _TabletRemoteKeyboard extends StatelessWidget {
  final Future<void> Function(String key, {bool modifier}) onKey;
  final Future<void> Function() onLanguage;
  final Set<String> activeModifiers;
  final String languageCode;

  const _TabletRemoteKeyboard({
    required this.onKey,
    required this.onLanguage,
    required this.activeModifiers,
    required this.languageCode,
  });

  static const _rows = <List<_KeyboardKeySpec>>[
    [
      _KeyboardKeySpec('ESC', 'Esc', flex: 13),
      _KeyboardKeySpec('GRAVE', '`', ru: 'Ё', enShift: '~'),
      _KeyboardKeySpec('1', '1', enShift: '!', ruShift: '!'),
      _KeyboardKeySpec('2', '2', enShift: '@', ruShift: '"'),
      _KeyboardKeySpec('3', '3', enShift: '#', ruShift: '№'),
      _KeyboardKeySpec('4', '4', enShift: r'$', ruShift: ';'),
      _KeyboardKeySpec('5', '5', enShift: '%', ruShift: '%'),
      _KeyboardKeySpec('6', '6', enShift: '^', ruShift: ':'),
      _KeyboardKeySpec('7', '7', enShift: '&', ruShift: '?'),
      _KeyboardKeySpec('8', '8', enShift: '*', ruShift: '*'),
      _KeyboardKeySpec('9', '9', enShift: '(', ruShift: '('),
      _KeyboardKeySpec('0', '0', enShift: ')', ruShift: ')'),
      _KeyboardKeySpec('MINUS', '-', enShift: '_', ruShift: '_'),
      _KeyboardKeySpec('EQUALS', '=', enShift: '+', ruShift: '+'),
      _KeyboardKeySpec('BACKSPACE', '⌫', flex: 18),
    ],
    [
      _KeyboardKeySpec('TAB', 'Tab', flex: 16),
      _KeyboardKeySpec('Q', 'Q', ru: 'Й'),
      _KeyboardKeySpec('W', 'W', ru: 'Ц'),
      _KeyboardKeySpec('E', 'E', ru: 'У'),
      _KeyboardKeySpec('R', 'R', ru: 'К'),
      _KeyboardKeySpec('T', 'T', ru: 'Е'),
      _KeyboardKeySpec('Y', 'Y', ru: 'Н'),
      _KeyboardKeySpec('U', 'U', ru: 'Г'),
      _KeyboardKeySpec('I', 'I', ru: 'Ш'),
      _KeyboardKeySpec('O', 'O', ru: 'Щ'),
      _KeyboardKeySpec('P', 'P', ru: 'З'),
      _KeyboardKeySpec('LBRACKET', '[', ru: 'Х', enShift: '{'),
      _KeyboardKeySpec('RBRACKET', ']', ru: 'Ъ', enShift: '}'),
      _KeyboardKeySpec('BACKSLASH', r'\', ru: r'\', enShift: '|', ruShift: '/', flex: 13),
    ],
    [
      _KeyboardKeySpec('CAPSLOCK', 'Caps', flex: 19),
      _KeyboardKeySpec('A', 'A', ru: 'Ф'),
      _KeyboardKeySpec('S', 'S', ru: 'Ы'),
      _KeyboardKeySpec('D', 'D', ru: 'В'),
      _KeyboardKeySpec('F', 'F', ru: 'А'),
      _KeyboardKeySpec('G', 'G', ru: 'П'),
      _KeyboardKeySpec('H', 'H', ru: 'Р'),
      _KeyboardKeySpec('J', 'J', ru: 'О'),
      _KeyboardKeySpec('K', 'K', ru: 'Л'),
      _KeyboardKeySpec('L', 'L', ru: 'Д'),
      _KeyboardKeySpec('SEMICOLON', ';', ru: 'Ж', enShift: ':'),
      _KeyboardKeySpec('QUOTE', "'", ru: 'Э', enShift: '"'),
      _KeyboardKeySpec('ENTER', 'Enter', flex: 22),
    ],
    [
      _KeyboardKeySpec('SHIFT', 'Shift', flex: 24),
      _KeyboardKeySpec('Z', 'Z', ru: 'Я'),
      _KeyboardKeySpec('X', 'X', ru: 'Ч'),
      _KeyboardKeySpec('C', 'C', ru: 'С'),
      _KeyboardKeySpec('V', 'V', ru: 'М'),
      _KeyboardKeySpec('B', 'B', ru: 'И'),
      _KeyboardKeySpec('N', 'N', ru: 'Т'),
      _KeyboardKeySpec('M', 'M', ru: 'Ь'),
      _KeyboardKeySpec('COMMA', ',', ru: 'Б', enShift: '<'),
      _KeyboardKeySpec('PERIOD', '.', ru: 'Ю', enShift: '>'),
      _KeyboardKeySpec('SLASH', '/', ru: '.', enShift: '?', ruShift: ','),
      _KeyboardKeySpec('SHIFT', 'Shift', flex: 24),
    ],
    [
      _KeyboardKeySpec('CTRL', 'Ctrl', flex: 15),
      _KeyboardKeySpec('WIN', '⊞', flex: 13),
      _KeyboardKeySpec('ALT', 'Alt', flex: 14),
      _KeyboardKeySpec('SPACE', '', flex: 62),
      _KeyboardKeySpec('LANG', '🌐', flex: 20),
      _KeyboardKeySpec('ALT', 'Alt', flex: 14),
      _KeyboardKeySpec('CTRL', 'Ctrl', flex: 15),
      _KeyboardKeySpec('HOME', 'Home', flex: 15),
      _KeyboardKeySpec('PAGEUP', 'PgUp', flex: 15),
      _KeyboardKeySpec('LEFT', '←', flex: 12),
      _KeyboardKeySpec('DOWN', '↓', flex: 12),
      _KeyboardKeySpec('UP', '↑', flex: 12),
      _KeyboardKeySpec('RIGHT', '→', flex: 12),
      _KeyboardKeySpec('END', 'End', flex: 15),
      _KeyboardKeySpec('PAGEDOWN', 'PgDn', flex: 15),
    ],
  ];

  bool get _isRu => languageCode.toUpperCase().startsWith('RU');

  bool _modifier(String token) =>
      token == 'CTRL' || token == 'ALT' || token == 'SHIFT' || token == 'WIN';

  String _primary(_KeyboardKeySpec spec) {
    if (spec.token == 'LANG') return '🌐 ${languageCode.toUpperCase()}';
    if (spec.token == 'SPACE') return '';
    if (_isRu && spec.ru.isNotEmpty) return spec.ru;
    return spec.en;
  }

  String _corner(_KeyboardKeySpec spec) {
    if (_isRu) return spec.ruShift;
    return spec.enShift;
  }

  @override
  Widget build(BuildContext context) => Container(
        color: const Color(0xff111315),
        padding: const EdgeInsets.fromLTRB(7, 4, 7, 6),
        child: Column(children: [
          for (final row in _rows)
            Expanded(
              child: Row(
                children: [
                  for (final spec in row)
                    Expanded(flex: spec.flex, child: _key(spec)),
                ],
              ),
            ),
        ]),
      );

  Widget _key(_KeyboardKeySpec spec) {
    final modifier = _modifier(spec.token);
    final active = activeModifiers.contains(spec.token);
    final primary = _primary(spec);
    final corner = _corner(spec);

    return Padding(
      padding: const EdgeInsets.all(2.2),
      child: Material(
        color: active ? const Color(0xff264e73) : mpPanel2,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(6),
          side: BorderSide(color: active ? mpBlue : mpBorder),
        ),
        child: InkWell(
          borderRadius: BorderRadius.circular(6),
          canRequestFocus: false,
          onTap: spec.token == 'LANG'
              ? onLanguage
              : () => onKey(spec.token, modifier: modifier),
          child: Stack(
            fit: StackFit.expand,
            children: [
              if (corner.isNotEmpty)
                Positioned(
                  left: 5,
                  top: 3,
                  child: Text(
                    corner,
                    style: const TextStyle(
                      color: v12Muted,
                      fontSize: 7.2,
                      fontWeight: FontWeight.w600,
                      height: 1,
                    ),
                  ),
                ),
              Center(
                child: spec.token == 'SPACE'
                    ? const SizedBox.shrink()
                    : Text(
                        primary,
                        textAlign: TextAlign.center,
                        maxLines: 1,
                        overflow: TextOverflow.fade,
                        style: TextStyle(
                          fontSize: spec.flex <= 12 ? 10.5 : 12.0,
                          height: 1,
                          color: Colors.white,
                          fontWeight:
                              active ? FontWeight.w700 : FontWeight.w600,
                        ),
                      ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
'''

    text = replace_between(text, start_marker, end_marker, keyboard, "v1.2.2 clean keyboard labels")
    path.write_text(text, encoding="utf-8")
    print(f"Applied v1.2.2 keyboard labels: {path}")

if __name__ == "__main__":
    main()
