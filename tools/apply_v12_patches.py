from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)


def patch_mobile() -> None:
    path = ROOT / "src/mobile/macropad_mobile/lib/main.dart"
    text = path.read_text(encoding="utf-8")

    text = replace_once(
        text,
        "        dividerColor: mpBorder,\n        inputDecorationTheme:",
        "        dividerColor: mpBorder,\n        focusColor: Colors.transparent,\n        inputDecorationTheme:",
        "disable focus highlight",
    )

    old = """  static Future<void> remove(String serverId) async {
    final all = await load();
    all.remove(serverId);
    await saveAll(all);
  }
}

class ConnectPage extends StatefulWidget {"""
    new = """  static Future<void> remove(String serverId) async {
    final all = await load();
    all.remove(serverId);
    await saveAll(all);
  }
}

class MobileUiStore {
  static const FlutterSecureStorage _storage = FlutterSecureStorage();

  static String _deckKey(String serverId, String profileId, String pageId) =>
      'nexo_deck_view_v1_${serverId}_${profileId}_${pageId}';

  static Future<List<double>?> loadDeckMatrix(String serverId, String profileId, String pageId) async {
    try {
      final raw = await _storage.read(key: _deckKey(serverId, profileId, pageId));
      if (raw == null || raw.isEmpty) return null;
      final values = (jsonDecode(raw) as List).map((e) => (e as num).toDouble()).toList();
      return values.length == 16 ? values : null;
    } catch (_) {
      return null;
    }
  }

  static Future<void> saveDeckMatrix(String serverId, String profileId, String pageId, Matrix4 matrix) async {
    if (serverId.isEmpty || profileId.isEmpty || pageId.isEmpty) return;
    await _storage.write(key: _deckKey(serverId, profileId, pageId), value: jsonEncode(matrix.storage.toList()));
  }
}

class ConnectPage extends StatefulWidget {"""
    text = replace_once(text, old, new, "mobile UI persistence store")

    text = replace_once(
        text,
        "class _RemotePageState extends State<RemotePage> with SingleTickerProviderStateMixin {",
        "class _RemotePageState extends State<RemotePage> with SingleTickerProviderStateMixin, WidgetsBindingObserver {",
        "remote page lifecycle observer",
    )

    old = """  String serverId = '';
  String serverName = '';
  bool scaleLocked = false;"""
    new = """  String serverId = '';
  String serverName = '';
  List<KeyboardLayoutSnapshot> keyboardLayouts = const [];
  String activeKeyboardLayout = '';
  final FocusNode _hardwareFocusNode = FocusNode(debugLabel: 'NEXO hardware keyboard', skipTraversal: true);
  bool scaleLocked = false;"""
    text = replace_once(text, old, new, "keyboard layout state")

    old = """    serverId = widget.initialServerId;
    serverName = widget.initialServerName;
    _deckReturnController = AnimationController(vsync: this, duration: const Duration(milliseconds: 260))
      ..addListener(() { if (_deckReturnAnimation != null) _deckTransform.value = _deckReturnAnimation!.value; });
    if (widget.formFactor == ClientFormFactor.tablet) {"""
    new = """    serverId = widget.initialServerId;
    serverName = widget.initialServerName;
    WidgetsBinding.instance.addObserver(this);
    _deckReturnController = AnimationController(vsync: this, duration: const Duration(milliseconds: 260))
      ..addListener(() { if (_deckReturnAnimation != null) _deckTransform.value = _deckReturnAnimation!.value; })
      ..addStatusListener((state) { if (state == AnimationStatus.completed) unawaited(_saveDeckView()); });
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _hardwareFocusNode.requestFocus();
    });
    if (widget.formFactor == ClientFormFactor.tablet) {"""
    text = replace_once(text, old, new, "remote init persistence and focus")

    marker = """  Future<void> _virtualKey(String key, {bool modifier = false}) async {"""
    insert = """  Future<void> _saveDeckView() async {
    final p = profile;
    if (p == null || serverId.isEmpty) return;
    await MobileUiStore.saveDeckMatrix(serverId, p.id, p.pageId, _deckTransform.value);
  }

  Future<void> _restoreDeckView() async {
    final p = profile;
    if (p == null || serverId.isEmpty) return;
    final values = await MobileUiStore.loadDeckMatrix(serverId, p.id, p.pageId);
    if (!mounted || values == null) return;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      _deckReturnController.stop();
      _deckTransform.value = Matrix4.fromList(values);
    });
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.inactive || state == AppLifecycleState.paused || state == AppLifecycleState.detached) {
      unawaited(_saveDeckView());
    }
  }

  String? _physicalKeyToken(PhysicalKeyboardKey key) => switch (key) {
        PhysicalKeyboardKey.keyA => 'A', PhysicalKeyboardKey.keyB => 'B', PhysicalKeyboardKey.keyC => 'C',
        PhysicalKeyboardKey.keyD => 'D', PhysicalKeyboardKey.keyE => 'E', PhysicalKeyboardKey.keyF => 'F',
        PhysicalKeyboardKey.keyG => 'G', PhysicalKeyboardKey.keyH => 'H', PhysicalKeyboardKey.keyI => 'I',
        PhysicalKeyboardKey.keyJ => 'J', PhysicalKeyboardKey.keyK => 'K', PhysicalKeyboardKey.keyL => 'L',
        PhysicalKeyboardKey.keyM => 'M', PhysicalKeyboardKey.keyN => 'N', PhysicalKeyboardKey.keyO => 'O',
        PhysicalKeyboardKey.keyP => 'P', PhysicalKeyboardKey.keyQ => 'Q', PhysicalKeyboardKey.keyR => 'R',
        PhysicalKeyboardKey.keyS => 'S', PhysicalKeyboardKey.keyT => 'T', PhysicalKeyboardKey.keyU => 'U',
        PhysicalKeyboardKey.keyV => 'V', PhysicalKeyboardKey.keyW => 'W', PhysicalKeyboardKey.keyX => 'X',
        PhysicalKeyboardKey.keyY => 'Y', PhysicalKeyboardKey.keyZ => 'Z',
        PhysicalKeyboardKey.digit0 => '0', PhysicalKeyboardKey.digit1 => '1', PhysicalKeyboardKey.digit2 => '2',
        PhysicalKeyboardKey.digit3 => '3', PhysicalKeyboardKey.digit4 => '4', PhysicalKeyboardKey.digit5 => '5',
        PhysicalKeyboardKey.digit6 => '6', PhysicalKeyboardKey.digit7 => '7', PhysicalKeyboardKey.digit8 => '8', PhysicalKeyboardKey.digit9 => '9',
        PhysicalKeyboardKey.enter => 'ENTER', PhysicalKeyboardKey.escape => 'ESC', PhysicalKeyboardKey.backspace => 'BACKSPACE',
        PhysicalKeyboardKey.tab => 'TAB', PhysicalKeyboardKey.space => 'SPACE', PhysicalKeyboardKey.delete => 'DELETE',
        PhysicalKeyboardKey.insert => 'INSERT', PhysicalKeyboardKey.home => 'HOME', PhysicalKeyboardKey.end => 'END',
        PhysicalKeyboardKey.pageUp => 'PAGEUP', PhysicalKeyboardKey.pageDown => 'PAGEDOWN',
        PhysicalKeyboardKey.arrowLeft => 'LEFT', PhysicalKeyboardKey.arrowRight => 'RIGHT',
        PhysicalKeyboardKey.arrowUp => 'UP', PhysicalKeyboardKey.arrowDown => 'DOWN',
        PhysicalKeyboardKey.shiftLeft || PhysicalKeyboardKey.shiftRight => 'SHIFT',
        PhysicalKeyboardKey.controlLeft || PhysicalKeyboardKey.controlRight => 'CTRL',
        PhysicalKeyboardKey.altLeft || PhysicalKeyboardKey.altRight => 'ALT',
        PhysicalKeyboardKey.metaLeft || PhysicalKeyboardKey.metaRight => 'WIN',
        PhysicalKeyboardKey.capsLock => 'CAPSLOCK', PhysicalKeyboardKey.minus => 'MINUS', PhysicalKeyboardKey.equal => 'EQUALS',
        PhysicalKeyboardKey.bracketLeft => 'LBRACKET', PhysicalKeyboardKey.bracketRight => 'RBRACKET',
        PhysicalKeyboardKey.backslash => 'BACKSLASH', PhysicalKeyboardKey.semicolon => 'SEMICOLON',
        PhysicalKeyboardKey.quote => 'QUOTE', PhysicalKeyboardKey.comma => 'COMMA', PhysicalKeyboardKey.period => 'PERIOD',
        PhysicalKeyboardKey.slash => 'SLASH', PhysicalKeyboardKey.backquote => 'GRAVE',
        _ => null,
      };

  KeyEventResult _handleHardwareKeyEvent(FocusNode node, KeyEvent event) {
    if (widget.formFactor != ClientFormFactor.tablet) return KeyEventResult.ignored;
    final token = _physicalKeyToken(event.physicalKey);
    if (token == null) return KeyEventResult.ignored;
    if (!externalKeyboardConnected && mounted) {
      setState(() { externalKeyboardConnected = true; tabletKeyboardVisible = false; });
    }
    final down = event is KeyDownEvent || event is KeyRepeatEvent;
    unawaited(widget.transport.send({'type': 'keyEvent', 'key': token, 'down': down}));
    return KeyEventResult.handled;
  }

  Future<void> _selectKeyboardLayout() async {
    if (keyboardLayouts.isEmpty) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Windows не передал список раскладок.')));
      return;
    }
    final selected = await showModalBottomSheet<String>(
      context: context,
      backgroundColor: mpPanel,
      builder: (sheetContext) => SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          const Padding(padding: EdgeInsets.fromLTRB(18, 16, 18, 8), child: Align(alignment: Alignment.centerLeft, child: Text('Язык клавиатуры Windows', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w600)))),
          for (final layout in keyboardLayouts)
            ListTile(
              leading: Icon(layout.id == activeKeyboardLayout ? Icons.radio_button_checked : Icons.radio_button_off, color: layout.id == activeKeyboardLayout ? mpBlue : mpMuted),
              title: Text(layout.label),
              subtitle: Text(layout.code, style: const TextStyle(color: mpMuted, fontSize: 10)),
              onTap: () => Navigator.of(sheetContext).pop(layout.id),
            ),
        ]),
      ),
    );
    if (selected == null) return;
    setState(() => activeKeyboardLayout = selected);
    await HapticFeedback.selectionClick();
    await widget.transport.send({'type': 'setKeyboardLayout', 'layoutId': selected});
    _hardwareFocusNode.requestFocus();
  }

  String get _activeLanguageCode {
    for (final layout in keyboardLayouts) {
      if (layout.id == activeKeyboardLayout) return layout.code;
    }
    return keyboardLayouts.isNotEmpty ? keyboardLayouts.first.code : 'KB';
  }

  Future<void> _virtualKey(String key, {bool modifier = false}) async {"""
    text = replace_once(text, marker, insert, "hardware keyboard and language methods")

    text = replace_once(
        text,
        "    for (final candidate in const ['CTRL', 'ALT', 'SHIFT']) {",
        "    for (final candidate in const ['CTRL', 'ALT', 'SHIFT', 'WIN']) {",
        "support Windows modifier",
    )

    old = """        final summaries = ((json['profiles'] ?? const []) as List)
            .map((item) => WorkspaceProfileSummary.fromJson(Map<String, dynamic>.from(item as Map)))
            .toList();
        if (mounted) setState(() { profile = p; profiles = summaries; });"""
    new = """        final summaries = ((json['profiles'] ?? const []) as List)
            .map((item) => WorkspaceProfileSummary.fromJson(Map<String, dynamic>.from(item as Map)))
            .toList();
        final layouts = ((json['keyboardLayouts'] ?? const []) as List)
            .whereType<Map>()
            .map((item) => KeyboardLayoutSnapshot.fromJson(Map<String, dynamic>.from(item)))
            .toList();
        final activeLayout = '${json['activeKeyboardLayout'] ?? ''}';
        if (mounted) setState(() { profile = p; profiles = summaries; keyboardLayouts = layouts; activeKeyboardLayout = activeLayout; });
        await _restoreDeckView();"""
    text = replace_once(text, old, new, "receive Windows keyboard layouts")

    old = """  @override
  void dispose() {
    subscription?.cancel();
    _hardwareKeyboardTimer?.cancel();
    if (widget.formFactor == ClientFormFactor.tablet) _deviceChannel.setMethodCallHandler(null);
    _deckReturnController.dispose();
    _deckTransform.dispose();
    widget.transport.close();
    super.dispose();
  }"""
    new = """  @override
  void dispose() {
    unawaited(_saveDeckView());
    WidgetsBinding.instance.removeObserver(this);
    subscription?.cancel();
    _hardwareKeyboardTimer?.cancel();
    if (widget.formFactor == ClientFormFactor.tablet) _deviceChannel.setMethodCallHandler(null);
    _deckReturnController.dispose();
    _deckTransform.dispose();
    _hardwareFocusNode.dispose();
    widget.transport.close();
    super.dispose();
  }"""
    text = replace_once(text, old, new, "persist view on dispose")

    old = """  @override
  Widget build(BuildContext context) {
    final pages = <Widget>[deck(), media()];
    if (tab >= pages.length) tab = 0;
    final compact = widget.formFactor == ClientFormFactor.phone && MediaQuery.orientationOf(context) == Orientation.landscape;
    return PopScope(
      canPop: false,
      child: Scaffold(
        drawer: _drawer(compact: compact),
        appBar: AppBar(
          toolbarHeight: compact ? 38 : null,
          titleSpacing: compact ? 8 : null,
          title: Row(mainAxisSize: MainAxisSize.min, children: [MacroPadMark(size: compact ? 17 : 22), SizedBox(width: compact ? 6 : 9), Flexible(child: Text(profile?.name ?? 'NEXO', overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: compact ? 13 : null)))]),
          actions: [
            IconButton(tooltip: 'Повернуть экран', visualDensity: compact ? VisualDensity.compact : VisualDensity.standard, onPressed: () => toggleScreenOrientation(context), icon: Icon(Icons.screen_rotation, size: compact ? 19 : 23)),
            Padding(padding: EdgeInsets.only(right: compact ? 5 : 10), child: Center(child: Row(children: [Icon(Icons.circle, size: 7, color: connectionError == null && status != 'Отключено' ? mpGreen : mpMuted), const SizedBox(width: 5), if (!compact) Text(status, style: const TextStyle(fontSize: 11))]))),
          ],
        ),
        body: SafeArea(child: connectionError == null ? _workspaceBody(pages, compact) : _connectionErrorView()),
        bottomNavigationBar: connectionError == null && !compact ? _SharpBottomNav(compact: false, selectedIndex: tab, onSelected: (value) => setState(() => tab = value), items: const [_SharpNavItem(Icons.grid_view, 'Deck'), _SharpNavItem(Icons.play_circle_outline, 'Media')]) : null,
      ),
    );
  }"""
    new = """  @override
  Widget build(BuildContext context) {
    final pages = <Widget>[deck(), media()];
    if (tab >= pages.length) tab = 0;
    final compact = widget.formFactor == ClientFormFactor.phone && MediaQuery.orientationOf(context) == Orientation.landscape;
    final tablet = widget.formFactor == ClientFormFactor.tablet;
    return Focus(
      focusNode: _hardwareFocusNode,
      autofocus: true,
      descendantsAreFocusable: false,
      onKeyEvent: _handleHardwareKeyEvent,
      child: PopScope(
        canPop: false,
        child: Scaffold(
          drawer: _drawer(compact: compact),
          appBar: AppBar(
            toolbarHeight: compact ? 38 : null,
            titleSpacing: compact ? 8 : null,
            title: Row(mainAxisSize: MainAxisSize.min, children: [MacroPadMark(size: compact ? 17 : 22), SizedBox(width: compact ? 6 : 9), Flexible(child: Text(profile?.name ?? 'NEXO', overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: compact ? 13 : null)))]),
            actions: [
              IconButton(tooltip: 'Повернуть экран', visualDensity: compact ? VisualDensity.compact : VisualDensity.standard, onPressed: () => toggleScreenOrientation(context), icon: Icon(Icons.screen_rotation, size: compact ? 19 : 23)),
              Padding(padding: EdgeInsets.only(right: compact ? 5 : 10), child: Center(child: Row(children: [Icon(Icons.circle, size: 7, color: connectionError == null && status != 'Отключено' ? mpGreen : mpMuted), const SizedBox(width: 5), if (!compact) Text(status, style: const TextStyle(fontSize: 11))]))),
            ],
          ),
          body: SafeArea(child: connectionError == null ? _workspaceBody(pages, compact) : _connectionErrorView()),
          bottomNavigationBar: connectionError == null && !compact && !tablet ? _SharpBottomNav(compact: false, selectedIndex: tab, onSelected: (value) => setState(() => tab = value), items: const [_SharpNavItem(Icons.grid_view, 'Deck'), _SharpNavItem(Icons.play_circle_outline, 'Media')]) : null,
        ),
      ),
    );
  }"""
    text = replace_once(text, old, new, "hardware keyboard focus and tablet nav")

    old = """  Widget _tabletWorkspace(List<Widget> pages) {
    final showKeyboardCapability = !externalKeyboardConnected && tab == 0;
    return Column(children: [
      Expanded(child: pages[tab]),
      if (showKeyboardCapability && tabletKeyboardVisible)
        SizedBox(
          height: tabletKeyboardHeight,
          child: Column(children: [
            GestureDetector(
              behavior: HitTestBehavior.opaque,
              onVerticalDragUpdate: (details) => setState(() => tabletKeyboardHeight = (tabletKeyboardHeight - details.delta.dy).clamp(150.0, 430.0)),
              child: Container(
                height: 18,
                color: const Color(0xaa24272a),
                alignment: Alignment.center,
                child: const Icon(Icons.drag_handle, size: 17, color: Color(0xffb8bdc2)),
              ),
            ),
            Expanded(child: _TabletRemoteKeyboard(onKey: _virtualKey, activeModifiers: _keyboardModifiers)),
          ]),
        ),
      if (showKeyboardCapability)
        Center(
          child: Material(
            color: const Color(0x9924272a),
            borderRadius: BorderRadius.circular(12),
            child: InkWell(
              borderRadius: BorderRadius.circular(12),
              onTap: () => setState(() => tabletKeyboardVisible = !tabletKeyboardVisible),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 30, vertical: 2),
                child: Icon(tabletKeyboardVisible ? Icons.keyboard_arrow_down : Icons.keyboard_arrow_up, size: 20, color: const Color(0xffc5c9cc)),
              ),
            ),
          ),
        ),
    ]);
  }"""
    new = """  Widget _tabletWorkspace(List<Widget> pages) {
    final keyboardCapability = !externalKeyboardConnected && tab == 0;
    final keyboardShown = keyboardCapability && tabletKeyboardVisible;
    final bothHidden = !bottomNavVisible && !keyboardShown;
    return Column(children: [
      Expanded(child: pages[tab]),
      AnimatedSize(
        duration: const Duration(milliseconds: 220),
        curve: Curves.easeOutCubic,
        child: bottomNavVisible
            ? SizedBox(height: 48, child: _SharpBottomNav(compact: true, selectedIndex: tab, onSelected: (value) => setState(() => tab = value), items: const [_SharpNavItem(Icons.grid_view, 'Deck'), _SharpNavItem(Icons.play_circle_outline, 'Media')]))
            : const SizedBox.shrink(),
      ),
      AnimatedSize(
        duration: const Duration(milliseconds: 240),
        curve: Curves.easeOutCubic,
        child: keyboardShown
            ? SizedBox(
                height: tabletKeyboardHeight,
                child: Column(children: [
                  GestureDetector(
                    behavior: HitTestBehavior.opaque,
                    onVerticalDragUpdate: (details) => setState(() => tabletKeyboardHeight = (tabletKeyboardHeight - details.delta.dy).clamp(170.0, 430.0)),
                    child: Container(height: 18, color: const Color(0xaa24272a), alignment: Alignment.center, child: const Icon(Icons.drag_handle, size: 17, color: Color(0xffb8bdc2))),
                  ),
                  Expanded(child: _TabletRemoteKeyboard(onKey: _virtualKey, onLanguage: _selectKeyboardLayout, activeModifiers: _keyboardModifiers, languageCode: _activeLanguageCode)),
                ]),
              )
            : const SizedBox.shrink(),
      ),
      SizedBox(height: 31, child: Center(child: _tabletToggleCluster(keyboardCapability: keyboardCapability, bothHidden: bothHidden))),
    ]);
  }

  Widget _tabletToggleCluster({required bool keyboardCapability, required bool bothHidden}) {
    final width = keyboardCapability ? (bothHidden ? 106.0 : 82.0) : 42.0;
    return AnimatedContainer(
      duration: const Duration(milliseconds: 240),
      curve: Curves.easeOutCubic,
      width: width,
      height: 27,
      child: Row(children: [
        if (keyboardCapability)
          Expanded(child: _tabletArrow(
            tooltip: tabletKeyboardVisible ? 'Скрыть клавиатуру' : 'Показать клавиатуру',
            icon: tabletKeyboardVisible ? Icons.keyboard_arrow_down : Icons.keyboard_arrow_up,
            onTap: () => setState(() => tabletKeyboardVisible = !tabletKeyboardVisible),
          )),
        if (keyboardCapability) const SizedBox(width: 7),
        Expanded(child: _tabletArrow(
          tooltip: bottomNavVisible ? 'Скрыть меню' : 'Показать меню',
          icon: bottomNavVisible ? Icons.keyboard_arrow_down : Icons.keyboard_arrow_up,
          onTap: () => setState(() => bottomNavVisible = !bottomNavVisible),
        )),
      ]),
    );
  }

  Widget _tabletArrow({required String tooltip, required IconData icon, required VoidCallback onTap}) => Tooltip(
        message: tooltip,
        child: Material(
          color: const Color(0x9924272a),
          borderRadius: BorderRadius.circular(11),
          child: InkWell(
            borderRadius: BorderRadius.circular(11),
            onTap: onTap,
            child: Center(child: Icon(icon, size: 20, color: const Color(0xffc5c9cc))),
          ),
        ),
      );"""
    text = replace_once(text, old, new, "tablet collapsible panels")

    text = replace_once(
        text,
        "            minScale: .35, maxScale: 3.2, boundaryMargin: const EdgeInsets.all(500), constrained: false,\n            child: canvas,",
        "            minScale: .35, maxScale: 3.2, boundaryMargin: const EdgeInsets.all(500), constrained: false,\n            onInteractionEnd: (_) => unawaited(_saveDeckView()),\n            child: canvas,",
        "save deck view after gesture",
    )

    start = text.index("class _TabletRemoteKeyboard extends StatelessWidget {")
    end = text.index("\nclass _SharpNavItem {", start)
    keyboard = r'''class _KeyboardKeySpec {
  final String token;
  final String en;
  final String ru;
  final int flex;
  const _KeyboardKeySpec(this.token, this.en, {this.ru = '', this.flex = 10});
}

class _TabletRemoteKeyboard extends StatelessWidget {
  final Future<void> Function(String key, {bool modifier}) onKey;
  final Future<void> Function() onLanguage;
  final Set<String> activeModifiers;
  final String languageCode;
  const _TabletRemoteKeyboard({required this.onKey, required this.onLanguage, required this.activeModifiers, required this.languageCode});

  static const _rows = <List<_KeyboardKeySpec>>[
    [
      _KeyboardKeySpec('ESC','Esc',flex:13), _KeyboardKeySpec('GRAVE','` ~',ru:'Ё'),
      _KeyboardKeySpec('1','1'), _KeyboardKeySpec('2','2'), _KeyboardKeySpec('3','3'), _KeyboardKeySpec('4','4'), _KeyboardKeySpec('5','5'),
      _KeyboardKeySpec('6','6'), _KeyboardKeySpec('7','7'), _KeyboardKeySpec('8','8'), _KeyboardKeySpec('9','9'), _KeyboardKeySpec('0','0'),
      _KeyboardKeySpec('MINUS','- _'), _KeyboardKeySpec('EQUALS','= +'), _KeyboardKeySpec('BACKSPACE','⌫',flex:18),
    ],
    [
      _KeyboardKeySpec('TAB','Tab',flex:16), _KeyboardKeySpec('Q','Q',ru:'Й'), _KeyboardKeySpec('W','W',ru:'Ц'), _KeyboardKeySpec('E','E',ru:'У'),
      _KeyboardKeySpec('R','R',ru:'К'), _KeyboardKeySpec('T','T',ru:'Е'), _KeyboardKeySpec('Y','Y',ru:'Н'), _KeyboardKeySpec('U','U',ru:'Г'),
      _KeyboardKeySpec('I','I',ru:'Ш'), _KeyboardKeySpec('O','O',ru:'Щ'), _KeyboardKeySpec('P','P',ru:'З'),
      _KeyboardKeySpec('LBRACKET','[',ru:'Х'), _KeyboardKeySpec('RBRACKET',']',ru:'Ъ'), _KeyboardKeySpec('BACKSLASH','\\',flex:13),
    ],
    [
      _KeyboardKeySpec('CAPSLOCK','Caps',flex:19), _KeyboardKeySpec('A','A',ru:'Ф'), _KeyboardKeySpec('S','S',ru:'Ы'), _KeyboardKeySpec('D','D',ru:'В'),
      _KeyboardKeySpec('F','F',ru:'А'), _KeyboardKeySpec('G','G',ru:'П'), _KeyboardKeySpec('H','H',ru:'Р'), _KeyboardKeySpec('J','J',ru:'О'),
      _KeyboardKeySpec('K','K',ru:'Л'), _KeyboardKeySpec('L','L',ru:'Д'), _KeyboardKeySpec('SEMICOLON',';',ru:'Ж'), _KeyboardKeySpec('QUOTE',"'",ru:'Э'),
      _KeyboardKeySpec('ENTER','Enter',flex:22),
    ],
    [
      _KeyboardKeySpec('SHIFT','Shift',flex:24), _KeyboardKeySpec('Z','Z',ru:'Я'), _KeyboardKeySpec('X','X',ru:'Ч'), _KeyboardKeySpec('C','C',ru:'С'),
      _KeyboardKeySpec('V','V',ru:'М'), _KeyboardKeySpec('B','B',ru:'И'), _KeyboardKeySpec('N','N',ru:'Т'), _KeyboardKeySpec('M','M',ru:'Ь'),
      _KeyboardKeySpec('COMMA',',',ru:'Б'), _KeyboardKeySpec('PERIOD','.',ru:'Ю'), _KeyboardKeySpec('SLASH','/',ru:'.'), _KeyboardKeySpec('SHIFT','Shift',flex:24),
    ],
    [
      _KeyboardKeySpec('CTRL','Ctrl',flex:15), _KeyboardKeySpec('WIN','⊞',flex:13), _KeyboardKeySpec('ALT','Alt',flex:14),
      _KeyboardKeySpec('SPACE','',flex:62), _KeyboardKeySpec('LANG','🌐',flex:20), _KeyboardKeySpec('ALT','Alt',flex:14), _KeyboardKeySpec('CTRL','Ctrl',flex:15),
      _KeyboardKeySpec('HOME','Home',flex:15), _KeyboardKeySpec('PAGEUP','PgUp',flex:15), _KeyboardKeySpec('LEFT','←',flex:12),
      _KeyboardKeySpec('DOWN','↓',flex:12), _KeyboardKeySpec('UP','↑',flex:12), _KeyboardKeySpec('RIGHT','→',flex:12),
      _KeyboardKeySpec('END','End',flex:15), _KeyboardKeySpec('PAGEDOWN','PgDn',flex:15),
    ],
  ];

  bool _modifier(String token) => token == 'CTRL' || token == 'ALT' || token == 'SHIFT' || token == 'WIN';

  String _label(_KeyboardKeySpec spec) {
    if (spec.token == 'LANG') return '🌐 ${languageCode.toUpperCase()}';
    if (spec.token == 'SPACE') return '';
    if (spec.ru.isEmpty) return spec.en;
    final ruFirst = languageCode.toUpperCase() == 'RU';
    return ruFirst ? '${spec.ru}\n${spec.en}' : '${spec.en}\n${spec.ru}';
  }

  @override
  Widget build(BuildContext context) => Container(
        color: const Color(0xff111315),
        padding: const EdgeInsets.fromLTRB(7, 4, 7, 6),
        child: Column(children: [
          for (final row in _rows)
            Expanded(child: Row(children: [for (final spec in row) Expanded(flex: spec.flex, child: _key(spec))])),
        ]),
      );

  Widget _key(_KeyboardKeySpec spec) {
    final modifier = _modifier(spec.token);
    final active = activeModifiers.contains(spec.token);
    return Padding(
      padding: const EdgeInsets.all(2.2),
      child: Material(
        color: active ? const Color(0xff264e73) : mpPanel2,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6), side: BorderSide(color: active ? mpBlue : mpBorder)),
        child: InkWell(
          borderRadius: BorderRadius.circular(6),
          canRequestFocus: false,
          onTap: spec.token == 'LANG' ? onLanguage : () => onKey(spec.token, modifier: modifier),
          child: Center(
            child: spec.token == 'SPACE'
                ? const SizedBox.shrink()
                : Text(_label(spec), textAlign: TextAlign.center, maxLines: 2, overflow: TextOverflow.fade, style: TextStyle(fontSize: spec.flex <= 12 ? 9.5 : 10.5, height: .92, color: Colors.white, fontWeight: active ? FontWeight.w700 : FontWeight.w500)),
          ),
        ),
      ),
    );
  }
}
'''
    text = text[:start] + keyboard + text[end:]

    marker = """class PageSummary {"""
    insert = """class KeyboardLayoutSnapshot {
  final String id;
  final String label;
  final String code;
  const KeyboardLayoutSnapshot({required this.id, required this.label, required this.code});
  factory KeyboardLayoutSnapshot.fromJson(Map<String, dynamic> json) => KeyboardLayoutSnapshot(
        id: '${json['id'] ?? ''}',
        label: '${json['label'] ?? json['code'] ?? 'Keyboard'}',
        code: '${json['code'] ?? 'KB'}'.toUpperCase(),
      );
}

class PageSummary {"""
    text = replace_once(text, marker, insert, "keyboard layout snapshot model")

    path.write_text(text, encoding="utf-8")
    print(f"Patched mobile: {path}")


