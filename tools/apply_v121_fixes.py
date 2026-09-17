from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, got {count}")
    return text.replace(old, new, 1)


def replace_between(text: str, start_marker: str, end_marker: str, replacement: str, label: str) -> str:
    start = text.find(start_marker)
    if start < 0:
        raise RuntimeError(f"{label}: start marker not found")
    end = text.find(end_marker, start)
    if end < 0:
        raise RuntimeError(f"{label}: end marker not found")
    return text[:start] + replacement + text[end:]


def patch_workspace_state() -> None:
    path = ROOT / "src/mobile/macropad_mobile/lib/v12_workspace.dart"
    text = path.read_text(encoding="utf-8")

    text = replace_once(
        text,
        """  final ProfileDockSide profileDock;\n  final bool controlsLocked;""",
        """  final ProfileDockSide profileDock;\n  final ProfileDockSide navDock;\n  final double profileBottomHeight;\n  final double navBottomHeight;\n  final bool controlsLocked;""",
        "workspace v121 fields",
    )
    text = replace_once(
        text,
        """    required this.profileDock,\n    required this.controlsLocked,""",
        """    required this.profileDock,\n    required this.navDock,\n    required this.profileBottomHeight,\n    required this.navBottomHeight,\n    required this.controlsLocked,""",
        "workspace v121 constructor",
    )
    text = replace_once(
        text,
        """        profileDock: ProfileDockSide.left,\n        controlsLocked: false,""",
        """        profileDock: ProfileDockSide.left,\n        navDock: ProfileDockSide.bottom,\n        profileBottomHeight: 52,\n        navBottomHeight: 48,\n        controlsLocked: false,""",
        "workspace v121 defaults",
    )
    text = replace_once(
        text,
        """    final dock = ProfileDockSide.values.firstWhere(\n      (x) => x.name == dockName,\n      orElse: () => ProfileDockSide.left,\n    );""",
        """    final dock = ProfileDockSide.values.firstWhere(\n      (x) => x.name == dockName,\n      orElse: () => ProfileDockSide.left,\n    );\n    final navDockName = '${json['navDock'] ?? 'bottom'}';\n    final navDock = ProfileDockSide.values.firstWhere(\n      (x) => x.name == navDockName,\n      orElse: () => ProfileDockSide.bottom,\n    );""",
        "workspace v121 load dock",
    )
    text = replace_once(
        text,
        """      profileDock: dock,\n      controlsLocked: json['controlsLocked'] == true,""",
        """      profileDock: dock,\n      navDock: navDock,\n      profileBottomHeight: ((json['profileBottomHeight'] as num?)?.toDouble() ?? 52).clamp(42.0, 96.0),\n      navBottomHeight: ((json['navBottomHeight'] as num?)?.toDouble() ?? 48).clamp(40.0, 104.0),\n      controlsLocked: json['controlsLocked'] == true,""",
        "workspace v121 load sizes",
    )
    text = replace_once(
        text,
        """        'profileDock': profileDock.name,\n        'controlsLocked': controlsLocked,""",
        """        'profileDock': profileDock.name,\n        'navDock': navDock.name,\n        'profileBottomHeight': profileBottomHeight,\n        'navBottomHeight': navBottomHeight,\n        'controlsLocked': controlsLocked,""",
        "workspace v121 save fields",
    )

    # Let the horizontal profile rail scale when it is docked at the bottom.
    text = replace_once(
        text,
        """  final bool dockLocked;\n\n  const NexoProfileRail({""",
        """  final bool dockLocked;\n  final double bottomExtent;\n\n  const NexoProfileRail({""",
        "profile rail bottom extent field",
    )
    text = replace_once(
        text,
        """    this.dockLocked = false,\n  });""",
        """    this.dockLocked = false,\n    this.bottomExtent = 48,\n  });""",
        "profile rail bottom extent constructor",
    )
    text = replace_once(
        text,
        """    const itemExtent = 44.0;\n    const arrowExtent = 24.0;\n    final listExtent = itemExtent * 4;""",
        """    final crossExtent = widget.dock == ProfileDockSide.bottom ? widget.bottomExtent.clamp(42.0, 96.0).toDouble() : 48.0;\n    final itemExtent = _vertical ? 44.0 : (crossExtent - 4).clamp(38.0, 82.0).toDouble();\n    const arrowExtent = 24.0;\n    final listExtent = itemExtent * 4;""",
        "profile rail dynamic extent",
    )
    text = replace_once(
        text,
        """          height: _vertical ? arrowExtent : 48,""",
        """          height: _vertical ? arrowExtent : crossExtent,""",
        "profile rail arrow height",
    )
    text = replace_once(
        text,
        """          height: _vertical ? listExtent : 48,""",
        """          height: _vertical ? listExtent : crossExtent,""",
        "profile rail list height",
    )
    text = replace_once(
        text,
        """                    child: Center(child: ProfileIconView(value: item.icon, size: 26, color: selected ? Colors.white : v12Text)),""",
        """                    child: Center(child: ProfileIconView(value: item.icon, size: _vertical ? 26 : (crossExtent - 18).clamp(22.0, 36.0).toDouble(), color: selected ? Colors.white : v12Text)),""",
        "profile rail icon size",
    )

    path.write_text(text, encoding="utf-8")
    print(f"Applied v1.2.1 workspace state: {path}")


