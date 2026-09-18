from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)


def replace_between(text: str, start: str, end: str, replacement: str, label: str) -> str:
    a = text.find(start)
    if a < 0:
        raise RuntimeError(f"{label}: start marker not found")
    b = text.find(end, a)
    if b < 0:
        raise RuntimeError(f"{label}: end marker not found")
    return text[:a] + replacement + text[b:]


def main() -> None:
    path = ROOT / "src/mobile/macropad_mobile/lib/main.dart"
    text = path.read_text(encoding="utf-8")

    # v1.4 uses explicit transfer packages. Mobile does not mirror every active
    # workspace anymore; it only stores a package when a PC explicitly sends it
    # or when link auto-sync is enabled.
    text = text.replace("Перенос / библиотека устройств", "QR: передача / импорт")
    text = text.replace("      await widget.transport.send({'type': 'workspaceBackupRequest'});\n", "")

    if "  Future<void> _v13ScanRestoreQr() async {" in text:
        text = replace_between(
            text,
            "  Future<void> _v13ScanRestoreQr() async {",
            "  Future<void> _pairWifi(DiscoveredPc pc) async {",
            r'''  Future<void> _v13ScanRestoreQr() async {
    final qr = await _scanQr();
    if (!mounted || qr == null) return;
    if (qr.mode != 'importDevice') {
      _message('Этот QR предназначен для обычного подключения.');
      return;
    }
    await _v14SendPendingTransferByQr(qr);
  }

  Future<void> _v14SendPendingTransferByQr(QrPairing qr) async {
    if (qr.transport != TransportKind.wifi || qr.host == null || qr.host!.trim().isEmpty) {
      _message('Передача профилей через QR выполняется по Wi‑Fi.');
      return;
    }

    final workspace = await V13WorkspaceVault.loadPending();
    if (workspace == null) {
      _message('На устройстве нет подготовленного пакета. Сначала передайте профили с исходного ПК.');
      return;
    }

    final remote = WifiRemoteTransport(
      host: qr.host!.trim(),
      port: qr.port,
      clientId: clientId,
      pairToken: qr.token,
    );
    StreamSubscription<String>? transferSub;
    try {
      await remote.connect();
      String newToken = '';
      String newName = 'NEXO PC';
      final paired = Completer<void>();
      transferSub = remote.messages.listen((message) async {
        try {
          final json = jsonDecode(message);
          if (json is Map && json['type'] == 'paired') {
            newToken = (json['deviceToken'] ?? '').toString();
            newName = (json['serverName'] ?? newName).toString();
            if (!paired.isCompleted) paired.complete();
          }
        } catch (_) {}
      });

      await remote.send({
        'type': 'applyTransferPackage',
        'workspace': workspace,
        'firstRun': true,
      });
      await Future.any([paired.future, Future<void>.delayed(const Duration(milliseconds: 900))]);

      if (newToken.isNotEmpty && qr.serverId.isNotEmpty) {
        final pc = SavedPc(
          serverId: qr.serverId,
          name: newName,
          host: qr.host!.trim(),
          port: qr.port,
          deviceToken: newToken,
          transport: 'wifi',
          lastSeen: DateTime.now(),
        );
        await DeviceStore.upsert(pc);
        savedPcs[pc.serverId] = pc;
      }

      await V13WorkspaceVault.clearPending();
      if (mounted) _message('Пакет профилей и настроек передан на новый ПК.');
    } catch (e) {
      if (mounted) _message('Не удалось передать пакет: $e');
    } finally {
      await transferSub?.cancel();
      await remote.close();
    }
  }

''',
            "v1.4 QR transfer",
        )

    # The normal QR button understands the transfer mode automatically.
    if "  Future<void> _connectByQrDirect() async {" in text:
        text = replace_between(
            text,
            "  Future<void> _connectByQrDirect() async {",
            "  Future<void> _pairWifi(DiscoveredPc pc) async {",
            r'''  Future<void> _connectByQrDirect() async {
    final qr = await _scanQr();
    if (!mounted || qr == null) return;
    if (qr.mode == 'importDevice') {
      await _v14SendPendingTransferByQr(qr);
      return;
    }
    if (qr.transport == TransportKind.wifi) {
      final host = qr.host?.trim() ?? '';
      if (host.isEmpty) return _message('В QR-коде нет адреса ПК.');
      final remote = WifiRemoteTransport(host: host, port: qr.port, clientId: clientId, pairToken: qr.token);
      await _openRemote(remote, serverId: qr.serverId, serverName: 'NEXO PC', host: host, port: qr.port, transportName: 'wifi');
      return;
    }
    if (transport != TransportKind.bluetooth) await _switchTransport(TransportKind.bluetooth);
    _message('Для Bluetooth дождитесь появления ПК в списке и подтвердите привязку этим QR-кодом.');
  }

''',
            "QR mode auto routing",
        )

    if "      if (json['type'] == 'workspaceBackup') {" in text:
        text = replace_between(
            text,
            "      if (json['type'] == 'workspaceBackup') {",
            "      if (json['type'] == 'deviceForgotten') {",
            r'''      if (json['type'] == 'workspaceBackup') {
        // Legacy v1.3 message: no passive saving in v1.4.
        return;
      }
      if (json['type'] == 'transferPackage') {
        final markPending = json['markPending'] != false;
        await V13WorkspaceVault.saveTransfer(json, markPending: markPending);
        try {
          await widget.transport.send({
            'type': 'transferStored',
            'sourceServerId': (json['sourceServerId'] ?? '').toString(),
          });
        } catch (_) {}
        return;
      }
      if (json['type'] == 'transferPackageRequest') {
        final requestedServerId = (json['sourceServerId'] ?? '').toString();
        final workspace = requestedServerId.isEmpty
            ? await V13WorkspaceVault.loadPending()
            : await V13WorkspaceVault.load(requestedServerId);
        try {
          await widget.transport.send({
            'type': 'transferPackageResponse',
            'sourceServerId': requestedServerId,
            'workspace': workspace,
          });
        } catch (_) {}
        return;
      }
''',
            "v1.4 transfer protocol",
        )

    text = replace_once(
        text,
        "  final Set<String> _keyboardModifiers = <String>{};\n",
        "  final Set<String> _keyboardModifiers = <String>{};\n  final Set<String> _physicalKeyboardModifiers = <String>{};\n",
        "physical keyboard modifiers",
    )

    # Native Android dispatchKeyEvent is authoritative. Flutter Focus no longer
    # receives the same key a second time.
    text = replace_between(
        text,
        "      _deviceChannel.setMethodCallHandler((call) async {",
        "      _refreshHardwareKeyboard();",
        r'''      _deviceChannel.setMethodCallHandler((call) async {
        if (call.method == 'hardwareKeyboardChanged') {
          final connected = call.arguments == true;
          if (!connected) _physicalKeyboardModifiers.clear();
          if (mounted && connected != externalKeyboardConnected) {
            setState(() {
              externalKeyboardConnected = connected;
              tabletKeyboardVisible = !connected;
            });
          } else if (mounted && !connected && !tabletKeyboardVisible) {
            setState(() => tabletKeyboardVisible = true);
          }
          return;
        }

        if (call.method == 'hardwareKeyEvent') {
          final args = call.arguments;
          if (args is! Map) return;
          final token = (args['key'] ?? '').toString();
          final down = args['down'] == true;
          if (token.isEmpty) return;

          if (mounted && !externalKeyboardConnected) {
            setState(() {
              externalKeyboardConnected = true;
              tabletKeyboardVisible = false;
            });
          }

          const modifiers = {'CTRL', 'ALT', 'SHIFT', 'WIN'};
          if (modifiers.contains(token)) {
            if (down) {
              _physicalKeyboardModifiers.add(token);
            } else {
              _physicalKeyboardModifiers.remove(token);
            }
            try { await widget.transport.send({'type': 'keyEvent', 'key': token, 'down': down}); } catch (_) {}
            return;
          }

          final ctrl = _physicalKeyboardModifiers.contains('CTRL');
          final alt = _physicalKeyboardModifiers.contains('ALT');
          final win = _physicalKeyboardModifiers.contains('WIN');
          final shift = _physicalKeyboardModifiers.contains('SHIFT');
          final printable = !ctrl && !alt && !win ? _printableKeyboardText(token, shift) : null;

          if (printable != null) {
            if (down) {
              try { await widget.transport.send({'type': 'textInput', 'text': printable}); } catch (_) {}
            }
            return;
          }

          try { await widget.transport.send({'type': 'keyEvent', 'key': token, 'down': down}); } catch (_) {}
        }
      });
''',
        "native external keyboard bridge",
    )

    # Polling fallback also restores the screen keyboard after unplugging.
    text = text.replace(
        "        externalKeyboardConnected = connected;\n        if (connected) tabletKeyboardVisible = false;",
        "        externalKeyboardConnected = connected;\n        tabletKeyboardVisible = !connected;",
    )

    # Remove Flutter Focus wrapper that caused the green frame when pressing Space.
    build_start = """  @override
  Widget build(BuildContext context) {
    final pages = <Widget>[deck(), media()];"""
    build_end = "\n  ProfileDockSide _nearestDock(Offset point, Size size) {"
    build = r'''  @override
  Widget build(BuildContext context) {
    final pages = <Widget>[deck(), media()];
    if (tab >= pages.length) tab = 0;
    final compact = widget.formFactor == ClientFormFactor.phone && MediaQuery.orientationOf(context) == Orientation.landscape;
    final tablet = widget.formFactor == ClientFormFactor.tablet;
    return PopScope(
      canPop: _remoteRevoked,
      child: Scaffold(
        drawer: _drawer(compact: compact),
        appBar: AppBar(
          toolbarHeight: compact ? 38 : null,
          titleSpacing: compact ? 8 : null,
          title: Row(mainAxisSize: MainAxisSize.min, children: [
            MacroPadMark(size: compact ? 17 : 22),
            SizedBox(width: compact ? 6 : 9),
            Flexible(child: Text(profile?.name ?? 'NEXO', overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: compact ? 13 : null))),
          ]),
          actions: [
            IconButton(
              tooltip: 'Повернуть экран',
              visualDensity: compact ? VisualDensity.compact : VisualDensity.standard,
              onPressed: () => toggleScreenOrientation(context),
              icon: Icon(Icons.screen_rotation, size: compact ? 19 : 23),
            ),
            Padding(
              padding: EdgeInsets.only(right: compact ? 5 : 10),
              child: Center(child: Row(children: [
                Icon(Icons.circle, size: 7, color: connectionError == null && status != 'Отключено' ? mpGreen : mpMuted),
                const SizedBox(width: 5),
                if (!compact) Text(status, style: const TextStyle(fontSize: 11)),
              ])),
            ),
          ],
        ),
        body: SafeArea(child: connectionError == null ? _workspaceBody(pages, compact) : _connectionErrorView()),
        bottomNavigationBar: connectionError == null && !compact && !tablet
            ? _SharpBottomNav(
                compact: false,
                selectedIndex: tab,
                onSelected: (value) => setState(() => tab = value),
                items: const [_SharpNavItem(Icons.grid_view, 'Deck'), _SharpNavItem(Icons.play_circle_outline, 'Media')],
              )
            : null,
      ),
    );
  }
'''
    text = replace_between(text, build_start, build_end, build, "remove Flutter keyboard focus")

    # Never restore a stale translation that can leave all cells outside the
    # current reduced work area. The saved zoom level is retained.
    text = text.replace(
        "_deckTransform.value = Matrix4.fromList(values);",
        """final restored = Matrix4.fromList(values);
      final scale = restored.getMaxScaleOnAxis().clamp(.35, 3.2).toDouble();
      _deckTransform.value = Matrix4.diagonal3Values(scale, scale, 1);""",
    )

    text = text.replace(
        "minScale: .35, maxScale: 3.2, boundaryMargin: const EdgeInsets.all(500), constrained: false,",
        "minScale: .35, maxScale: 3.2, boundaryMargin: EdgeInsets.zero, constrained: false, clipBehavior: Clip.hardEdge,",
    )

    # The work-area bounds are invisible. They shrink on every side occupied by
    # a visible auxiliary panel or its separate arrow strip.
    workspace_start = "  Widget _workspaceBody(List<Widget> pages, bool compact) {"
    control_start = "  Widget _controlOverlay(Widget child, {required bool showKeyboard}) {"
    workspace = r'''  Widget _workspaceBody(List<Widget> pages, bool compact) {
    final tablet = widget.formFactor == ClientFormFactor.tablet;
    if (!tablet && !compact) return pages[tab];

    final keyboardCapability = tablet && !externalKeyboardConnected && tab == 0;
    final keyboardShown = keyboardCapability && tabletKeyboardVisible;

    final leftPanel = (profileRailVisible && profileDock == ProfileDockSide.left ? 50.0 : 0.0)
        + (bottomNavVisible && navDock == ProfileDockSide.left ? 54.0 : 0.0);
    final rightPanel = (profileRailVisible && profileDock == ProfileDockSide.right ? 50.0 : 0.0)
        + (bottomNavVisible && navDock == ProfileDockSide.right ? 54.0 : 0.0);
    final topPanel = (profileRailVisible && profileDock == ProfileDockSide.top ? 50.0 : 0.0)
        + (bottomNavVisible && navDock == ProfileDockSide.top ? 54.0 : 0.0);

    final leftControls = profileDock == ProfileDockSide.left || navDock == ProfileDockSide.left ? 32.0 : 0.0;
    final rightControls = profileDock == ProfileDockSide.right || navDock == ProfileDockSide.right ? 32.0 : 0.0;
    final topControls = profileDock == ProfileDockSide.top || navDock == ProfileDockSide.top ? 32.0 : 0.0;

    final bottomProfile = profileDock == ProfileDockSide.bottom && profileRailVisible;
    final bottomNav = navDock == ProfileDockSide.bottom && bottomNavVisible;
    final hasBottomControls = keyboardCapability || profileDock == ProfileDockSide.bottom || navDock == ProfileDockSide.bottom;

    final content = Column(children: [
      Expanded(
        child: Padding(
          padding: EdgeInsets.only(
            left: leftPanel + leftControls,
            right: rightPanel + rightControls,
            top: topPanel + topControls,
          ),
          child: ClipRect(child: pages[tab]),
        ),
      ),
      if (bottomProfile) _bottomProfilePanel(),
      if (bottomNav) _bottomModePanel(),
      if (keyboardShown) _bottomKeyboardPanel(),
      if (hasBottomControls)
        SizedBox(
          height: 31,
          child: Center(child: _bottomControlCluster(showKeyboard: keyboardCapability)),
        ),
    ]);

    return _controlOverlay(content, showKeyboard: false);
  }

'''
    text = replace_between(text, workspace_start, control_start, workspace, "invisible workspace bounds")

    # Bottom arrows now live in their own 31px strip below every bottom panel,
    # never on top of the panel itself.
    overlay_end = "  Widget _profileRail({double? horizontalExtent}) => NexoProfileRail("
    overlay = r'''  Widget _controlOverlay(Widget child, {required bool showKeyboard}) {
    return Stack(clipBehavior: Clip.hardEdge, children: [
      Positioned.fill(child: child),
      if (profileRailVisible && profileDock != ProfileDockSide.bottom)
        _positionProfileRail(_profileDragSurface(_profileRail())),
      if (profileDock != ProfileDockSide.bottom)
        _positionProfileRailHandle(_profileRailSideHandle()),
      if (bottomNavVisible && navDock != ProfileDockSide.bottom)
        _positionNavPanel(_navDragSurface(_modeSwitcher(vertical: navDock == ProfileDockSide.left || navDock == ProfileDockSide.right))),
      if (navDock != ProfileDockSide.bottom)
        _positionNavHandle(_navSideHandle()),
    ]);
  }

'''
    text = replace_between(text, control_start, overlay_end, overlay, "separate bottom arrow strip")

    path.write_text(text, encoding="utf-8")
    print(f"Applied v1.4 mobile input/workspace fixes: {path}")


if __name__ == "__main__":
    main()
