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


def patch_windows() -> None:
    path = ROOT / "src/windows/MacroPadRemote/MainWindow.xaml.cs"
    text = path.read_text(encoding="utf-8")

    old_forget = """    private async Task ForgetTrustedClientAsync(TrustedClient device)
    {
        List<WebSocket> close = new();
        lock (_clients)
            foreach (var pair in _clientIds.Where(x => x.Value == device.Id).ToList()) close.Add(pair.Key);
        foreach (var socket in close)
            try { await socket.CloseAsync(WebSocketCloseStatus.NormalClosure, "Device forgotten", CancellationToken.None); } catch { }
        if (_bleClientId == device.Id) { _bleAuthenticated = false; _bleClientId = ""; }
        _state.TrustedDevices.RemoveAll(x => x.Id == device.Id);
        SaveState(); RefreshTrustedDevices(); UpdateConnectionStatus();
    }"""

    new_forget = """    private async Task ForgetTrustedClientAsync(TrustedClient device)
    {
        var revokedMessage = JsonSerializer.Serialize(new
        {
            type = "deviceForgotten",
            serverId = _state.ServerId
        }, _json);
        var revokedBytes = Encoding.UTF8.GetBytes(revokedMessage);

        List<WebSocket> close = new();
        lock (_clients)
            foreach (var pair in _clientIds.Where(x => x.Value == device.Id).ToList())
                close.Add(pair.Key);

        foreach (var socket in close)
        {
            try
            {
                if (socket.State == WebSocketState.Open)
                {
                    await socket.SendAsync(new ArraySegment<byte>(revokedBytes), WebSocketMessageType.Text, true, CancellationToken.None);
                    await Task.Delay(70);
                    await socket.CloseAsync(WebSocketCloseStatus.NormalClosure, "Device forgotten", CancellationToken.None);
                }
            }
            catch { }
        }

        if (_bleClientId == device.Id)
        {
            try
            {
                await _ble.SetSnapshotAsync(revokedMessage);
                await Task.Delay(90);
            }
            catch { }
            _bleAuthenticated = false;
            _bleClientId = "";
        }

        _state.TrustedDevices.RemoveAll(x => x.Id == device.Id);
        SaveState();
        RefreshTrustedDevices();
        UpdateConnectionStatus();
    }"""
    text = replace_once(text, old_forget, new_forget, "notify forgotten device")

    start = "    private async void HeaderSettingsButton_Click(object sender, RoutedEventArgs e)"
    end = "\n    private static Profile DefaultProfile"
    new_settings = r'''    private async void HeaderSettingsButton_Click(object sender, RoutedEventArgs e)
    {
        var win = new Window
        {
            Owner = this,
            Title = "NEXO — подключение и устройства",
            Width = 560,
            Height = 560,
            WindowStartupLocation = WindowStartupLocation.CenterOwner,
            Background = (Brush)FindResource("Bg")
        };

        var root = new StackPanel { Margin = new Thickness(18) };
        root.Children.Add(new TextBlock { Text = "Подключение", FontSize = 20, FontWeight = FontWeights.SemiBold });

        var combo = new ComboBox
        {
            Height = 34,
            Margin = new Thickness(0, 10, 0, 10),
            ItemsSource = new[] { "Wi‑Fi", "Bluetooth LE" },
            SelectedIndex = SelectedTransport() == "Bluetooth" ? 1 : 0
        };
        root.Children.Add(combo);

        var qr = new Button { Content = "Показать QR-код", Height = 34, Margin = new Thickness(0, 0, 0, 16) };
        qr.Click += ShowQr_Click;
        root.Children.Add(qr);

        root.Children.Add(new TextBlock
        {
            Text = "Привязанные устройства",
            FontSize = 16,
            FontWeight = FontWeights.SemiBold,
            Margin = new Thickness(0, 4, 0, 8)
        });

        var deviceRows = new StackPanel();
        root.Children.Add(deviceRows);

        void RebuildDeviceRows()
        {
            deviceRows.Children.Clear();
            var devices = _state.TrustedDevices.OrderByDescending(x => x.LastSeenUtc).ToList();
            if (devices.Count == 0)
            {
                deviceRows.Children.Add(new TextBlock
                {
                    Text = "Нет привязанных устройств",
                    Foreground = (Brush)FindResource("Muted"),
                    Margin = new Thickness(0, 4, 0, 8)
                });
                return;
            }

            foreach (var d in devices)
            {
                var row = new Grid { Height = 46, Margin = new Thickness(0, 0, 0, 4) };
                row.ColumnDefinitions.Add(new ColumnDefinition());
                row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(42) });
                row.Children.Add(new TextBlock
                {
                    Text = $"{d.Name}   •   {d.Transport}",
                    VerticalAlignment = VerticalAlignment.Center,
                    Foreground = Brushes.White
                });

                var more = new Button { Content = "⋮", Tag = d };
                more.Click += (_, args) =>
                {
                    var menu = new ContextMenu();
                    var forget = new MenuItem { Header = "Забыть устройство (отключиться)" };
                    forget.Click += async (_, _) =>
                    {
                        await ForgetTrustedClientAsync(d);
                        if (win.IsVisible)
                            RebuildDeviceRows();
                    };
                    menu.Items.Add(forget);
                    more.ContextMenu = menu;
                    menu.PlacementTarget = more;
                    menu.IsOpen = true;
                    args.Handled = true;
                };
                Grid.SetColumn(more, 1);
                row.Children.Add(more);
                deviceRows.Children.Add(row);
            }
        }

        RebuildDeviceRows();

        combo.SelectionChanged += async (_, _) =>
        {
            await StopAllTransportsAsync();
            _state.Transport = combo.SelectedIndex == 1 ? "Bluetooth" : "Wifi";
            ApplyTransport();
            SaveState();
            await StartSelectedTransportAsync();
        };

        win.Content = new ScrollViewer { Content = root };
        win.ShowDialog();
    }
'''
    text = replace_between(text, start, end, new_settings, "live trusted device settings list")

    path.write_text(text, encoding="utf-8")
    print(f"Applied v1.2.3 Windows fixes: {path}")