def patch_windows() -> None:
    path = ROOT / "src/windows/MacroPadRemote/MainWindow.xaml.cs"
    text = path.read_text(encoding="utf-8")

    old = """        if (_state.Profiles.Count == 0)
        {
            _state.Profiles.Add(DefaultProfile("Revit", "R"));
            _state.Profiles.Add(DefaultProfile("NanoCAD", "N"));
            _state.Profiles.Add(DefaultProfile("Рабочий стол", "▣"));
            _state.ActiveProfileId = _state.Profiles[0].Id;
        }"""
    new = """        // v1.2 removes the bundled application-specific profiles. Keep only a useful desktop profile.
        _state.Profiles.RemoveAll(p => string.Equals(p.Name, "Revit", StringComparison.OrdinalIgnoreCase)
            || string.Equals(p.Name, "NanoCAD", StringComparison.OrdinalIgnoreCase));
        if (_state.Profiles.Count == 0)
        {
            _state.Profiles.Add(DefaultProfile("Рабочий стол", "▣"));
            _state.ActiveProfileId = _state.Profiles[0].Id;
        }
        else if (!_state.Profiles.Any(p => p.Id == _state.ActiveProfileId))
        {
            _state.ActiveProfileId = _state.Profiles[0].Id;
        }"""
    text = replace_once(text, old, new, "remove bundled Revit and NanoCAD profiles")

    old = """        var defaults = new[]
        {
            new Tile { Title = "Сохранить", ActionType = "hotkey", Hotkey = "CTRL+S" },
            new Tile { Title = "Скриншот", ActionType = "hotkey", Hotkey = "WIN+SHIFT+S" },
            new Tile { Title = "Переключить окна", ActionType = "hotkey", Hotkey = "ALT+TAB" },
            new Tile { Title = "Браузер", ActionType = "url", ActionValue = "https://www.google.com" },
            new Tile { Title = "Назад", ActionType = "hotkey", Hotkey = "ESC" },
            new Tile { Title = "Воспроизведение", ActionType = "media", ActionValue = "MEDIA_PLAY" },
            new Tile { Title = "Выключить звук", ActionType = "media", ActionValue = "VOLUME_MUTE" },
            new Tile { Title = "Рабочий стол", ActionType = "hotkey", Hotkey = "WIN+D" },
            new Tile { Title = "Почта" }, new Tile { Title = "Калькулятор" }, new Tile { Title = "Открыть папку" }, new Tile()
        };"""
    new = """        var defaults = new[]
        {
            new Tile { Title = "Сохранить", ActionType = "hotkey", Hotkey = "CTRL+S" },
            new Tile { Title = "Копировать", ActionType = "hotkey", Hotkey = "CTRL+C" },
            new Tile { Title = "Вставить", ActionType = "hotkey", Hotkey = "CTRL+V" },
            new Tile { Title = "Отменить", ActionType = "hotkey", Hotkey = "CTRL+Z" },
            new Tile { Title = "Скриншот", ActionType = "hotkey", Hotkey = "WIN+SHIFT+S" },
            new Tile { Title = "Переключить окна", ActionType = "hotkey", Hotkey = "ALT+TAB" },
            new Tile { Title = "Рабочий стол", ActionType = "hotkey", Hotkey = "WIN+D" },
            new Tile { Title = "Проводник", ActionType = "hotkey", Hotkey = "WIN+E" },
            new Tile { Title = "Браузер", ActionType = "url", ActionValue = "https://www.google.com" },
            new Tile { Title = "Калькулятор", ActionType = "open", ActionValue = "calc.exe" },
            new Tile { Title = "Без звука", ActionType = "media", ActionValue = "VOLUME_MUTE" },
            new Tile { Title = "Play / Pause", ActionType = "media", ActionValue = "MEDIA_PLAY" }
        };"""
    text = replace_once(text, old, new, "desktop default actions")

    marker = """            if (messageType == "switchProfile" && root.TryGetProperty("profileId", out var profileIdProp))"""
    insert = """            if (messageType == "setKeyboardLayout" && root.TryGetProperty("layoutId", out var layoutIdProp))
            {
                var layoutId = layoutIdProp.GetString() ?? "";
                var changed = KeyboardLayoutService.SetActive(layoutId);
                Dispatcher.Invoke(() => DeviceStatus.Text = changed ? "Раскладка клавиатуры изменена с планшета" : "Не удалось изменить раскладку клавиатуры");
                if (changed)
                {
                    await Task.Delay(120);
                    await BroadcastSnapshotAsync();
                }
                return;
            }

            if (messageType == "keyEvent" && root.TryGetProperty("key", out var keyProp))
            {
                var token = keyProp.GetString() ?? "";
                var down = !root.TryGetProperty("down", out var downProp) || downProp.ValueKind != JsonValueKind.False;
                var vk = TokenToVk(token);
                if (vk != 0)
                    SendInputs(new[] { KeyInput(vk, !down) });
                return;
            }

            if (messageType == "switchProfile" && root.TryGetProperty("profileId", out var profileIdProp))"""
    text = replace_once(text, marker, insert, "keyboard protocol messages")

    old = """            profiles = _profiles.Select(p => new
            {
                id = p.Id,
                name = p.Name,
                icon = p.Icon,
                activePageId = p.ActivePageId,
                pages = p.Pages.Select(pg => new { id = pg.Id, name = pg.Name }).ToList()
            }).ToList()
        };"""
    new = """            profiles = _profiles.Select(p => new
            {
                id = p.Id,
                name = p.Name,
                icon = p.Icon,
                activePageId = p.ActivePageId,
                pages = p.Pages.Select(pg => new { id = pg.Id, name = pg.Name }).ToList()
            }).ToList(),
            keyboardLayouts = KeyboardLayoutService.GetLayouts(),
            activeKeyboardLayout = KeyboardLayoutService.GetActiveId()
        };"""
    text = replace_once(text, old, new, "snapshot keyboard layouts")

    old = """            "BACKSPACE" => 0x08, "DELETE" => 0x2E, "INSERT" => 0x2D, "HOME" => 0x24, "END" => 0x23,
            "LEFT" => 0x25, "UP" => 0x26, "RIGHT" => 0x27, "DOWN" => 0x28, "PAGEUP" => 0x21, "PAGEDOWN" => 0x22,
            "PLUS" or "+" => 0xBB, "MINUS" or "-" => 0xBD, "COMMA" => 0xBC, "PERIOD" or "DOT" => 0xBE,"""
    new = """            "BACKSPACE" => 0x08, "DELETE" => 0x2E, "INSERT" => 0x2D, "HOME" => 0x24, "END" => 0x23, "CAPSLOCK" => 0x14,
            "LEFT" => 0x25, "UP" => 0x26, "RIGHT" => 0x27, "DOWN" => 0x28, "PAGEUP" => 0x21, "PAGEDOWN" => 0x22,
            "SEMICOLON" => 0xBA, "PLUS" or "+" or "EQUALS" => 0xBB, "COMMA" => 0xBC, "MINUS" or "-" => 0xBD,
            "PERIOD" or "DOT" => 0xBE, "SLASH" => 0xBF, "GRAVE" => 0xC0, "LBRACKET" => 0xDB,
            "BACKSLASH" => 0xDC, "RBRACKET" => 0xDD, "QUOTE" => 0xDE,"""
    text = replace_once(text, old, new, "physical punctuation key mapping")

    path.write_text(text, encoding="utf-8")
    print(f"Patched Windows: {path}")


def main() -> None:
    target = sys.argv[1] if len(sys.argv) > 1 else "all"
    if target in ("all", "mobile"):
        patch_mobile()
    if target in ("all", "windows"):
        patch_windows()
    if target not in ("all", "mobile", "windows"):
        raise SystemExit("usage: apply_v12_patches.py [all|mobile|windows]")


if __name__ == "__main__":
    main()
