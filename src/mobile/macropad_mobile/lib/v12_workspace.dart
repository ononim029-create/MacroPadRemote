import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

const v12Bg = Color(0xff17191b);
const v12Panel = Color(0xff1d1f21);
const v12Panel2 = Color(0xff24272a);
const v12Hover = Color(0xff2c3034);
const v12Border = Color(0xff353a3e);
const v12Text = Color(0xfff2f2f2);
const v12Muted = Color(0xff9da3a8);
const v12Blue = Color(0xff1688ff);

enum ProfileDockSide { left, right, top, bottom }

class KeyboardLayoutSummary {
  final String id;
  final String label;
  final String code;

  const KeyboardLayoutSummary({required this.id, required this.label, required this.code});

  factory KeyboardLayoutSummary.fromJson(Map<String, dynamic> json) => KeyboardLayoutSummary(
        id: '${json['id'] ?? ''}',
        label: '${json['label'] ?? ''}',
        code: '${json['code'] ?? 'KB'}',
      );
}

class WorkspaceViewState {
  final List<double> matrix;
  final bool profileRailVisible;
  final bool navVisible;
  final bool keyboardVisible;
  final double keyboardHeight;
  final ProfileDockSide profileDock;

  const WorkspaceViewState({
    required this.matrix,
    required this.profileRailVisible,
    required this.navVisible,
    required this.keyboardVisible,
    required this.keyboardHeight,
    required this.profileDock,
  });

  factory WorkspaceViewState.defaults() => WorkspaceViewState(
        matrix: Matrix4.identity().storage.toList(growable: false),
        profileRailVisible: true,
        navVisible: false,
        keyboardVisible: true,
        keyboardHeight: 250,
        profileDock: ProfileDockSide.left,
      );

  factory WorkspaceViewState.fromJson(Map<String, dynamic> json) {
    final raw = (json['matrix'] as List?)?.whereType<num>().map((e) => e.toDouble()).toList() ?? const <double>[];
    final dockName = '${json['profileDock'] ?? 'left'}';
    final dock = ProfileDockSide.values.firstWhere(
      (x) => x.name == dockName,
      orElse: () => ProfileDockSide.left,
    );
    return WorkspaceViewState(
      matrix: raw.length == 16 ? raw : Matrix4.identity().storage.toList(growable: false),
      profileRailVisible: json['profileRailVisible'] != false,
      navVisible: json['navVisible'] == true,
      keyboardVisible: json['keyboardVisible'] != false,
      keyboardHeight: ((json['keyboardHeight'] as num?)?.toDouble() ?? 250).clamp(150.0, 430.0),
      profileDock: dock,
    );
  }

  Map<String, dynamic> toJson() => {
        'matrix': matrix,
        'profileRailVisible': profileRailVisible,
        'navVisible': navVisible,
        'keyboardVisible': keyboardVisible,
        'keyboardHeight': keyboardHeight,
        'profileDock': profileDock.name,
      };
}

class WorkspaceViewStore {
  static const FlutterSecureStorage _storage = FlutterSecureStorage();
  static const _prefix = 'nexo_workspace_v12_';

  static String _key(String serverId, String formFactor) => '$_prefix${serverId}_$formFactor';

  static Future<WorkspaceViewState> load(String serverId, String formFactor) async {
    if (serverId.isEmpty) return WorkspaceViewState.defaults();
    try {
      final raw = await _storage.read(key: _key(serverId, formFactor));
      if (raw == null || raw.isEmpty) return WorkspaceViewState.defaults();
      return WorkspaceViewState.fromJson(Map<String, dynamic>.from(jsonDecode(raw) as Map));
    } catch (_) {
      return WorkspaceViewState.defaults();
    }
  }

  static Future<void> save(String serverId, String formFactor, WorkspaceViewState state) async {
    if (serverId.isEmpty) return;
    try {
      await _storage.write(key: _key(serverId, formFactor), value: jsonEncode(state.toJson()));
    } catch (_) {}
  }
}

class ProfileRailItem {
  final String id;
  final String icon;
  const ProfileRailItem({required this.id, required this.icon});
}

class ProfileIconView extends StatelessWidget {
  final String value;
  final double size;
  final Color? color;

  const ProfileIconView({super.key, required this.value, this.size = 24, this.color});