def patch_workspace() -> None:
    path = ROOT / "src/mobile/macropad_mobile/lib/v12_workspace.dart"
    text = path.read_text(encoding="utf-8")

    text = replace_once(text, "  final bool controlsLocked;\n", "  final double profileDockOffset;\n  final double navDockOffset;\n  final bool controlsLocked;\n", "workspace dock offset fields")
    text = replace_once(text, "    required this.controlsLocked,\n", "    required this.profileDockOffset,\n    required this.navDockOffset,\n    required this.controlsLocked,\n", "workspace dock offset constructor")
    text = replace_once(text, "        controlsLocked: false,\n", "        profileDockOffset: .5,\n        navDockOffset: .5,\n        controlsLocked: false,\n", "workspace dock offset defaults")
    text = replace_once(text, "      controlsLocked: json['controlsLocked'] == true,\n", "      profileDockOffset: ((json['profileDockOffset'] as num?)?.toDouble() ?? .5).clamp(.08, .92),\n      navDockOffset: ((json['navDockOffset'] as num?)?.toDouble() ?? .5).clamp(.08, .92),\n      controlsLocked: json['controlsLocked'] == true,\n", "workspace dock offset load")
    text = replace_once(text, "        'controlsLocked': controlsLocked,\n", "        'profileDockOffset': profileDockOffset,\n        'navDockOffset': navDockOffset,\n        'controlsLocked': controlsLocked,\n", "workspace dock offset save")

    text = replace_once(text, "  final double bottomExtent;\n", "  final double bottomExtent;\n  final double? horizontalExtent;\n", "profile rail horizontal extent field")
    text = replace_once(text, "    this.bottomExtent = 48,\n", "    this.bottomExtent = 48,\n    this.horizontalExtent,\n", "profile rail horizontal extent constructor")
    text = replace_once(
        text,
        "    final listExtent = itemExtent * 4;",
        "    final requestedListExtent = !_vertical && widget.horizontalExtent != null ? widget.horizontalExtent! - arrowExtent * 2 : null;\n    final listExtent = requestedListExtent == null\n        ? itemExtent * 4\n        : requestedListExtent.clamp(itemExtent * 2, 2000.0).toDouble();",
        "profile rail unlimited horizontal viewport",
    )

    path.write_text(text, encoding="utf-8")
    print(f"Applied v1.2.3 workspace state: {path}")


