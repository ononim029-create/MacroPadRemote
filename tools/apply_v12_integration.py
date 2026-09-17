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


def patch_workspace_helpers() -> None:
    path = ROOT / "src/mobile/macropad_mobile/lib/v12_workspace.dart"
    text = path.read_text(encoding="utf-8")

    text = replace_once(
        text,
        """  final ProfileDockSide profileDock;\n\n  const WorkspaceViewState({\n    required this.matrix,\n    required this.profileRailVisible,\n    required this.navVisible,\n    required this.keyboardVisible,\n    required this.keyboardHeight,\n    required this.profileDock,\n  });""",
        """  final ProfileDockSide profileDock;\n  final bool controlsLocked;\n\n  const WorkspaceViewState({\n    required this.matrix,\n    required this.profileRailVisible,\n    required this.navVisible,\n    required this.keyboardVisible,\n    required this.keyboardHeight,\n    required this.profileDock,\n    required this.controlsLocked,\n  });""",
        "workspace lock field",
    )
    text = replace_once(
        text,
        """        keyboardHeight: 250,\n        profileDock: ProfileDockSide.left,\n      );""",
        """        keyboardHeight: 250,\n        profileDock: ProfileDockSide.left,\n        controlsLocked: false,\n      );""",
        "workspace default lock",
    )
    text = replace_once(
        text,
        """      keyboardHeight: ((json['keyboardHeight'] as num?)?.toDouble() ?? 250).clamp(150.0, 430.0),\n      profileDock: dock,\n    );""",
        """      keyboardHeight: ((json['keyboardHeight'] as num?)?.toDouble() ?? 250).clamp(150.0, 430.0),\n      profileDock: dock,\n      controlsLocked: json['controlsLocked'] == true,\n    );""",
        "workspace load lock",
    )
    text = replace_once(
        text,
        """        'keyboardHeight': keyboardHeight,\n        'profileDock': profileDock.name,\n      };""",
        """        'keyboardHeight': keyboardHeight,\n        'profileDock': profileDock.name,\n        'controlsLocked': controlsLocked,\n      };""",
        "workspace save lock",
    )

    text = replace_once(
        text,
        """  final VoidCallback onToggle;\n  final ValueChanged<ProfileDockSide> onDockChanged;\n\n  const NexoProfileRail({""",
        """  final VoidCallback onToggle;\n  final ValueChanged<ProfileDockSide> onDockChanged;\n  final bool dockLocked;\n\n  const NexoProfileRail({""",
        "rail lock field",
    )
    text = replace_once(
        text,
        """    required this.onSelected,\n    required this.onToggle,\n    required this.onDockChanged,\n  });""",
        """    required this.onSelected,\n    required this.onToggle,\n    required this.onDockChanged,\n    this.dockLocked = false,\n  });""",
        "rail lock constructor",
    )
    text = replace_once(
        text,
        """      onLongPress: () => _showDockMenu(context),""",
        """      onLongPress: widget.dockLocked ? null : () => _showDockMenu(context),""",
        "rail disable docking",
    )

    path.write_text(text, encoding="utf-8")
    print(f"Integrated workspace helper: {path}")