  @override
  Widget build(BuildContext context) {
    if (value.startsWith('data:image/')) {
      try {
        final comma = value.indexOf(',');
        final payload = comma >= 0 ? value.substring(comma + 1) : value;
        return SizedBox(width: size, height: size, child: Image.memory(base64Decode(payload), fit: BoxFit.contain, gaplessPlayback: true));
      } catch (_) {}
    }
    return SizedBox(
      width: size,
      height: size,
      child: Center(
        child: Text(value.trim().isEmpty ? '•' : value, maxLines: 1, overflow: TextOverflow.clip, style: TextStyle(color: color ?? Colors.white, fontSize: size * .62, fontWeight: FontWeight.w700, height: 1)),
      ),
    );
  }
}

class NexoProfileRail extends StatefulWidget {
  final List<ProfileRailItem> items;
  final String activeId;
  final ProfileDockSide dock;
  final ValueChanged<String> onSelected;
  final VoidCallback onToggle;
  final ValueChanged<ProfileDockSide> onDockChanged;

  const NexoProfileRail({
    super.key,
    required this.items,
    required this.activeId,
    required this.dock,
    required this.onSelected,
    required this.onToggle,
    required this.onDockChanged,
  });

  @override
  State<NexoProfileRail> createState() => _NexoProfileRailState();
}

class _NexoProfileRailState extends State<NexoProfileRail> {
  final ScrollController _scroll = ScrollController();

  bool get _vertical => widget.dock == ProfileDockSide.left || widget.dock == ProfileDockSide.right;

  @override
  void dispose() {
    _scroll.dispose();
    super.dispose();
  }

  void _step(double amount) {
    if (!_scroll.hasClients) return;
    final target = (_scroll.offset + amount).clamp(0.0, _scroll.position.maxScrollExtent);
    _scroll.animateTo(target, duration: const Duration(milliseconds: 190), curve: Curves.easeOutCubic);
  }

  Future<void> _showDockMenu(BuildContext context) async {
    final selected = await showModalBottomSheet<ProfileDockSide>(
      context: context,
      backgroundColor: v12Panel,
      builder: (_) => SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          const ListTile(title: Text('Закрепить панель профилей', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w600))),
          for (final side in ProfileDockSide.values)
            ListTile(
              leading: Icon(switch (side) { ProfileDockSide.left => Icons.align_horizontal_left, ProfileDockSide.right => Icons.align_horizontal_right, ProfileDockSide.top => Icons.vertical_align_top, ProfileDockSide.bottom => Icons.vertical_align_bottom }, color: side == widget.dock ? v12Blue : Colors.white),
              title: Text(switch (side) { ProfileDockSide.left => 'Слева', ProfileDockSide.right => 'Справа', ProfileDockSide.top => 'Сверху', ProfileDockSide.bottom => 'Снизу' }, style: const TextStyle(color: Colors.white)),
              onTap: () => Navigator.of(context).pop(side),
            ),
        ]),
      ),
    );
    if (selected != null) widget.onDockChanged(selected);
  }

  @override
  Widget build(BuildContext context) {
    const itemExtent = 44.0;
    const arrowExtent = 24.0;
    final listExtent = itemExtent * 4;
    final selectedColor = Color.lerp(v12Bg, Colors.white, .20)!;

    Widget arrow(IconData icon, VoidCallback action) => SizedBox(
          width: _vertical ? 48 : arrowExtent,
          height: _vertical ? arrowExtent : 48,
          child: InkWell(onTap: action, child: Icon(icon, size: 18, color: v12Muted)),
        );

    Widget list() => SizedBox(
          width: _vertical ? 48 : listExtent,
          height: _vertical ? listExtent : 48,
          child: ListView.builder(
            controller: _scroll,
            scrollDirection: _vertical ? Axis.vertical : Axis.horizontal,
            physics: const BouncingScrollPhysics(parent: AlwaysScrollableScrollPhysics()),
            itemExtent: itemExtent,
            itemCount: widget.items.length,
            itemBuilder: (_, index) {
              final item = widget.items[index];
              final selected = item.id == widget.activeId;
              return Padding(
                padding: const EdgeInsets.all(2),
                child: Material(
                  color: selected ? selectedColor : v12Panel2,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8), side: BorderSide(color: selected ? v12Blue : v12Border)),
                  child: InkWell(
                    borderRadius: BorderRadius.circular(8),
                    onTap: () => widget.onSelected(item.id),
                    child: Center(child: ProfileIconView(value: item.icon, size: 26, color: selected ? Colors.white : v12Text)),
                  ),
                ),
              );
            },
          ),
        );

    final content = _vertical
        ? Column(mainAxisSize: MainAxisSize.min, children: [
            arrow(Icons.keyboard_arrow_up, () => _step(-itemExtent)),
            list(),
            arrow(Icons.keyboard_arrow_down, () => _step(itemExtent)),
          ])
        : Row(mainAxisSize: MainAxisSize.min, children: [
            arrow(Icons.keyboard_arrow_left, () => _step(-itemExtent)),
            list(),
            arrow(Icons.keyboard_arrow_right, () => _step(itemExtent)),
          ]);

    return GestureDetector(
      onLongPress: () => _showDockMenu(context),
      child: Material(
        color: const Color(0xee1d1f21),
        elevation: 6,
        borderRadius: BorderRadius.circular(11),
        child: Container(
          decoration: BoxDecoration(border: Border.all(color: v12Border), borderRadius: BorderRadius.circular(11)),
          child: content,
        ),
      ),
    );
  }
}