def patch_mobile() -> None:
    path = ROOT / "src/mobile/macropad_mobile/lib/main.dart"
    text = path.read_text(encoding="utf-8")

    text = replace_once(text, "  double navBottomHeight = 48;\n  Offset _profileMoveDelta = Offset.zero;", "  double navBottomHeight = 48;\n  double profileDockOffset = .5;\n  double navDockOffset = .5;\n  Offset _profileMoveDelta = Offset.zero;", "mobile dock offset state")
    text = replace_once(text, "  bool _resumeReconnectPending = false;\n", "  bool _resumeReconnectPending = false;\n  bool _remoteRevoked = false;\n", "remote revocation state")
    text = replace_once(text, "      navBottomHeight = saved.navBottomHeight;\n      controlsLocked = saved.controlsLocked;", "      navBottomHeight = saved.navBottomHeight;\n      profileDockOffset = saved.profileDockOffset;\n      navDockOffset = saved.navDockOffset;\n      controlsLocked = saved.controlsLocked;", "load dock offsets")
    text = replace_once(text, "        navBottomHeight: navBottomHeight,\n        controlsLocked: controlsLocked,", "        navBottomHeight: navBottomHeight,\n        profileDockOffset: profileDockOffset,\n        navDockOffset: navDockOffset,\n        controlsLocked: controlsLocked,", "save dock offsets")

    old_set_dock = """  void _setProfileDock(ProfileDockSide side) {
    if (controlsLocked || side == profileDock) return;
    setState(() => profileDock = side);
    unawaited(_saveWorkspaceUi());
  }"""
    new_set_dock = """  void _setProfileDock(ProfileDockSide side) {
    if (controlsLocked || side == profileDock) return;
    setState(() {
      profileDock = side;
      profileDockOffset = .5;
    });
    unawaited(_saveWorkspaceUi());
  }"""
    text = replace_once(text, old_set_dock, new_set_dock, "center profile panel on redock")

    text = replace_once(
        text,
        "      if (json is! Map<String, dynamic>) return;\n",
        """      if (json is! Map<String, dynamic>) return;
      if (json['type'] == 'deviceForgotten') {
        _remoteRevoked = true;
        _resumeReconnectPending = false;
        final revokedServerId = (json['serverId'] ?? serverId).toString();
        if (revokedServerId.isNotEmpty) await DeviceStore.remove(revokedServerId);
        try { await widget.transport.close(); } catch (_) {}
        if (mounted) Navigator.of(context).pop('__device_list__');
        return;
      }
""",
        "handle server-side device unlink",
    )

    text = replace_once(text, "      subscription = widget.transport.messages.listen(_onMessage, onError: (Object error) {\n        _resumeReconnectPending = true;", "      subscription = widget.transport.messages.listen(_onMessage, onError: (Object error) {\n        if (_remoteRevoked) return;\n        _resumeReconnectPending = true;", "do not reconnect revoked device on error")
    text = replace_once(text, "      }, onDone: () {\n        _resumeReconnectPending = true;", "      }, onDone: () {\n        if (_remoteRevoked) return;\n        _resumeReconnectPending = true;", "do not reconnect revoked device on close")
    text = replace_once(text, "      _resumeReconnectPending = false;\n      if (mounted) setState(() => status = widget.transport.label);", "      _remoteRevoked = false;\n      _resumeReconnectPending = false;\n      if (mounted) setState(() => status = widget.transport.label);", "clear revocation after successful connection")

    start_marker = "  ProfileDockSide _dockFromDrag(Offset delta, ProfileDockSide current) {"
    end_marker = "  Widget _drawer({required bool compact}) {"
    replacement = r'''  ProfileDockSide _dockFromDrag(Offset delta, ProfileDockSide current) {
    final dx = delta.dx;
    final dy = delta.dy;
    if (current == ProfileDockSide.left || current == ProfileDockSide.right) {
      if (dx.abs() > 62 && dx.abs() > dy.abs() * .8) return dx < 0 ? ProfileDockSide.left : ProfileDockSide.right;
      if (dx.abs() > 42 && dy.abs() > 92) return dy < 0 ? ProfileDockSide.top : ProfileDockSide.bottom;
      return current;
    }
    if (dy.abs() > 62 && dy.abs() > dx.abs() * .8) return dy < 0 ? ProfileDockSide.top : ProfileDockSide.bottom;
    if (dy.abs() > 42 && dx.abs() > 92) return dx < 0 ? ProfileDockSide.left : ProfileDockSide.right;
    return current;
  }

  double _offsetDelta(ProfileDockSide side, Offset delta) {
    if (side == ProfileDockSide.left || side == ProfileDockSide.right) return delta.dy / 420;
    return delta.dx / 700;
  }

  void _profileDragUpdate(DragUpdateDetails details) {
    if (controlsLocked) return;
    _profileMoveDelta += details.delta;
    final nextOffset = (profileDockOffset + _offsetDelta(profileDock, details.delta)).clamp(.08, .92).toDouble();
    if (nextOffset != profileDockOffset) setState(() => profileDockOffset = nextOffset);
  }

  void _profileDragEnd(DragEndDetails details) {
    if (controlsLocked) return;
    final next = _dockFromDrag(_profileMoveDelta, profileDock);
    _profileMoveDelta = Offset.zero;
    if (next != profileDock) {
      setState(() {
        profileDock = next;
        profileDockOffset = .5;
      });
    }
    unawaited(_saveWorkspaceUi());
  }

  void _navDragUpdate(DragUpdateDetails details) {
    if (controlsLocked) return;
    _navMoveDelta += details.delta;
    final nextOffset = (navDockOffset + _offsetDelta(navDock, details.delta)).clamp(.08, .92).toDouble();
    if (nextOffset != navDockOffset) setState(() => navDockOffset = nextOffset);
  }

  void _navDragEnd(DragEndDetails details) {
    if (controlsLocked) return;
    final next = _dockFromDrag(_navMoveDelta, navDock);
    _navMoveDelta = Offset.zero;
    if (next != navDock) {
      setState(() {
        navDock = next;
        navDockOffset = .5;
      });
    }
    unawaited(_saveWorkspaceUi());
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

  Widget _edgePosition({required Widget child, required ProfileDockSide side, required double offset, Offset translation = Offset.zero}) =>
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
      SizedBox(height: 31, child: Center(child: _bottomControlCluster(showKeyboard: keyboardCapability))),
    ]);
    return _controlOverlay(content);
  }

  Widget _controlOverlay(Widget child) {
    return Stack(children: [
      Positioned.fill(child: child),
      if (profileRailVisible && profileDock != ProfileDockSide.bottom) _positionProfileRail(_profileRail()),
      if (profileDock != ProfileDockSide.bottom) _positionProfileRailHandle(_profileRailSideHandle()),
      if (bottomNavVisible && navDock != ProfileDockSide.bottom) _positionNavPanel(_modeSwitcher(vertical: navDock == ProfileDockSide.left || navDock == ProfileDockSide.right)),
      if (navDock != ProfileDockSide.bottom) _positionNavHandle(_navSideHandle()),
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

  Widget _bottomProfilePanel() => Column(mainAxisSize: MainAxisSize.min, children: [
        _bottomResizeHandle(value: profileBottomHeight, min: 42, max: 96, onChanged: (value) => setState(() => profileBottomHeight = value)),
        SizedBox(
          height: profileBottomHeight,
          child: LayoutBuilder(
            builder: (_, constraints) => Center(
              child: _profileRail(horizontalExtent: (constraints.maxWidth - 16).clamp(180.0, 2000.0).toDouble()),
            ),
          ),
        ),
      ]);

  Widget _bottomModePanel() => Column(mainAxisSize: MainAxisSize.min, children: [
        _bottomResizeHandle(value: navBottomHeight, min: 40, max: 104, onChanged: (value) => setState(() => navBottomHeight = value)),
        SizedBox(height: navBottomHeight, child: Center(child: _modeSwitcher(vertical: false))),
      ]);

  Widget _bottomKeyboardPanel() => SizedBox(
        height: tabletKeyboardHeight,
        child: Column(children: [
          if (!controlsLocked)
            GestureDetector(
              behavior: HitTestBehavior.opaque,
              onVerticalDragUpdate: (details) => setState(() => tabletKeyboardHeight = (tabletKeyboardHeight - details.delta.dy).clamp(170.0, 430.0)),
              onVerticalDragEnd: (_) => unawaited(_saveWorkspaceUi()),
              child: Container(
                height: 18,
                color: const Color(0xff24272a),
                alignment: Alignment.center,
                child: const Icon(Icons.drag_handle, size: 17, color: Color(0xffb8bdc2)),
              ),
            ),
          Expanded(child: _TabletRemoteKeyboard(onKey: _virtualKey, onLanguage: _selectKeyboardLayout, activeModifiers: _keyboardModifiers, languageCode: _activeLanguageCode)),
        ]),
      );

  Widget _bottomResizeHandle({required double value, required double min, required double max, required ValueChanged<double> onChanged}) {
    if (controlsLocked) return const SizedBox.shrink();
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onVerticalDragUpdate: (details) => onChanged((value - details.delta.dy).clamp(min, max).toDouble()),
      onVerticalDragEnd: (_) => unawaited(_saveWorkspaceUi()),
      child: const SizedBox(
        height: 12,
        child: ColoredBox(color: Color(0xff24272a), child: Center(child: Icon(Icons.drag_handle, size: 15, color: Color(0xff9da3a8)))),
      ),
    );
  }

  Widget _positionProfileRail(Widget rail) => _edgePosition(child: rail, side: profileDock, offset: profileDockOffset);
  Widget _positionProfileRailHandle(Widget handle) => _edgePosition(
        child: handle,
        side: profileDock,
        offset: profileDockOffset,
        translation: _handleTranslation(profileDock, profileRailVisible, 50),
      );
  Widget _positionNavPanel(Widget panel) => _edgePosition(child: panel, side: navDock, offset: navDockOffset);
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
      tooltip: controlsLocked ? 'Профили: показать / скрыть' : 'Профили: нажмите или перетащите',
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
      tooltip: controlsLocked ? 'DECK / Multi.: показать / скрыть' : 'DECK / Multi.: нажмите или перетащите',
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
              child: SizedBox(width: 30, height: 38, child: Icon(icon, size: 18, color: mpMuted)),
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
              tooltip: bottomNavVisible ? 'Скрыть DECK / Multi.' : 'Показать DECK / Multi.',
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
              tooltip: profileRailVisible ? 'Скрыть профили' : 'Показать профили',
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
    text = replace_between(text, start_marker, end_marker, replacement, "v1.2.3 workspace controls")

    drawer_anchor = """                  const Divider(height: 1),
                  const Padding(padding: EdgeInsets.fromLTRB(16, 14, 16, 6), child: Text('СМЕНИТЬ УСТРОЙСТВО', style: TextStyle(color: mpMuted, fontSize: 10, letterSpacing: 1))),"""
    drawer_insert = """                  const Divider(height: 1),
                  const Padding(
                    padding: EdgeInsets.fromLTRB(16, 14, 16, 6),
                    child: Text('ДОПОЛНИТЕЛЬНЫЕ ПАНЕЛИ', style: TextStyle(color: mpMuted, fontSize: 10, letterSpacing: 1)),
                  ),
                  SwitchListTile.adaptive(
                    dense: true,
                    value: profileRailVisible || bottomNavVisible || (widget.formFactor == ClientFormFactor.tablet && tabletKeyboardVisible),
                    title: const Text('Все дополнительные панели'),
                    subtitle: const Text('Показать или скрыть дополнительные элементы рабочего пространства', style: TextStyle(fontSize: 10, color: mpMuted)),
                    onChanged: (value) {
                      setState(() {
                        profileRailVisible = value;
                        bottomNavVisible = value;
                        if (widget.formFactor == ClientFormFactor.tablet) tabletKeyboardVisible = value;
                      });
                      unawaited(_saveWorkspaceUi());
                    },
                  ),
                  SwitchListTile.adaptive(
                    dense: true,
                    value: profileRailVisible,
                    title: const Text('Панель профилей'),
                    onChanged: (value) { setState(() => profileRailVisible = value); unawaited(_saveWorkspaceUi()); },
                  ),
                  SwitchListTile.adaptive(
                    dense: true,
                    value: bottomNavVisible,
                    title: const Text('DECK / Multi.'),
                    onChanged: (value) { setState(() => bottomNavVisible = value); unawaited(_saveWorkspaceUi()); },
                  ),
                  if (widget.formFactor == ClientFormFactor.tablet)
                    SwitchListTile.adaptive(
                      dense: true,
                      value: tabletKeyboardVisible,
                      title: const Text('Экранная клавиатура'),
                      onChanged: externalKeyboardConnected ? null : (value) { setState(() => tabletKeyboardVisible = value); unawaited(_saveWorkspaceUi()); },
                    ),
                  const Divider(height: 1),
                  const Padding(padding: EdgeInsets.fromLTRB(16, 14, 16, 6), child: Text('СМЕНИТЬ УСТРОЙСТВО', style: TextStyle(color: mpMuted, fontSize: 10, letterSpacing: 1))),"""
    text = replace_once(text, drawer_anchor, drawer_insert, "drawer panel visibility controls")

    path.write_text(text, encoding="utf-8")
    print(f"Applied v1.2.3 mobile fixes: {path}")


def main() -> None:
    target = sys.argv[1] if len(sys.argv) > 1 else "all"
    if target in ("all", "windows"):
        patch_windows()
    if target in ("all", "mobile"):
        patch_workspace()
        patch_mobile()
    if target not in ("all", "windows", "mobile"):
        raise SystemExit("usage: apply_v123_fixes.py [all|windows|mobile]")


if __name__ == "__main__":
    main()