def patch_mobile() -> None:
    path = ROOT / "src/mobile/macropad_mobile/lib/main.dart"
    text = path.read_text(encoding="utf-8")

    text = replace_once(
        text,
        """  ProfileDockSide profileDock = ProfileDockSide.left;\n  bool controlsLocked = false;""",
        """  ProfileDockSide profileDock = ProfileDockSide.left;\n  ProfileDockSide navDock = ProfileDockSide.bottom;\n  double profileBottomHeight = 52;\n  double navBottomHeight = 48;\n  Offset _profileMoveDelta = Offset.zero;\n  Offset _navMoveDelta = Offset.zero;\n  bool controlsLocked = false;""",
        "mobile v121 control state",
    )
    text = replace_once(
        text,
        """      profileDock = saved.profileDock;\n      controlsLocked = saved.controlsLocked;""",
        """      profileDock = saved.profileDock;\n      navDock = saved.navDock;\n      profileBottomHeight = saved.profileBottomHeight;\n      navBottomHeight = saved.navBottomHeight;\n      controlsLocked = saved.controlsLocked;""",
        "mobile v121 load controls",
    )
    text = replace_once(
        text,
        """        profileDock: profileDock,\n        controlsLocked: controlsLocked,""",
        """        profileDock: profileDock,\n        navDock: navDock,\n        profileBottomHeight: profileBottomHeight,\n        navBottomHeight: navBottomHeight,\n        controlsLocked: controlsLocked,""",
        "mobile v121 save controls",
    )

    # Native Android dispatchKeyEvent is authoritative for external keyboards.
    text = replace_once(
        text,
        """        if (call.method == 'hardwareKeyboardChanged') {\n          final connected = call.arguments == true;\n          if (mounted && connected != externalKeyboardConnected) {\n            setState(() { externalKeyboardConnected = connected; if (connected) tabletKeyboardVisible = false; });\n          }\n        }""",
        """        if (call.method == 'hardwareKeyboardChanged') {\n          final connected = call.arguments == true;\n          if (mounted && connected != externalKeyboardConnected) {\n            setState(() { externalKeyboardConnected = connected; if (connected) tabletKeyboardVisible = false; });\n          }\n        } else if (call.method == 'hardwareKeyEvent') {\n          final args = call.arguments;\n          if (args is Map) {\n            final token = '${args['key'] ?? ''}';\n            final down = args['down'] == true;\n            if (token.isNotEmpty) {\n              if (mounted && !externalKeyboardConnected) {\n                setState(() { externalKeyboardConnected = true; tabletKeyboardVisible = false; });\n              }\n              try { await widget.transport.send({'type': 'keyEvent', 'key': token, 'down': down}); } catch (_) {}\n            }\n          }\n        }""",
        "native hardware key event bridge",
    )

    # Replace v1.2 workspace implementation with v1.2.1 draggable/snap implementation.
    start_marker = "  Widget _workspaceBody(List<Widget> pages, bool compact) {"
    end_marker = "  Widget _drawer({required bool compact}) {"
    replacement = r'''  ProfileDockSide _dockFromDrag(Offset delta, ProfileDockSide current) {
    if (delta.distance < 18) return current;
    if (delta.dx.abs() > delta.dy.abs()) return delta.dx < 0 ? ProfileDockSide.left : ProfileDockSide.right;
    return delta.dy < 0 ? ProfileDockSide.top : ProfileDockSide.bottom;
  }

  void _profileDragUpdate(DragUpdateDetails details) {
    if (controlsLocked) return;
    _profileMoveDelta += details.delta;
  }

  void _profileDragEnd(DragEndDetails details) {
    if (controlsLocked) return;
    final next = _dockFromDrag(_profileMoveDelta, profileDock);
    _profileMoveDelta = Offset.zero;
    _setProfileDock(next);
  }

  void _navDragUpdate(DragUpdateDetails details) {
    if (controlsLocked) return;
    _navMoveDelta += details.delta;
  }

  void _navDragEnd(DragEndDetails details) {
    if (controlsLocked) return;
    final next = _dockFromDrag(_navMoveDelta, navDock);
    _navMoveDelta = Offset.zero;
    if (next == navDock) return;
    setState(() => navDock = next);
    unawaited(_saveWorkspaceUi());
  }

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
      SizedBox(height: 31, child: Center(child: _bottomControlCluster(showKeyboard: keyboardCapability))),
    ]);

    return _controlOverlay(content);
  }

  Widget _controlOverlay(Widget child) {
    return Stack(children: [
      Positioned.fill(child: child),
      if (profileRailVisible && profileDock != ProfileDockSide.bottom)
        _positionProfileRail(_profileRail()),
      if (profileDock != ProfileDockSide.bottom)
        _positionProfileRailHandle(_profileRailSideHandle()),
      if (bottomNavVisible && navDock != ProfileDockSide.bottom)
        _positionNavPanel(_modeSwitcher(vertical: navDock == ProfileDockSide.left || navDock == ProfileDockSide.right)),
      if (navDock != ProfileDockSide.bottom)
        _positionNavHandle(_navSideHandle()),
    ]);
  }

  Widget _profileRail() => NexoProfileRail(
        items: [for (final item in profiles) ProfileRailItem(id: item.id, icon: item.icon)],
        activeId: profile?.id ?? '',
        dock: profileDock,
        onSelected: (id) { if (id != profile?.id) unawaited(_switchProfile(id)); },
        onToggle: _toggleProfileRail,
        onDockChanged: _setProfileDock,
        dockLocked: controlsLocked,
        bottomExtent: profileBottomHeight,
      );

  Widget _bottomProfilePanel() => Column(mainAxisSize: MainAxisSize.min, children: [
        _bottomResizeHandle(
          value: profileBottomHeight,
          min: 42,
          max: 96,
          onChanged: (value) => setState(() => profileBottomHeight = value),
        ),
        SizedBox(height: profileBottomHeight, child: Align(alignment: Alignment.centerLeft, child: _profileRail())),
      ]);

  Widget _bottomModePanel() => Column(mainAxisSize: MainAxisSize.min, children: [
        _bottomResizeHandle(
          value: navBottomHeight,
          min: 40,
          max: 104,
          onChanged: (value) => setState(() => navBottomHeight = value),
        ),
        SizedBox(height: navBottomHeight, child: _modeSwitcher(vertical: false)),
      ]);

  Widget _bottomKeyboardPanel() => SizedBox(
        height: tabletKeyboardHeight,
        child: Column(children: [
          GestureDetector(
            behavior: HitTestBehavior.opaque,
            onVerticalDragUpdate: controlsLocked
                ? null
                : (details) => setState(() => tabletKeyboardHeight = (tabletKeyboardHeight - details.delta.dy).clamp(170.0, 430.0)),
            onVerticalDragEnd: controlsLocked ? null : (_) => unawaited(_saveWorkspaceUi()),
            child: Container(
              height: 18,
              color: const Color(0xff24272a),
              alignment: Alignment.center,
              child: Icon(controlsLocked ? Icons.lock_outline : Icons.drag_handle, size: 17, color: const Color(0xffb8bdc2)),
            ),
          ),
          Expanded(child: _TabletRemoteKeyboard(onKey: _virtualKey, onLanguage: _selectKeyboardLayout, activeModifiers: _keyboardModifiers, languageCode: _activeLanguageCode)),
        ]),
      );

  Widget _bottomResizeHandle({required double value, required double min, required double max, required ValueChanged<double> onChanged}) {
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onVerticalDragUpdate: controlsLocked
          ? null
          : (details) => onChanged((value - details.delta.dy).clamp(min, max).toDouble()),
      onVerticalDragEnd: controlsLocked ? null : (_) => unawaited(_saveWorkspaceUi()),
      child: Container(
        height: 12,
        color: const Color(0xff24272a),
        alignment: Alignment.center,
        child: Icon(controlsLocked ? Icons.lock_outline : Icons.drag_handle, size: 15, color: const Color(0xff9da3a8)),
      ),
    );
  }

  Widget _positionProfileRail(Widget rail) => switch (profileDock) {
        ProfileDockSide.left => Positioned(left: 0, top: 12, child: rail),
        ProfileDockSide.right => Positioned(right: 0, top: 12, child: rail),
        ProfileDockSide.top => Positioned(top: 0, left: 62, child: rail),
        ProfileDockSide.bottom => Positioned(bottom: 0, left: 62, child: rail),
      };

  Widget _positionProfileRailHandle(Widget handle) => switch (profileDock) {
        ProfileDockSide.left => Positioned(left: profileRailVisible ? 48 : 0, top: 96, child: handle),
        ProfileDockSide.right => Positioned(right: profileRailVisible ? 48 : 0, top: 96, child: handle),
        ProfileDockSide.top => Positioned(top: profileRailVisible ? 48 : 0, left: 92, child: handle),
        ProfileDockSide.bottom => Positioned(bottom: 0, left: 92, child: handle),
      };

  Widget _positionNavPanel(Widget panel) => switch (navDock) {
        ProfileDockSide.left => Positioned(left: 0, bottom: 54, child: panel),
        ProfileDockSide.right => Positioned(right: 0, bottom: 54, child: panel),
        ProfileDockSide.top => Positioned(top: 0, right: 62, child: panel),
        ProfileDockSide.bottom => Positioned(bottom: 0, right: 62, child: panel),
      };

  Widget _positionNavHandle(Widget handle) => switch (navDock) {
        ProfileDockSide.left => Positioned(left: bottomNavVisible ? 52 : 0, bottom: 90, child: handle),
        ProfileDockSide.right => Positioned(right: bottomNavVisible ? 52 : 0, bottom: 90, child: handle),
        ProfileDockSide.top => Positioned(top: bottomNavVisible ? 48 : 0, right: 92, child: handle),
        ProfileDockSide.bottom => Positioned(bottom: 0, right: 92, child: handle),
      };

  Widget _profileRailSideHandle() {
    final icon = switch (profileDock) {
      ProfileDockSide.left => profileRailVisible ? Icons.chevron_left : Icons.chevron_right,
      ProfileDockSide.right => profileRailVisible ? Icons.chevron_right : Icons.chevron_left,
      ProfileDockSide.top => profileRailVisible ? Icons.keyboard_arrow_up : Icons.keyboard_arrow_down,
      ProfileDockSide.bottom => profileRailVisible ? Icons.keyboard_arrow_down : Icons.keyboard_arrow_up,
    };
    return _movableHandle(
      tooltip: controlsLocked ? 'Панель профилей зафиксирована' : 'Профили: нажмите или перетащите',
      icon: icon,
      onTap: _toggleProfileRail,
      onPanUpdate: _profileDragUpdate,
      onPanEnd: _profileDragEnd,
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
      tooltip: controlsLocked ? 'DECK / Multi. зафиксировано' : 'DECK / Multi.: нажмите или перетащите',
      icon: icon,
      onTap: _toggleBottomNav,
      onPanUpdate: _navDragUpdate,
      onPanEnd: _navDragEnd,
    );
  }

  Widget _movableHandle({
    required String tooltip,
    required IconData icon,
    required VoidCallback onTap,
    required GestureDragUpdateCallback onPanUpdate,
    required GestureDragEndCallback onPanEnd,
  }) => Tooltip(
        message: tooltip,
        child: GestureDetector(
          behavior: HitTestBehavior.opaque,
          onPanUpdate: controlsLocked ? null : onPanUpdate,
          onPanEnd: controlsLocked ? null : onPanEnd,
          child: Material(
            color: const Color(0xee24272a),
            borderRadius: BorderRadius.circular(8),
            child: InkWell(
              canRequestFocus: false,
              borderRadius: BorderRadius.circular(8),
              onTap: onTap,
              child: SizedBox(width: 30, height: 38, child: Icon(controlsLocked ? Icons.lock_outline : icon, size: 18, color: mpMuted)),
            ),
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
          Expanded(child: _tabletArrow(
            tooltip: tabletKeyboardVisible ? 'Скрыть клавиатуру' : 'Показать клавиатуру',
            icon: tabletKeyboardVisible ? Icons.keyboard_arrow_down : Icons.keyboard_arrow_up,
            onTap: _toggleTabletKeyboard,
          )),
        if (includeNav)
          Expanded(child: GestureDetector(
            behavior: HitTestBehavior.opaque,
            onPanUpdate: controlsLocked ? null : _navDragUpdate,
            onPanEnd: controlsLocked ? null : _navDragEnd,
            child: _tabletArrow(
              tooltip: controlsLocked ? 'DECK / Multi. зафиксировано' : 'DECK / Multi.: нажмите или перетащите',
              icon: bottomNavVisible ? Icons.keyboard_arrow_down : Icons.keyboard_arrow_up,
              onTap: _toggleBottomNav,
            ),
          )),
        if (includeProfiles)
          Expanded(child: GestureDetector(
            behavior: HitTestBehavior.opaque,
            onPanUpdate: controlsLocked ? null : _profileDragUpdate,
            onPanEnd: controlsLocked ? null : _profileDragEnd,
            child: _tabletArrow(
              tooltip: controlsLocked ? 'Профили зафиксированы' : 'Профили: нажмите или перетащите',
              icon: profileRailVisible ? Icons.keyboard_arrow_down : Icons.keyboard_arrow_up,
              onTap: _toggleProfileRail,
            ),
          )),
      ]),
    );
  }

  Widget _tabletArrow({required String tooltip, required IconData icon, required VoidCallback onTap}) => Tooltip(
        message: tooltip,
        child: Material(
          color: const Color(0xff24272a),
          child: InkWell(
            canRequestFocus: false,
            onTap: onTap,
            child: Center(child: Icon(icon, size: 20, color: const Color(0xffc5c9cc))),
          ),
        ),
      );

'''
    text = replace_between(text, start_marker, end_marker, replacement, "v121 workspace controls")

    text = replace_once(
        text,
        """                    subtitle: const Text('Фиксирует положение профилей и DECK / Multi.; положение кнопки клавиатуры всегда фиксировано', style: TextStyle(fontSize: 10, color: mpMuted)),""",
        """                    subtitle: const Text('Блокирует перемещение и изменение размеров панелей профилей, DECK / Multi. и экранной клавиатуры', style: TextStyle(fontSize: 10, color: mpMuted)),""",
        "controls lock description",
    )

    path.write_text(text, encoding="utf-8")
    print(f"Applied v1.2.1 mobile fixes: {path}")


def main() -> None:
    target = sys.argv[1] if len(sys.argv) > 1 else "mobile"
    if target == "mobile":
        patch_workspace_state()
        patch_mobile()
    elif target != "none":
        raise SystemExit("usage: apply_v121_fixes.py [mobile]")


if __name__ == "__main__":
    main()