class NexoTabletKeyboard extends StatelessWidget {
  final Future<void> Function(String key, {bool modifier}) onKey;
  final Set<String> activeModifiers;
  final List<KeyboardLayoutSummary> layouts;
  final String activeLayoutId;
  final ValueChanged<String> onLayoutSelected;

  const NexoTabletKeyboard({
    super.key,
    required this.onKey,
    required this.activeModifiers,
    required this.layouts,
    required this.activeLayoutId,
    required this.onLayoutSelected,
  });

  static const _ru = <String, String>{
    'Q':'Й','W':'Ц','E':'У','R':'К','T':'Е','Y':'Н','U':'Г','I':'Ш','O':'Щ','P':'З',
    'LBRACKET':'Х','RBRACKET':'Ъ','A':'Ф','S':'Ы','D':'В','F':'А','G':'П','H':'Р','J':'О','K':'Л','L':'Д',
    'SEMICOLON':'Ж','QUOTE':'Э','Z':'Я','X':'Ч','C':'С','V':'М','B':'И','N':'Т','M':'Ь','COMMA':'Б','PERIOD':'Ю',
  };

  static const _rows = <List<_KeySpec>>[
    [
      _KeySpec('ESC', 1.05), _KeySpec('1'), _KeySpec('2'), _KeySpec('3'), _KeySpec('4'), _KeySpec('5'), _KeySpec('6'), _KeySpec('7'), _KeySpec('8'), _KeySpec('9'), _KeySpec('0'), _KeySpec('MINUS'), _KeySpec('PLUS'), _KeySpec('DELETE', 1.35),
    ],
    [
      _KeySpec('TAB', 1.45), _KeySpec('Q'), _KeySpec('W'), _KeySpec('E'), _KeySpec('R'), _KeySpec('T'), _KeySpec('Y'), _KeySpec('U'), _KeySpec('I'), _KeySpec('O'), _KeySpec('P'), _KeySpec('LBRACKET'), _KeySpec('RBRACKET'), _KeySpec('BACKSLASH', 1.2),
    ],
    [
      _KeySpec('CAPS', 1.75), _KeySpec('A'), _KeySpec('S'), _KeySpec('D'), _KeySpec('F'), _KeySpec('G'), _KeySpec('H'), _KeySpec('J'), _KeySpec('K'), _KeySpec('L'), _KeySpec('SEMICOLON'), _KeySpec('QUOTE'), _KeySpec('ENTER', 1.95),
    ],
    [
      _KeySpec('SHIFT', 2.15, modifier: true), _KeySpec('Z'), _KeySpec('X'), _KeySpec('C'), _KeySpec('V'), _KeySpec('B'), _KeySpec('N'), _KeySpec('M'), _KeySpec('COMMA'), _KeySpec('PERIOD'), _KeySpec('SLASH'), _KeySpec('SHIFT', 2.15, modifier: true),
    ],
  ];

  bool get _ruActive {
    final layout = layouts.where((x) => x.id == activeLayoutId).firstOrNull;
    return layout?.code.toUpperCase() == 'RU';
  }