def patch_mobile() -> None:
    path = ROOT / "src/mobile/macropad_mobile/lib/main.dart"
    text = path.read_text(encoding="utf-8")

    text = replace_once(
        text,
        "import 'package:flutter/services.dart';\n",
        "import 'package:flutter/services.dart';\n\nimport 'v12_workspace.dart';\n",
        "import workspace helpers",
    )

    text = replace_once(
        text,
        """  bool externalKeyboardConnected = false;\n  double tabletKeyboardHeight = 250;""",
        """  bool externalKeyboardConnected = false;\n  bool profileRailVisible = true;\n  ProfileDockSide profileDock = ProfileDockSide.left;\n  bool controlsLocked = false;\n  bool _deckFitMode = false;\n  Matrix4? _deckUserTransformBeforeFit;\n  bool _resumeReconnectPending = false;\n  double tabletKeyboardHeight = 250;""",
        "mobile v12 state fields",
    )

    text = replace_once(
        text,
        """    _connect();\n  }\n\n\n  Future<void> _refreshHardwareKeyboard() async {""",
        """    _connect();\n    unawaited(_loadWorkspaceUi());\n  }\n\n  String get _workspaceFormFactorKey => widget.formFactor == ClientFormFactor.tablet ? 'tablet' : 'phone';\n\n  Future<void> _loadWorkspaceUi() async {\n    final saved = await WorkspaceViewStore.load(serverId, _workspaceFormFactorKey);\n    if (!mounted) return;\n    setState(() {\n      profileRailVisible = saved.profileRailVisible;\n      bottomNavVisible = saved.navVisible;\n      tabletKeyboardVisible = saved.keyboardVisible;\n      tabletKeyboardHeight = saved.keyboardHeight;\n      profileDock = saved.profileDock;\n      controlsLocked = saved.controlsLocked;\n    });\n  }\n\n  Future<void> _saveWorkspaceUi() async {\n    await WorkspaceViewStore.save(\n      serverId,\n      _workspaceFormFactorKey,\n      WorkspaceViewState(\n        matrix: _deckTransform.value.storage.toList(growable: false),\n        profileRailVisible: profileRailVisible,\n        navVisible: bottomNavVisible,\n        keyboardVisible: tabletKeyboardVisible,\n        keyboardHeight: tabletKeyboardHeight,\n        profileDock: profileDock,\n        controlsLocked: controlsLocked,\n      ),\n    );\n  }\n\n  void _setProfileDock(ProfileDockSide side) {\n    if (controlsLocked || side == profileDock) return;\n    setState(() => profileDock = side);\n    unawaited(_saveWorkspaceUi());\n  }\n\n  void _toggleProfileRail() {\n    setState(() => profileRailVisible = !profileRailVisible);\n    unawaited(_saveWorkspaceUi());\n  }\n\n  void _toggleBottomNav() {\n    setState(() => bottomNavVisible = !bottomNavVisible);\n    unawaited(_saveWorkspaceUi());\n  }\n\n  void _toggleTabletKeyboard() {\n    setState(() => tabletKeyboardVisible = !tabletKeyboardVisible);\n    unawaited(_saveWorkspaceUi());\n  }\n\n  Future<void> _refreshHardwareKeyboard() async {""",
        "workspace ui load/save methods",
    )

    old_lifecycle = """  @override\n  void didChangeAppLifecycleState(AppLifecycleState state) {\n    if (state == AppLifecycleState.inactive || state == AppLifecycleState.paused || state == AppLifecycleState.detached) {\n      unawaited(_saveDeckView());\n    }\n  }"""
    new_lifecycle = """  @override\n  void didChangeAppLifecycleState(AppLifecycleState state) {\n    if (state == AppLifecycleState.inactive || state == AppLifecycleState.paused || state == AppLifecycleState.detached) {\n      unawaited(_saveDeckView());\n      unawaited(_saveWorkspaceUi());\n      if (state == AppLifecycleState.paused) _resumeReconnectPending = true;\n      return;\n    }\n    if (state == AppLifecycleState.resumed) {\n      _hardwareFocusNode.requestFocus();\n      final disconnected = connectionError != null || status == 'Отключено' || status == 'Ошибка связи' || status == 'Ошибка подключения';\n      if (_resumeReconnectPending && disconnected) {\n        _resumeReconnectPending = false;\n        unawaited(_connect());\n      } else {\n        _resumeReconnectPending = false;\n      }\n    }\n  }"""
    text = replace_once(text, old_lifecycle, new_lifecycle, "resume reconnect lifecycle")

    text = replace_once(
        text,
        """  Future<void> _connect() async {\n    if (mounted) setState(() { status = 'Подключение…'; connectionError = null; });\n    try {\n      await widget.transport.connect();\n      subscription = widget.transport.messages.listen(_onMessage, onError: (Object error) {\n        if (mounted) setState(() { status = 'Ошибка связи'; connectionError = _friendlyConnectionError(error); });\n      }, onDone: () {\n        if (mounted) setState(() => status = 'Отключено');\n      });""",
        """  Future<void> _connect() async {\n    if (mounted) setState(() { status = 'Подключение…'; connectionError = null; });\n    try {\n      await subscription?.cancel();\n      subscription = null;\n      await widget.transport.connect();\n      subscription = widget.transport.messages.listen(_onMessage, onError: (Object error) {\n        _resumeReconnectPending = true;\n        if (mounted) setState(() { status = 'Ошибка связи'; connectionError = _friendlyConnectionError(error); });\n      }, onDone: () {\n        _resumeReconnectPending = true;\n        if (mounted) setState(() => status = 'Отключено');\n      });""",
        "reconnect transport subscription",
    )
    text = replace_once(
        text,
        """      if (mounted) setState(() => status = widget.transport.label);\n    } catch (e) {""",
        """      _resumeReconnectPending = false;\n      if (mounted) setState(() => status = widget.transport.label);\n    } catch (e) {""",
        "clear reconnect state",
    )

    old_fit = """  void _fitDeck() {\n    _deckReturnController.stop();\n    _deckReturnAnimation = Matrix4Tween(begin: _deckTransform.value.clone(), end: Matrix4.identity())\n        .animate(CurvedAnimation(parent: _deckReturnController, curve: Curves.easeOutCubic));\n    _deckReturnController.forward(from: 0);\n  }"""
    new_fit = """  void _fitDeck() {\n    _deckReturnController.stop();\n    final begin = _deckTransform.value.clone();\n    late final Matrix4 target;\n    if (_deckFitMode) {\n      target = _deckUserTransformBeforeFit?.clone() ?? Matrix4.identity();\n      _deckFitMode = false;\n    } else {\n      _deckUserTransformBeforeFit = begin.clone();\n      target = Matrix4.identity();\n      _deckFitMode = true;\n    }\n    _deckReturnAnimation = Matrix4Tween(begin: begin, end: target)\n        .animate(CurvedAnimation(parent: _deckReturnController, curve: Curves.easeOutCubic));\n    _deckReturnController.forward(from: 0);\n  }"""
    text = replace_once(text, old_fit, new_fit, "toggle fit and previous view")

    text = replace_once(
        text,
        """            onInteractionEnd: (_) => unawaited(_saveDeckView()),\n            child: canvas,""",
        """            alignment: Alignment.center,\n            clipBehavior: Clip.none,\n            onInteractionStart: (_) {\n              if (_deckFitMode) {\n                _deckFitMode = false;\n                _deckUserTransformBeforeFit = null;\n              }\n            },\n            onInteractionEnd: (_) {\n              unawaited(_saveDeckView());\n              unawaited(_saveWorkspaceUi());\n            },\n            child: canvas,""",
        "center viewer and remember user interaction",
    )

    # Replace workspace area with profile rail overlay and a shared bottom control cluster.
    start_marker = "  Widget _workspaceBody(List<Widget> pages, bool compact) {"
    end_marker = "  Widget _drawer({required bool compact}) {"
    replacement = r'''  Widget _workspaceBody(List<Widget> pages, bool compact) {
    final tablet = widget.formFactor == ClientFormFactor.tablet;
    Widget content;
    if (tablet) {
      content = _tabletWorkspace(pages);
    } else if (!compact) {
      content = pages[tab];
    } else {
      content = Stack(children: [
        Positioned.fill(child: pages[tab]),
        AnimatedPositioned(
          duration: const Duration(milliseconds: 220),
          curve: Curves.easeOutCubic,
          left: 18,
          right: 18,
          bottom: bottomNavVisible ? 30 : -64,
          child: IgnorePointer(
            ignoring: !bottomNavVisible,
            child: ClipRRect(
              borderRadius: BorderRadius.circular(14),
              child: _SharpBottomNav(
                compact: true,
                selectedIndex: tab,
                onSelected: (value) => setState(() => tab = value),
                items: const [_SharpNavItem(Icons.grid_view, 'DECK'), _SharpNavItem(Icons.play_circle_outline, 'Multi.')],
              ),
            ),
          ),
        ),
        Positioned(left: 0, right: 0, bottom: 2, child: Center(child: _bottomControlCluster(showKeyboard: false))),
      ]);
    }

    final useRail = tablet || compact;
    return useRail ? _profileRailOverlay(content) : content;
  }

  Widget _profileRailOverlay(Widget child) {
    final rail = NexoProfileRail(
      items: [for (final item in profiles) ProfileRailItem(id: item.id, icon: item.icon)],
      activeId: profile?.id ?? '',
      dock: profileDock,
      onSelected: (id) { if (id != profile?.id) unawaited(_switchProfile(id)); },
      onToggle: _toggleProfileRail,
      onDockChanged: _setProfileDock,
      dockLocked: controlsLocked,
    );

    final handle = _profileRailSideHandle();
    return Stack(children: [
      Positioned.fill(child: child),
      if (profileRailVisible) _positionProfileRail(rail),
      if (profileDock != ProfileDockSide.bottom) _positionProfileRailHandle(handle),
    ]);
  }

  Widget _positionProfileRail(Widget rail) => switch (profileDock) {
        ProfileDockSide.left => Positioned(left: 7, top: 12, child: rail),
        ProfileDockSide.right => Positioned(right: 7, top: 12, child: rail),
        ProfileDockSide.top => Positioned(top: 7, left: 62, child: rail),
        ProfileDockSide.bottom => Positioned(bottom: 38, left: 62, child: rail),
      };

  Widget _positionProfileRailHandle(Widget handle) => switch (profileDock) {
        ProfileDockSide.left => Positioned(left: profileRailVisible ? 58 : 3, top: 96, child: handle),
        ProfileDockSide.right => Positioned(right: profileRailVisible ? 58 : 3, top: 96, child: handle),
        ProfileDockSide.top => Positioned(top: profileRailVisible ? 58 : 3, left: 92, child: handle),
        ProfileDockSide.bottom => Positioned(bottom: 3, left: 92, child: handle),
      };

  Widget _profileRailSideHandle() {
    final icon = switch (profileDock) {
      ProfileDockSide.left => profileRailVisible ? Icons.chevron_left : Icons.chevron_right,
      ProfileDockSide.right => profileRailVisible ? Icons.chevron_right : Icons.chevron_left,
      ProfileDockSide.top => profileRailVisible ? Icons.keyboard_arrow_up : Icons.keyboard_arrow_down,
      ProfileDockSide.bottom => profileRailVisible ? Icons.keyboard_arrow_down : Icons.keyboard_arrow_up,
    };
    return Material(
      color: const Color(0xdd24272a),
      borderRadius: BorderRadius.circular(9),
      child: InkWell(
        borderRadius: BorderRadius.circular(9),
        onTap: _toggleProfileRail,
        child: SizedBox(width: 27, height: 38, child: Icon(icon, size: 18, color: mpMuted)),
      ),
    );
  }

  Widget _tabletWorkspace(List<Widget> pages) {
    final keyboardCapability = !externalKeyboardConnected && tab == 0;
    final keyboardShown = keyboardCapability && tabletKeyboardVisible;
    return Column(children: [
      Expanded(child: pages[tab]),
      AnimatedSize(
        duration: const Duration(milliseconds: 220),
        curve: Curves.easeOutCubic,
        child: bottomNavVisible
            ? SizedBox(
                height: 48,
                child: _SharpBottomNav(
                  compact: true,
                  selectedIndex: tab,
                  onSelected: (value) => setState(() => tab = value),
                  items: const [_SharpNavItem(Icons.grid_view, 'DECK'), _SharpNavItem(Icons.play_circle_outline, 'Multi.')],
                ),
              )
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
                    onVerticalDragUpdate: controlsLocked
                        ? null
                        : (details) {
                            setState(() => tabletKeyboardHeight = (tabletKeyboardHeight - details.delta.dy).clamp(170.0, 430.0));
                          },
                    onVerticalDragEnd: controlsLocked ? null : (_) => unawaited(_saveWorkspaceUi()),
                    child: Container(
                      height: 18,
                      color: const Color(0xaa24272a),
                      alignment: Alignment.center,
                      child: Icon(controlsLocked ? Icons.lock_outline : Icons.drag_handle, size: 17, color: const Color(0xffb8bdc2)),
                    ),
                  ),
                  Expanded(child: _TabletRemoteKeyboard(onKey: _virtualKey, onLanguage: _selectKeyboardLayout, activeModifiers: _keyboardModifiers, languageCode: _activeLanguageCode)),
                ]),
              )
            : const SizedBox.shrink(),
      ),
      SizedBox(height: 31, child: Center(child: _bottomControlCluster(showKeyboard: keyboardCapability))),
    ]);
  }

  Widget _bottomControlCluster({required bool showKeyboard}) {
    final includeProfiles = profileDock == ProfileDockSide.bottom;
    final count = (showKeyboard ? 1 : 0) + 1 + (includeProfiles ? 1 : 0);
    return AnimatedContainer(
      duration: const Duration(milliseconds: 240),
      curve: Curves.easeOutCubic,
      width: count * 42.0 + (count - 1) * 7.0,
      height: 27,
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        if (showKeyboard) ...[
          Expanded(child: _tabletArrow(
            tooltip: tabletKeyboardVisible ? 'Скрыть клавиатуру' : 'Показать клавиатуру',
            icon: tabletKeyboardVisible ? Icons.keyboard_arrow_down : Icons.keyboard_arrow_up,
            onTap: _toggleTabletKeyboard,
          )),
          const SizedBox(width: 7),
        ],
        Expanded(child: _tabletArrow(
          tooltip: bottomNavVisible ? 'Скрыть DECK / Multi.' : 'Показать DECK / Multi.',
          icon: bottomNavVisible ? Icons.keyboard_arrow_down : Icons.keyboard_arrow_up,
          onTap: _toggleBottomNav,
        )),
        if (includeProfiles) ...[
          const SizedBox(width: 7),
          Expanded(child: _tabletArrow(
            tooltip: profileRailVisible ? 'Скрыть профили' : 'Показать профили',
            icon: profileRailVisible ? Icons.keyboard_arrow_down : Icons.keyboard_arrow_up,
            onTap: _toggleProfileRail,
          )),
        ],
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
      );

'''
    text = replace_between(text, start_marker, end_marker, replacement, "workspace/rail integration")

    # Drawer: render image/glyph profile icons and add the management-layout lock.
    text = replace_once(
        text,
        """                      leading: Text(item.icon.isEmpty ? '•' : item.icon, style: TextStyle(color: item.id == activeId ? mpBlue : Colors.white, fontWeight: FontWeight.bold)),""",
        """                      leading: ProfileIconView(value: item.icon, size: 24, color: item.id == activeId ? mpBlue : Colors.white),""",
        "drawer profile icons",
    )

    drawer_anchor = """                  const Divider(height: 1),\n                  const Padding(padding: EdgeInsets.fromLTRB(16, 14, 16, 6), child: Text('СМЕНИТЬ УСТРОЙСТВО', style: TextStyle(color: mpMuted, fontSize: 10, letterSpacing: 1))),"""
    drawer_insert = """                  const Divider(height: 1),\n                  CheckboxListTile(\n                    dense: true,\n                    value: controlsLocked,\n                    controlAffinity: ListTileControlAffinity.leading,\n                    title: const Text('Блокировка меню управления'),\n                    subtitle: const Text('Фиксирует положение профилей и DECK / Multi.; положение кнопки клавиатуры всегда фиксировано', style: TextStyle(fontSize: 10, color: mpMuted)),\n                    onChanged: (value) {\n                      setState(() => controlsLocked = value == true);\n                      unawaited(_saveWorkspaceUi());\n                    },\n                  ),\n                  const Divider(height: 1),\n                  const Padding(padding: EdgeInsets.fromLTRB(16, 14, 16, 6), child: Text('СМЕНИТЬ УСТРОЙСТВО', style: TextStyle(color: mpMuted, fontSize: 10, letterSpacing: 1))),"""
    text = replace_once(text, drawer_anchor, drawer_insert, "drawer controls lock")

    # Portrait phone keeps the normal bottom bar, but use the requested labels.
    text = text.replace("_SharpNavItem(Icons.grid_view, 'Deck'), _SharpNavItem(Icons.play_circle_outline, 'Media')", "_SharpNavItem(Icons.grid_view, 'DECK'), _SharpNavItem(Icons.play_circle_outline, 'Multi.')")

    # Direct QR entry for a hidden PC: QR already contains host/port/token.
    qr_marker = """  Future<void> _pairWifi(DiscoveredPc pc) async {"""
    qr_insert = """  Future<void> _connectByQrDirect() async {\n    final qr = await _scanQr();\n    if (!mounted || qr == null) return;\n    if (qr.transport == TransportKind.wifi) {\n      final host = qr.host?.trim() ?? '';\n      if (host.isEmpty) return _message('В QR-коде нет адреса скрытого ПК.');\n      final remote = WifiRemoteTransport(host: host, port: qr.port, clientId: clientId, pairToken: qr.token);\n      await _openRemote(remote, serverId: qr.serverId, serverName: 'NEXO PC', host: host, port: qr.port, transportName: 'wifi');\n      return;\n    }\n    if (transport != TransportKind.bluetooth) await _switchTransport(TransportKind.bluetooth);\n    _message('Для Bluetooth дождитесь появления ПК в списке и подтвердите привязку этим QR-кодом.');\n  }\n\n  Future<void> _pairWifi(DiscoveredPc pc) async {"""
    text = replace_once(text, qr_marker, qr_insert, "direct hidden pc qr")

    text = replace_once(
        text,
        """          IconButton(tooltip: 'Повернуть экран', onPressed: () => toggleScreenOrientation(context), icon: const Icon(Icons.screen_rotation)),\n          IconButton(tooltip: 'Настройки', onPressed: _showSettings, icon: const Icon(Icons.settings)),""",
        """          IconButton(tooltip: 'QR / скрытый ПК', onPressed: _connectByQrDirect, icon: const Icon(Icons.qr_code_scanner)),\n          IconButton(tooltip: 'Повернуть экран', onPressed: () => toggleScreenOrientation(context), icon: const Icon(Icons.screen_rotation)),\n          IconButton(tooltip: 'Настройки', onPressed: _showSettings, icon: const Icon(Icons.settings)),""",
        "connect page qr action",
    )

    text = replace_once(
        text,
        """  @override\n  void dispose() {\n    unawaited(_saveDeckView());""",
        """  @override\n  void dispose() {\n    unawaited(_saveDeckView());\n    unawaited(_saveWorkspaceUi());""",
        "persist workspace on dispose",
    )

    path.write_text(text, encoding="utf-8")
    print(f"Integrated mobile v1.2: {path}")


