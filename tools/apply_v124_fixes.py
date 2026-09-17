from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)


def replace_between(text: str, start_marker: str, end_marker: str, replacement: str, label: str) -> str:
    start = text.find(start_marker)
    if start < 0:
        raise RuntimeError(f"{label}: start marker not found")
    end = text.find(end_marker, start)
    if end < 0:
        raise RuntimeError(f"{label}: end marker not found")
    return text[:start] + replacement + text[end:]


def insert_before_once(text: str, marker: str, insertion: str, label: str) -> str:
    count = text.count(marker)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one marker, got {count}")
    return text.replace(marker, insertion + marker, 1)


def patch_windows() -> None:
    path = ROOT / "src/windows/MacroPadRemote/MainWindow.xaml.cs"
    text = path.read_text(encoding="utf-8")

    marker = '            if (messageType == "setKeyboardLayout" && root.TryGetProperty("layoutId", out var layoutIdProp))'
    insertion = r'''            if (messageType == "textInput" && root.TryGetProperty("text", out var textProp))
            {
                var value = textProp.GetString() ?? "";
                if (!string.IsNullOrEmpty(value))
                    await Dispatcher.InvokeAsync(() => SendText(value));
                return;
            }

'''
    text = insert_before_once(text, marker, insertion, "unicode text input protocol")

    path.write_text(text, encoding="utf-8")
    print(f"Applied v1.2.4 Windows fixes: {path}")


def patch_workspace() -> None:
    path = ROOT / "src/mobile/macropad_mobile/lib/v12_workspace.dart"
    text = path.read_text(encoding="utf-8")

    # The profile rail is dragged by the workspace itself in v1.2.4. Remove the
    # old long-press dock menu so it cannot steal the long-press gesture.
    text = replace_between(
        text,
        "  Future<void> _showDockMenu(BuildContext context) async {",
        "\n  @override\n  Widget build(BuildContext context) {",
        "",
        "remove old profile rail dock menu",
    )

    old_extent = r'''    final requestedListExtent = !_vertical && widget.horizontalExtent != null ? widget.horizontalExtent! - arrowExtent * 2 : null;
    final listExtent = requestedListExtent == null
        ? itemExtent * 4
        : requestedListExtent.clamp(itemExtent * 2, 2000.0).toDouble();
    final selectedColor = Color.lerp(v12Bg, Colors.white, .20)!;'''
    new_extent = r'''    final requestedListExtent = !_vertical && widget.horizontalExtent != null ? widget.horizontalExtent! - arrowExtent * 2 : null;
    final listExtent = requestedListExtent == null
        ? itemExtent * 4
        : (requestedListExtent < itemExtent * 2 ? itemExtent * 2 : requestedListExtent).toDouble();
    final contentExtent = widget.items.length * itemExtent;
    final centerPadding = !_vertical && listExtent > contentExtent ? (listExtent - contentExtent) / 2 : 0.0;
    final selectedColor = Color.lerp(v12Bg, Colors.white, .20)!;'''
    text = replace_once(text, old_extent, new_extent, "full width centered profile rail")

    text = replace_once(
        text,
        r'''            physics: const BouncingScrollPhysics(parent: AlwaysScrollableScrollPhysics()),
            itemExtent: itemExtent,''',
        r'''            physics: const BouncingScrollPhysics(parent: AlwaysScrollableScrollPhysics()),
            padding: _vertical || centerPadding <= 0 ? EdgeInsets.zero : EdgeInsets.symmetric(horizontal: centerPadding),
            itemExtent: itemExtent,''',
        "center profile icons in horizontal rail",
    )

    start = r'''    return GestureDetector(
      onLongPress: widget.dockLocked ? null : () => _showDockMenu(context),'''
    end = "\n  }\n}\n\nclass NexoTabletKeyboard"
    replacement = r'''    final bottomDock = widget.dock == ProfileDockSide.bottom;
    return Material(
      color: const Color(0xee1d1f21),
      elevation: bottomDock ? 0 : 6,
      borderRadius: bottomDock ? BorderRadius.zero : BorderRadius.circular(11),
      child: Container(
        decoration: bottomDock
            ? null
            : BoxDecoration(
                border: Border.all(color: v12Border),
                borderRadius: BorderRadius.circular(11),
              ),
        child: content,
      ),
    );'''
    text = replace_between(text, start, end, replacement, "flat bottom profile rail")

    path.write_text(text, encoding="utf-8")
    print(f"Applied v1.2.4 workspace fixes: {path}")