  @override
  Widget build(BuildContext context) {
    final currentLayout = layouts.where((x) => x.id == activeLayoutId).firstOrNull;
    return Container(
      color: const Color(0xff111315),
      padding: const EdgeInsets.fromLTRB(7, 4, 7, 6),
      child: Column(children: [
        for (final row in _rows)
          Expanded(child: Row(children: [for (final spec in row) Expanded(flex: (spec.flex * 100).round(), child: _key(spec))])),
        Expanded(
          child: Row(children: [
            Expanded(flex: 120, child: _key(const _KeySpec('CTRL', 1.2, modifier: true))),
            Expanded(flex: 90, child: _key(const _KeySpec('FN', .9, modifier: true))),
            Expanded(flex: 105, child: _key(const _KeySpec('WIN', 1.05, modifier: true))),
            Expanded(flex: 110, child: _key(const _KeySpec('ALT', 1.1, modifier: true))),
            Expanded(flex: 520, child: _key(const _KeySpec('SPACE', 5.2), customLabel: '')),
            Expanded(flex: 110, child: _key(const _KeySpec('ALT', 1.1, modifier: true))),
            Expanded(flex: 120, child: _key(const _KeySpec('CTRL', 1.2, modifier: true))),
            Expanded(
              flex: 150,
              child: Padding(
                padding: const EdgeInsets.all(2.2),
                child: Material(
                  color: v12Panel2,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6), side: const BorderSide(color: v12Border)),
                  child: PopupMenuButton<String>(
                    tooltip: 'Раскладка Windows',
                    color: v12Panel2,
                    initialValue: activeLayoutId.isEmpty ? null : activeLayoutId,
                    onSelected: onLayoutSelected,
                    itemBuilder: (_) => [for (final layout in layouts) PopupMenuItem(value: layout.id, child: Text(layout.label, style: const TextStyle(color: Colors.white)))],
                    child: Center(child: Text(currentLayout?.code ?? 'KB', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 11))),
                  ),
                ),
              ),
            ),
            Expanded(flex: 90, child: _key(const _KeySpec('HOME', .9))),
            Expanded(flex: 90, child: _key(const _KeySpec('UP', .9))),
            Expanded(flex: 90, child: _key(const _KeySpec('PAGEUP', .9))),
            Expanded(flex: 90, child: _key(const _KeySpec('LEFT', .9))),
            Expanded(flex: 90, child: _key(const _KeySpec('DOWN', .9))),
            Expanded(flex: 90, child: _key(const _KeySpec('RIGHT', .9))),
            Expanded(flex: 90, child: _key(const _KeySpec('END', .9))),
          ]),
        ),
      ]),
    );
  }

  Widget _key(_KeySpec spec, {String? customLabel}) {
    final active = activeModifiers.contains(spec.key);
    final primary = customLabel ?? _label(spec.key);
    final secondary = _secondary(spec.key);
    return Padding(
      padding: const EdgeInsets.all(2.2),
      child: Material(
        color: active ? const Color(0xff264e73) : v12Panel2,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6), side: BorderSide(color: active ? v12Blue : v12Border)),
        child: InkWell(
          borderRadius: BorderRadius.circular(6),
          onTap: () => onKey(spec.key, modifier: spec.modifier),
          child: Center(
            child: secondary == null
                ? Text(primary, maxLines: 1, overflow: TextOverflow.fade, style: TextStyle(fontSize: primary.length > 5 ? 8.5 : 11.5, color: Colors.white, fontWeight: active ? FontWeight.w700 : FontWeight.w500))
                : Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                    Text(_ruActive ? secondary : primary, style: const TextStyle(color: Colors.white, fontSize: 11.5, fontWeight: FontWeight.w600, height: 1)),
                    const SizedBox(height: 1),
                    Text(_ruActive ? primary : secondary, style: const TextStyle(color: v12Muted, fontSize: 7.5, height: 1)),
                  ]),
          ),
        ),
      ),
    );
  }

  String? _secondary(String key) => _ru[key];

  String _label(String key) => switch (key) {
        'BACKSPACE' => '⌫', 'ENTER' => 'Enter', 'SHIFT' => 'Shift', 'CTRL' => 'Ctrl', 'ALT' => 'Alt', 'TAB' => 'Tab', 'DELETE' => 'Del',
        'LEFT' => '←', 'RIGHT' => '→', 'UP' => '↑', 'DOWN' => '↓', 'ESC' => 'Esc', 'SPACE' => '', 'WIN' => '⊞', 'CAPS' => 'Caps',
        'LBRACKET' => '[', 'RBRACKET' => ']', 'BACKSLASH' => '\\', 'SEMICOLON' => ';', 'QUOTE' => "'", 'COMMA' => ',', 'PERIOD' => '.', 'SLASH' => '/',
        'MINUS' => '-', 'PLUS' => '+', 'PAGEUP' => 'Pg↑', 'PAGEDOWN' => 'Pg↓', _ => key,
      };
}

class _KeySpec {
  final String key;
  final double flex;
  final bool modifier;
  const _KeySpec(this.key, [this.flex = 1, this.modifier = false]);
}

extension _FirstOrNullV12<T> on Iterable<T> {
  T? get firstOrNull => isEmpty ? null : first;
}