def patch_windows() -> None:
    path = ROOT / "src/windows/MacroPadRemote/MainWindow.xaml.cs"
    text = path.read_text(encoding="utf-8")

    # Start/stop context monitor for Windows keyboard layout + active application profiles.
    text = replace_once(
        text,
        """            await StartSelectedTransportAsync();\n            StartupStatus.Text = \"Готово\";""",
        """            await StartSelectedTransportAsync();\n            StartV12ContextMonitor();\n            StartupStatus.Text = \"Готово\";""",
        "start v12 context monitor",
    )
    text = replace_once(
        text,
        """        try { await StopAllTransportsAsync(); } catch { }\n        System.Windows.Application.Current.Shutdown();""",
        """        StopV12ContextMonitor();\n        try { await StopAllTransportsAsync(); } catch { }\n        System.Windows.Application.Current.Shutdown();""",
        "stop context monitor",
    )

    # New profiles are intentionally blank 3x3.
    default_profile_anchor = """    private static Profile DefaultProfile(string name, string icon)\n    {\n        var profile = new Profile { Name = name, Icon = icon };\n        var page = DefaultPage(\"Страница 1\");\n        profile.Pages.Add(page);\n        profile.ActivePageId = page.Id;\n        return profile;\n    }\n\n"""
    blank_profile = default_profile_anchor + """    private static Profile EmptyProfile(string name, string icon)\n    {\n        var profile = new Profile { Name = name, Icon = icon };\n        var page = new DeckPage { Name = \"Страница 1\", Rows = 3, Columns = 3 };\n        EnsureCapacity(page);\n        profile.Pages.Add(page);\n        profile.ActivePageId = page.Id;\n        return profile;\n    }\n\n"""
    text = replace_once(text, default_profile_anchor, blank_profile, "empty 3x3 profile helper")
    text = replace_once(
        text,
        """        var profile = DefaultProfile(name, name[..1].ToUpperInvariant());""",
        """        var profile = EmptyProfile(name, name[..1].ToUpperInvariant());""",
        "new profile uses empty 3x3",
    )

    # Extend profile context menu with icon and application binding.
    text = replace_once(
        text,
        """        menu.Items.Add(rename); menu.Items.Add(copy); menu.Items.Add(new Separator()); menu.Items.Add(delete);\n        button.ContextMenu = menu;""",
        """        menu.Items.Add(rename); menu.Items.Add(copy); menu.Items.Add(new Separator()); menu.Items.Add(delete);\n        AddV12ProfileMenuItems(menu, profile);\n        button.ContextMenu = menu;""",
        "profile icon/application menu",
    )

    # Privacy/availability controls in the existing connection window.
    settings_anchor = """        var qr = new Button { Content = \"Показать QR-код\", Height = 34, Margin = new Thickness(0,0,0,16) }; qr.Click += ShowQr_Click; root.Children.Add(qr);\n        root.Children.Add(new TextBlock { Text = \"Привязанные устройства\", FontSize = 16, FontWeight = FontWeights.SemiBold, Margin = new Thickness(0,4,0,8) });"""
    settings_insert = """        var qr = new Button { Content = \"Показать QR-код\", Height = 34, Margin = new Thickness(0,0,0,10) }; qr.Click += ShowQr_Click; root.Children.Add(qr);\n        var visibleToggle = new CheckBox { Content = \"Показывать этот ПК в локальной сети\", IsChecked = _state.Discoverable, Margin = new Thickness(0,4,0,4), Foreground = Brushes.White };\n        var onlineToggle = new CheckBox { Content = \"Разрешить подключения к этому ПК\", IsChecked = _state.AcceptConnections, Margin = new Thickness(0,4,0,12), Foreground = Brushes.White };\n        visibleToggle.Checked += async (_, _) => await SetLanDiscoverableAsync(true);\n        visibleToggle.Unchecked += async (_, _) => await SetLanDiscoverableAsync(false);\n        onlineToggle.Checked += async (_, _) => await SetConnectionsEnabledAsync(true);\n        onlineToggle.Unchecked += async (_, _) => await SetConnectionsEnabledAsync(false);\n        root.Children.Add(visibleToggle);\n        root.Children.Add(onlineToggle);\n        root.Children.Add(new TextBlock { Text = \"Если видимость выключена, уже привязанные устройства продолжают работать. Новый скрытый ПК можно подключить напрямую по QR. Если подключения выключены — NEXO отображается как не в сети.\", TextWrapping = TextWrapping.Wrap, Foreground = (Brush)FindResource(\"Muted\"), Margin = new Thickness(0,0,0,14) });\n        root.Children.Add(new TextBlock { Text = \"Привязанные устройства\", FontSize = 16, FontWeight = FontWeights.SemiBold, Margin = new Thickness(0,4,0,8) });"""
    text = replace_once(text, settings_anchor, settings_insert, "privacy settings ui")

    # Transport respects offline and hidden-discovery states.
    text = replace_once(
        text,
        """    private async Task StartSelectedTransportAsync()\n    {\n        if (SelectedTransport() == \"Bluetooth\")""",
        """    private async Task StartSelectedTransportAsync()\n    {\n        if (!_state.AcceptConnections)\n        {\n            DeviceStatus.Text = \"Устройство не в сети • подключения отключены\";\n            HeaderStatus.Text = \"Не в сети\";\n            HeaderDot.Foreground = (Brush)FindResource(\"Muted\");\n            SyncConnectionUi();\n            return;\n        }\n        if (SelectedTransport() == \"Bluetooth\")""",
        "offline transport guard",
    )
    text = replace_once(
        text,
        """        await app.StartAsync();\n        _server = app;\n        await _lanDiscovery.StartAsync();\n        DeviceStatus.Text = \"ПК виден в локальной сети • ожидается QR\";\n        HeaderStatus.Text = \"Wi‑Fi активен • требуется QR\";""",
        """        await app.StartAsync();\n        _server = app;\n        if (_state.Discoverable)\n            await _lanDiscovery.StartAsync();\n        else\n            await _lanDiscovery.StopAsync();\n        DeviceStatus.Text = _state.Discoverable ? \"ПК виден в локальной сети\" : \"ПК скрыт в локальной сети • подключение по QR доступно\";\n        HeaderStatus.Text = _state.Discoverable ? \"Wi‑Fi активен\" : \"Wi‑Fi активен • скрытый режим\";""",
        "hidden LAN discovery",
    )
    text = replace_once(
        text,
        """        if (!context.WebSockets.IsWebSocketRequest)\n        {\n            context.Response.StatusCode = 400;\n            return;\n        }""",
        """        if (!_state.AcceptConnections)\n        {\n            context.Response.StatusCode = 503;\n            return;\n        }\n        if (!context.WebSockets.IsWebSocketRequest)\n        {\n            context.Response.StatusCode = 400;\n            return;\n        }""",
        "reject when offline",
    )

    # More accurate status text for hidden/offline state.
    text = replace_once(
        text,
        """            ConnectionDetails.Text = _server is null\n                ? \"Wi‑Fi: запуск…\"\n                : $\"{LocalIp()}:{WebSocketPort} • устройства в сети видят этот ПК автоматически\";""",
        """            ConnectionDetails.Text = !_state.AcceptConnections\n                ? \"Wi‑Fi: подключения выключены\"\n                : _server is null\n                    ? \"Wi‑Fi: запуск…\"\n                    : _state.Discoverable\n                        ? $\"{LocalIp()}:{WebSocketPort} • ПК виден в локальной сети\"\n                        : $\"{LocalIp()}:{WebSocketPort} • скрытый режим • QR и ранее привязанные устройства работают\";""",
        "connection details hidden/offline",
    )

    # QR text now explicitly supports hidden direct connection.
    text = replace_once(
        text,
        """                \"Wi‑Fi: приложение на телефоне сначала обнаруживает этот ПК в той же сети. QR только подтверждает найденный ПК и передаёт одноразовый токен.\");""",
        """                \"Wi‑Fi: QR содержит прямой адрес этого ПК и одноразовый токен. Он работает и в скрытом режиме, когда ПК не публикуется в локальном поиске.\");""",
        "hidden pc qr caption",
    )

    # AppState/Profile persistence for privacy and automatic profiles.
    text = replace_once(
        text,
        """    public string Transport { get; set; } = \"Wifi\";\n    public List<Profile> Profiles { get; set; } = new();""",
        """    public string Transport { get; set; } = \"Wifi\";\n    public bool Discoverable { get; set; } = true;\n    public bool AcceptConnections { get; set; } = true;\n    public List<Profile> Profiles { get; set; } = new();""",
        "app state privacy fields",
    )
    text = replace_once(
        text,
        """    public string Description { get; set; } = \"\";\n    public string ActivePageId { get; set; } = \"\";""",
        """    public string Description { get; set; } = \"\";\n    public string BoundApplication { get; set; } = \"\";\n    public string BoundApplicationPath { get; set; } = \"\";\n    public string ActivePageId { get; set; } = \"\";""",
        "profile application binding fields",
    )

    path.write_text(text, encoding="utf-8")
    print(f"Integrated Windows v1.2: {path}")


def main() -> None:
    target = sys.argv[1] if len(sys.argv) > 1 else "all"
    if target in ("all", "mobile"):
        patch_workspace_helpers()
        patch_mobile()
    if target in ("all", "windows"):
        patch_windows()
    if target not in ("all", "mobile", "windows"):
        raise SystemExit("usage: apply_v12_integration.py [all|mobile|windows]")


if __name__ == "__main__":
    main()