def patch_mobile() -> None:
    path = ROOT / "src/mobile/macropad_mobile/lib/main.dart"
    text = path.read_text(encoding="utf-8")

    text = replace_once(
        text,
        "  Offset _profileMoveDelta = Offset.zero;\n  Offset _navMoveDelta = Offset.zero;\n",
        "",
        "remove obsolete pan accumulators",
    )

    # Printable screen-keyboard characters must be sent as Unicode text. Hotkeys
    # remain hotkeys when Ctrl/Alt/Win are active or for service keys.
    start = "  Future<void> _virtualKey(String key, {bool modifier = false}) async {"
    end = "\n  Future<void> _connect() async {"
    replacement = r'''  String? _printableKeyboardText(String key, bool shift) {
    final ru = _activeLanguageCode.toUpperCase().startsWith('RU');

    const enLetters = <String, String>{
      'A':'a','B':'b','C':'c','D':'d','E':'e','F':'f','G':'g','H':'h','I':'i','J':'j','K':'k','L':'l','M':'m',
      'N':'n','O':'o','P':'p','Q':'q','R':'r','S':'s','T':'t','U':'u','V':'v','W':'w','X':'x','Y':'y','Z':'z',
    };
    const ruLetters = <String, String>{
      'GRAVE':'ё','Q':'й','W':'ц','E':'у','R':'к','T':'е','Y':'н','U':'г','I':'ш','O':'щ','P':'з',
      'LBRACKET':'х','RBRACKET':'ъ','A':'ф','S':'ы','D':'в','F':'а','G':'п','H':'р','J':'о','K':'л','L':'д',
      'SEMICOLON':'ж','QUOTE':'э','Z':'я','X':'ч','C':'с','V':'м','B':'и','N':'т','M':'ь','COMMA':'б','PERIOD':'ю',
    };

    final letter = ru ? ruLetters[key] : enLetters[key];
    if (letter != null) return shift ? letter.toUpperCase() : letter;

    if (key.length == 1 && key.codeUnitAt(0) >= 0x30 && key.codeUnitAt(0) <= 0x39) {
      if (!shift) return key;
      if (ru) {
        const shiftedRu = <String, String>{'1':'!','2':'"','3':'№','4':';','5':'%','6':':','7':'?','8':'*','9':'(','0':')'};
        return shiftedRu[key] ?? key;
      }
      const shiftedEn = <String, String>{'1':'!','2':'@','3':'#','4':'\$','5':'%','6':'^','7':'&','8':'*','9':'(','0':')'};
      return shiftedEn[key] ?? key;
    }

    if (key == 'SPACE') return ' ';
    if (ru) {
      return switch (key) {
        'MINUS' => shift ? '_' : '-',
        'EQUALS' => shift ? '+' : '=',
        'BACKSLASH' => shift ? '/' : '\\',
        'SLASH' => shift ? ',' : '.',
        _ => null,
      };
    }
    return switch (key) {
      'GRAVE' => shift ? '~' : '`',
      'MINUS' => shift ? '_' : '-',
      'EQUALS' => shift ? '+' : '=',
      'LBRACKET' => shift ? '{' : '[',
      'RBRACKET' => shift ? '}' : ']',
      'BACKSLASH' => shift ? '|' : '\\',
      'SEMICOLON' => shift ? ':' : ';',
      'QUOTE' => shift ? '"' : "'",
      'COMMA' => shift ? '<' : ',',
      'PERIOD' => shift ? '>' : '.',
      'SLASH' => shift ? '?' : '/',
      _ => null,
    };
  }

  Future<void> _virtualKey(String key, {bool modifier = false}) async {
    if (modifier) {
      setState(() {
        if (_keyboardModifiers.contains(key)) {
          _keyboardModifiers.remove(key);
        } else {
          _keyboardModifiers.add(key);
        }
      });
      await HapticFeedback.selectionClick();
      return;
    }

    final ctrl = _keyboardModifiers.contains('CTRL');
    final alt = _keyboardModifiers.contains('ALT');
    final win = _keyboardModifiers.contains('WIN');
    final shift = _keyboardModifiers.contains('SHIFT');
    final printable = !ctrl && !alt && !win ? _printableKeyboardText(key, shift) : null;

    await HapticFeedback.lightImpact();
    if (printable != null) {
      await widget.transport.send({'type': 'textInput', 'text': printable});
      return;
    }

    final mods = <String>[];
    for (final candidate in const ['CTRL', 'ALT', 'SHIFT', 'WIN']) {
      if (_keyboardModifiers.contains(candidate)) mods.add(candidate);
    }
    await _sendHotkey([...mods, key].join('+'));
  }

'''
    text = replace_between(text, start, end, replacement, "screen keyboard printable input")

    # Server-side revocation must always leave the remote workspace and return to
    # the first connection/device page, regardless of drawer/history state.
    start = "      if (json['type'] == 'deviceForgotten') {"
    end = "      if (json['type'] == 'paired') {"
    replacement = r'''      if (json['type'] == 'deviceForgotten') {
        _remoteRevoked = true;
        _resumeReconnectPending = false;
        final revokedServerId = (json['serverId'] ?? serverId).toString();
        if (revokedServerId.isNotEmpty) await DeviceStore.remove(revokedServerId);
        final currentSubscription = subscription;
        subscription = null;
        try { await currentSubscription?.cancel(); } catch (_) {}
        try { await widget.transport.close(); } catch (_) {}
        if (mounted) {
          Navigator.of(context, rootNavigator: true).popUntil((route) => route.isFirst);
        }
        return;
      }
'''
    text = replace_between(text, start, end, replacement, "force navigation after PC unlink")

    # The visible line below the workspace/page selector is never rendered.
    text = replace_once(
        text,
        "      decoration: const BoxDecoration(color: mpPanel, border: Border(bottom: BorderSide(color: mpBorder))),",
        "      decoration: const BoxDecoration(color: mpPanel),",
        "hide workspace boundary line",
    )

    workspace_start = "  ProfileDockSide _dockFromDrag(Offset delta, ProfileDockSide current) {"
    workspace_end = "  Widget _drawer({required bool compact}) {"
    workspace = r'''  ProfileDockSide _nearestDock(Offset point, Size size) {
    final left = point.dx.abs();
    final right = (size.width - point.dx).abs();
    final top = point.dy.abs();
    final bottom = (size.height - point.dy).abs();
    final nearest = [left, right, top, bottom].reduce((a, b) => a < b ? a : b);
    if (nearest == left) return ProfileDockSide.left;
    if (nearest == right) return ProfileDockSide.right;
    if (nearest == top) return ProfileDockSide.top;
    return ProfileDockSide.bottom;
  }

  double _dockOffsetFromPoint(ProfileDockSide side, Offset point, Size size) {
    if (side == ProfileDockSide.left || side == ProfileDockSide.right) {
      return (point.dy / size.height).clamp(.08, .92).toDouble();
    }
    return (point.dx / size.width).clamp(.08, .92).toDouble();
  }

  Offset _dropPoint(DraggableDetails details, Size size) {
    final raw = details.offset + const Offset(58, 18);
    return Offset(
      raw.dx.clamp(0.0, size.width).toDouble(),
      raw.dy.clamp(0.0, size.height).toDouble(),
    );
  }

  void _finishProfileDrag(DraggableDetails details) {
    if (controlsLocked) return;
    final size = MediaQuery.sizeOf(context);
    final point = _dropPoint(details, size);
    final next = _nearestDock(point, size);
    setState(() {
      profileDock = next;
      profileDockOffset = next == ProfileDockSide.bottom ? .5 : _dockOffsetFromPoint(next, point, size);
    });
    unawaited(_saveWorkspaceUi());
  }

  void _finishNavDrag(DraggableDetails details) {
    if (controlsLocked) return;
    final size = MediaQuery.sizeOf(context);
    final point = _dropPoint(details, size);
    final next = _nearestDock(point, size);
    setState(() {
      navDock = next;
      navDockOffset = next == ProfileDockSide.bottom ? .5 : _dockOffsetFromPoint(next, point, size);
    });
    unawaited(_saveWorkspaceUi());
  }

  Widget _dragFeedback(String label, IconData icon) => Material(
        color: const Color(0xee24272a),
        borderRadius: BorderRadius.circular(9),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            Icon(icon, size: 17, color: Colors.white),
            const SizedBox(width: 7),
            Text(label, style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w600)),
          ]),
        ),
      );

  Widget _profileDragSurface(Widget child) {
    if (controlsLocked) return child;
    return LongPressDraggable<String>(
      data: 'profiles',
      delay: const Duration(milliseconds: 450),
      dragAnchorStrategy: pointerDragAnchorStrategy,
      onDragStarted: HapticFeedback.mediumImpact,
      onDragEnd: _finishProfileDrag,
      feedback: _dragFeedback('Профили', Icons.view_carousel_outlined),
      childWhenDragging: const SizedBox.shrink(),
      child: child,
    );
  }

  Widget _navDragSurface(Widget child) {
    if (controlsLocked) return child;
    return LongPressDraggable<String>(
      data: 'deck_multi',
      delay: const Duration(milliseconds: 450),
      dragAnchorStrategy: pointerDragAnchorStrategy,
      onDragStarted: HapticFeedback.mediumImpact,
      onDragEnd: _finishNavDrag,
      feedback: _dragFeedback('DECK / Multi.', Icons.space_dashboard_outlined),
      childWhenDragging: const SizedBox.shrink(),
      child: child,
    );
  }

  Widget _invisibleResizeZone({
    required double value,
    required double min,
    required double max,
    required ValueChanged<double> onChanged,
  }) {
    if (controlsLocked) return const SizedBox.shrink();
    return Positioned(
      left: 0,
      right: 0,
      top: 0,
      height: 8,
      child: GestureDetector(
        behavior: HitTestBehavior.translucent,
        onVerticalDragUpdate: (details) => onChanged((value - details.delta.dy).clamp(min, max).toDouble()),
        onVerticalDragEnd: (_) => unawaited(_saveWorkspaceUi()),
        child: const SizedBox.expand(),
      ),
    );
  }

  Alignment _dockAlignment(ProfileDockSide side, double offset) {
    final axis = offset.clamp(.08, .92) * 2 - 1;
    return switch (side) {
      ProfileDockSide.left => Alignment(-1, axis),
      ProfileDockSide.right => Alignment(1, axis),
      ProfileDockSide.top => Alignment(axis, -1),
      ProfileDockSide.bottom => Alignment(axis, 1),
    };
  }

  Offset _handleTranslation(ProfileDockSide side, bool panelVisible, double extent) {
    if (!panelVisible) return Offset.zero;
    return switch (side) {
      ProfileDockSide.left => Offset(extent, 0),
      ProfileDockSide.right => Offset(-extent, 0),
      ProfileDockSide.top => Offset(0, extent),
      ProfileDockSide.bottom => Offset(0, -extent),
    };
  }

  Widget _edgePosition({
    required Widget child,
    required ProfileDockSide side,
    required double offset,
    Offset translation = Offset.zero,
  }) =>
      Positioned.fill(
        child: Padding(
          padding: const EdgeInsets.all(4),
          child: Align(
            alignment: _dockAlignment(side, offset),
            child: Transform.translate(offset: translation, child: child),
          ),
        ),
      );

  Widget _workspaceBody(List<Widget> pages, bool compact) {
    final tablet = widget.formFactor == ClientFormFactor.tablet;
    if (!tablet && !compact) return pages[tab];

    final keyboardCapability = tablet && !externalKeyboardConnected && tab == 0;
    final keyboardShown = keyboardCapability && tabletKeyboardVisible;
    final bottomProfile = profileDock == ProfileDockSide.bottom && profileRailVisible;
    final bottomNav = navDock == ProfileDockSide.bottom && bottomNavVisible;

    final content = Column(children: [
      Expanded(child: pages[tab]),
      if (bottomProfile) _bottomProfilePanel(),
      if (bottomNav) _bottomModePanel(),
      if (keyboardShown) _bottomKeyboardPanel(),
    ]);
    return _controlOverlay(content, showKeyboard: keyboardCapability);
  }

  Widget _controlOverlay(Widget child, {required bool showKeyboard}) {
    return Stack(children: [
      Positioned.fill(child: child),
      if (profileRailVisible && profileDock != ProfileDockSide.bottom)
        _positionProfileRail(_profileDragSurface(_profileRail())),
      if (profileDock != ProfileDockSide.bottom)
        _positionProfileRailHandle(_profileRailSideHandle()),
      if (bottomNavVisible && navDock != ProfileDockSide.bottom)
        _positionNavPanel(_navDragSurface(_modeSwitcher(vertical: navDock == ProfileDockSide.left || navDock == ProfileDockSide.right))),
      if (navDock != ProfileDockSide.bottom)
        _positionNavHandle(_navSideHandle()),
      if (showKeyboard || profileDock == ProfileDockSide.bottom || navDock == ProfileDockSide.bottom)
        Positioned(
          left: 0,
          right: 0,
          bottom: 2,
          child: Center(child: _bottomControlCluster(showKeyboard: showKeyboard)),
        ),
    ]);
  }

  Widget _profileRail({double? horizontalExtent}) => NexoProfileRail(
        items: [for (final item in profiles) ProfileRailItem(id: item.id, icon: item.icon)],
        activeId: _pendingProfileId.isNotEmpty ? _pendingProfileId : (profile?.id ?? ''),
        dock: profileDock,
        onSelected: (id) { if (id != profile?.id) unawaited(_switchProfile(id)); },
        onToggle: _toggleProfileRail,
        onDockChanged: _setProfileDock,
        dockLocked: controlsLocked,
        bottomExtent: profileBottomHeight,
        horizontalExtent: horizontalExtent,
      );

  Widget _bottomProfilePanel() {
    final panel = SizedBox(
      width: double.infinity,
      height: profileBottomHeight,
      child: Stack(children: [
        Positioned.fill(
          child: LayoutBuilder(
            builder: (_, constraints) => SizedBox(
              width: constraints.maxWidth,
              child: _profileRail(horizontalExtent: constraints.maxWidth),
            ),
          ),
        ),
        _invisibleResizeZone(
          value: profileBottomHeight,
          min: 42,
          max: 96,
          onChanged: (value) => setState(() => profileBottomHeight = value),
        ),
      ]),
    );
    return _profileDragSurface(panel);
  }

  Widget _bottomModePanel() {
    final panel = SizedBox(
      width: double.infinity,
      height: navBottomHeight,
      child: Stack(children: [
        Positioned.fill(child: Center(child: _modeSwitcher(vertical: false))),
        _invisibleResizeZone(
          value: navBottomHeight,
          min: 40,
          max: 104,
          onChanged: (value) => setState(() => navBottomHeight = value),
        ),
      ]),
    );
    return _navDragSurface(panel);
  }

  Widget _bottomKeyboardPanel() => SizedBox(
        width: double.infinity,
        height: tabletKeyboardHeight,
        child: Stack(children: [
          Positioned.fill(
            child: _TabletRemoteKeyboard(
              onKey: _virtualKey,
              onLanguage: _selectKeyboardLayout,
              activeModifiers: _keyboardModifiers,
              languageCode: _activeLanguageCode,
            ),
          ),
          _invisibleResizeZone(
            value: tabletKeyboardHeight,
            min: 170,
            max: 430,
            onChanged: (value) => setState(() => tabletKeyboardHeight = value),
          ),
        ]),
      );

  Widget _positionProfileRail(Widget rail) => _edgePosition(
        child: rail,
        side: profileDock,
        offset: profileDockOffset,
      );

  Widget _positionProfileRailHandle(Widget handle) => _edgePosition(
        child: handle,
        side: profileDock,
        offset: profileDockOffset,
        translation: _handleTranslation(profileDock, profileRailVisible, 50),
      );

  Widget _positionNavPanel(Widget panel) => _edgePosition(
        child: panel,
        side: navDock,
        offset: navDockOffset,
      );

  Widget _positionNavHandle(Widget handle) => _edgePosition(
        child: handle,
        side: navDock,
        offset: navDockOffset,
        translation: _handleTranslation(navDock, bottomNavVisible, 54),
      );

  Widget _profileRailSideHandle() {
    final icon = switch (profileDock) {
      ProfileDockSide.left => profileRailVisible ? Icons.chevron_left : Icons.chevron_right,
      ProfileDockSide.right => profileRailVisible ? Icons.chevron_right : Icons.chevron_left,
      ProfileDockSide.top => profileRailVisible ? Icons.keyboard_arrow_up : Icons.keyboard_arrow_down,
      ProfileDockSide.bottom => profileRailVisible ? Icons.keyboard_arrow_down : Icons.keyboard_arrow_up,
    };
    return _movableHandle(
      tooltip: 'Профили: показать / скрыть',
      icon: icon,
      onTap: _toggleProfileRail,
    );
  }

  Widget _navSideHandle() {
    final icon = switch (navDock) {
      ProfileDockSide.left => bottomNavVisible ? Icons.chevron_left : Icons.chevron_right,
      ProfileDockSide.right => bottomNavVisible ? Icons.chevron_right : Icons.chevron_left,
      ProfileDockSide.top => bottomNavVisible ? Icons.keyboard_arrow_up : Icons.keyboard_arrow_down,
      ProfileDockSide.bottom => bottomNavVisible ? Icons.keyboard_arrow_down : Icons.keyboard_arrow_up,
    };
    return _movableHandle(
      tooltip: 'DECK / Multi.: показать / скрыть',
      icon: icon,
      onTap: _toggleBottomNav,
    );
  }

  Widget _movableHandle({
    required String tooltip,
    required IconData icon,
    required VoidCallback onTap,
  }) =>
      Tooltip(
        message: tooltip,
        child: Material(
          color: const Color(0xee24272a),
          borderRadius: BorderRadius.circular(8),
          child: InkWell(
            canRequestFocus: false,
            borderRadius: BorderRadius.circular(8),
            onTap: onTap,
            child: SizedBox(width: 30, height: 38, child: Icon(icon, size: 18, color: mpMuted)),
          ),
        ),
      );

  Widget _modeSwitcher({required bool vertical}) {
    final children = <Widget>[
      _modeButton(0, Icons.grid_view, 'DECK'),
      _modeButton(1, Icons.play_circle_outline, 'Multi.'),
    ];
    return Material(
      color: mpPanel,
      child: SizedBox(
        width: vertical ? 52 : 196,
        height: vertical ? 104 : double.infinity,
        child: Flex(direction: vertical ? Axis.vertical : Axis.horizontal, children: children),
      ),
    );
  }

  Widget _modeButton(int index, IconData icon, String label) => Expanded(
        child: InkWell(
          canRequestFocus: false,
          onTap: () => setState(() => tab = index),
          child: Container(
            decoration: BoxDecoration(
              color: tab == index ? mpHover : mpPanel,
              border: Border.all(color: tab == index ? mpBlue : mpBorder, width: tab == index ? 1.5 : 1),
            ),
            child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
              Icon(icon, size: 18, color: Colors.white),
              const SizedBox(height: 2),
              Text(label, style: const TextStyle(fontSize: 9, color: Colors.white)),
            ]),
          ),
        ),
      );

  Widget _bottomControlCluster({required bool showKeyboard}) {
    final includeProfiles = profileDock == ProfileDockSide.bottom;
    final includeNav = navDock == ProfileDockSide.bottom;
    final count = (showKeyboard ? 1 : 0) + (includeNav ? 1 : 0) + (includeProfiles ? 1 : 0);
    if (count == 0) return const SizedBox.shrink();
    return AnimatedContainer(
      duration: const Duration(milliseconds: 220),
      curve: Curves.easeOutCubic,
      width: count * 42.0,
      height: 27,
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        if (showKeyboard)
          Expanded(
            child: _tabletArrow(
              tooltip: tabletKeyboardVisible ? 'Скрыть клавиатуру' : 'Показать клавиатуру',
              icon: tabletKeyboardVisible ? Icons.keyboard_arrow_down : Icons.keyboard_arrow_up,
              onTap: _toggleTabletKeyboard,
            ),
          ),
        if (includeNav)
          Expanded(
            child: _tabletArrow(
              tooltip: bottomNavVisible ? 'Скрыть DECK / Multi.' : 'Показать DECK / Multi.',
              icon: bottomNavVisible ? Icons.keyboard_arrow_down : Icons.keyboard_arrow_up,
              onTap: _toggleBottomNav,
            ),
          ),
        if (includeProfiles)
          Expanded(
            child: _tabletArrow(
              tooltip: profileRailVisible ? 'Скрыть профили' : 'Показать профили',
              icon: profileRailVisible ? Icons.keyboard_arrow_down : Icons.keyboard_arrow_up,
              onTap: _toggleProfileRail,
            ),
          ),
      ]),
    );
  }

  Widget _tabletArrow({
    required String tooltip,
    required IconData icon,
    required VoidCallback onTap,
  }) =>
      Tooltip(
        message: tooltip,
        child: Material(
          color: const Color(0xdd24272a),
          borderRadius: BorderRadius.circular(7),
          child: InkWell(
            canRequestFocus: false,
            borderRadius: BorderRadius.circular(7),
            onTap: onTap,
            child: Center(child: Icon(icon, size: 20, color: const Color(0xffc5c9cc))),
          ),
        ),
      );

'''
    text = replace_between(text, workspace_start, workspace_end, workspace, "v1.2.4 bottom panels and long press docking")

    drawer_start = r'''                  const Padding(
                    padding: EdgeInsets.fromLTRB(16, 14, 16, 6),
                    child: Text('ДОПОЛНИТЕЛЬНЫЕ ПАНЕЛИ', style: TextStyle(color: mpMuted, fontSize: 10, letterSpacing: 1)),
                  ),'''
    drawer_end = r'''                  const Divider(height: 1),
                  const Padding(padding: EdgeInsets.fromLTRB(16, 14, 16, 6), child: Text('СМЕНИТЬ УСТРОЙСТВО', style: TextStyle(color: mpMuted, fontSize: 10, letterSpacing: 1))),'''
    drawer = r'''                  const Padding(
                    padding: EdgeInsets.fromLTRB(16, 14, 16, 6),
                    child: Text('ДОПОЛНИТЕЛЬНЫЕ ПАНЕЛИ', style: TextStyle(color: mpMuted, fontSize: 10, letterSpacing: 1)),
                  ),
                  SwitchListTile.adaptive(
                    dense: true,
                    value: profileRailVisible,
                    title: const Text('Панель профилей'),
                    subtitle: const Text('Включить / выключить панель выбора профиля', style: TextStyle(fontSize: 10, color: mpMuted)),
                    onChanged: (value) {
                      setState(() => profileRailVisible = value);
                      unawaited(_saveWorkspaceUi());
                    },
                  ),
                  SwitchListTile.adaptive(
                    dense: true,
                    value: bottomNavVisible,
                    title: const Text('Панель DECK / Multi.'),
                    subtitle: const Text('Включить / выключить панель режимов', style: TextStyle(fontSize: 10, color: mpMuted)),
                    onChanged: (value) {
                      setState(() => bottomNavVisible = value);
                      unawaited(_saveWorkspaceUi());
                    },
                  ),
                  if (widget.formFactor == ClientFormFactor.tablet)
                    SwitchListTile.adaptive(
                      dense: true,
                      value: tabletKeyboardVisible,
                      title: const Text('Экранная клавиатура'),
                      subtitle: const Text('Включить / выключить экранную клавиатуру', style: TextStyle(fontSize: 10, color: mpMuted)),
                      onChanged: externalKeyboardConnected
                          ? null
                          : (value) {
                              setState(() => tabletKeyboardVisible = value);
                              unawaited(_saveWorkspaceUi());
                            },
                    ),
'''
    text = replace_between(text, drawer_start, drawer_end, drawer, "independent additional panel switches")

    path.write_text(text, encoding="utf-8")
    print(f"Applied v1.2.4 mobile fixes: {path}")


def main() -> None:
    target = sys.argv[1] if len(sys.argv) > 1 else "all"
    if target in ("all", "windows"):
        patch_windows()
    if target in ("all", "mobile"):
        patch_workspace()
        patch_mobile()
    if target not in ("all", "windows", "mobile"):
        raise SystemExit("usage: apply_v124_fixes.py [all|windows|mobile]")


if __name__ == "__main__":
    main()