class PhysicalKeyMapper {
  static String? token(PhysicalKeyboardKey key) {
    const letters = <PhysicalKeyboardKey, String>{
      PhysicalKeyboardKey.keyA:'A', PhysicalKeyboardKey.keyB:'B', PhysicalKeyboardKey.keyC:'C', PhysicalKeyboardKey.keyD:'D', PhysicalKeyboardKey.keyE:'E', PhysicalKeyboardKey.keyF:'F', PhysicalKeyboardKey.keyG:'G', PhysicalKeyboardKey.keyH:'H', PhysicalKeyboardKey.keyI:'I', PhysicalKeyboardKey.keyJ:'J', PhysicalKeyboardKey.keyK:'K', PhysicalKeyboardKey.keyL:'L', PhysicalKeyboardKey.keyM:'M', PhysicalKeyboardKey.keyN:'N', PhysicalKeyboardKey.keyO:'O', PhysicalKeyboardKey.keyP:'P', PhysicalKeyboardKey.keyQ:'Q', PhysicalKeyboardKey.keyR:'R', PhysicalKeyboardKey.keyS:'S', PhysicalKeyboardKey.keyT:'T', PhysicalKeyboardKey.keyU:'U', PhysicalKeyboardKey.keyV:'V', PhysicalKeyboardKey.keyW:'W', PhysicalKeyboardKey.keyX:'X', PhysicalKeyboardKey.keyY:'Y', PhysicalKeyboardKey.keyZ:'Z',
    };
    final letter = letters[key];
    if (letter != null) return letter;
    const digits = <PhysicalKeyboardKey, String>{
      PhysicalKeyboardKey.digit0:'0', PhysicalKeyboardKey.digit1:'1', PhysicalKeyboardKey.digit2:'2', PhysicalKeyboardKey.digit3:'3', PhysicalKeyboardKey.digit4:'4', PhysicalKeyboardKey.digit5:'5', PhysicalKeyboardKey.digit6:'6', PhysicalKeyboardKey.digit7:'7', PhysicalKeyboardKey.digit8:'8', PhysicalKeyboardKey.digit9:'9',
    };
    final digit = digits[key];
    if (digit != null) return digit;
    if (key == PhysicalKeyboardKey.shiftLeft || key == PhysicalKeyboardKey.shiftRight) return 'SHIFT';
    if (key == PhysicalKeyboardKey.controlLeft || key == PhysicalKeyboardKey.controlRight) return 'CTRL';
    if (key == PhysicalKeyboardKey.altLeft || key == PhysicalKeyboardKey.altRight) return 'ALT';
    if (key == PhysicalKeyboardKey.metaLeft || key == PhysicalKeyboardKey.metaRight) return 'WIN';
    if (key == PhysicalKeyboardKey.tab) return 'TAB';
    if (key == PhysicalKeyboardKey.enter) return 'ENTER';
    if (key == PhysicalKeyboardKey.escape) return 'ESC';
    if (key == PhysicalKeyboardKey.space) return 'SPACE';
    if (key == PhysicalKeyboardKey.backspace) return 'BACKSPACE';
    if (key == PhysicalKeyboardKey.delete) return 'DELETE';
    if (key == PhysicalKeyboardKey.insert) return 'INSERT';
    if (key == PhysicalKeyboardKey.home) return 'HOME';
    if (key == PhysicalKeyboardKey.end) return 'END';
    if (key == PhysicalKeyboardKey.pageUp) return 'PAGEUP';
    if (key == PhysicalKeyboardKey.pageDown) return 'PAGEDOWN';
    if (key == PhysicalKeyboardKey.arrowLeft) return 'LEFT';
    if (key == PhysicalKeyboardKey.arrowRight) return 'RIGHT';
    if (key == PhysicalKeyboardKey.arrowUp) return 'UP';
    if (key == PhysicalKeyboardKey.arrowDown) return 'DOWN';
    if (key == PhysicalKeyboardKey.capsLock) return 'CAPS';
    if (key == PhysicalKeyboardKey.minus) return 'MINUS';
    if (key == PhysicalKeyboardKey.equal) return 'PLUS';
    if (key == PhysicalKeyboardKey.bracketLeft) return 'LBRACKET';
    if (key == PhysicalKeyboardKey.bracketRight) return 'RBRACKET';
    if (key == PhysicalKeyboardKey.backslash) return 'BACKSLASH';
    if (key == PhysicalKeyboardKey.semicolon) return 'SEMICOLON';
    if (key == PhysicalKeyboardKey.quote) return 'QUOTE';
    if (key == PhysicalKeyboardKey.comma) return 'COMMA';
    if (key == PhysicalKeyboardKey.period) return 'PERIOD';
    if (key == PhysicalKeyboardKey.slash) return 'SLASH';
    return null;
  }
}
