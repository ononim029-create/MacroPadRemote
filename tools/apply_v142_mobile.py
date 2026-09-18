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
    b = text.find(end, a + len(start))
    if b < 0:
        raise RuntimeError(f"{label}: end marker not found")
    return text[:a] + replacement + text[b:]


def main() -> None:
    path = ROOT / "src/mobile/macropad_mobile/lib/main.dart"
    text = path.read_text(encoding="utf-8")

    # Dynamic pan/zoom metrics for the current deck viewport.
    text = replace_once(
        text,
        "  Matrix4? _deckUserTransformBeforeFit;\n",
        """  Matrix4? _deckUserTransformBeforeFit;
  Matrix4? _pendingDeckRestore;
  Size _deckViewportSize = Size.zero;
  Size _deckCanvasSize = Size.zero;
  Size _deckCellSize = Size.zero;
  double _deckMinScale = 1.0;
  double _deckMaxScale = 2.0;
  bool _deckClampGuard = false;
  double _workspaceLeftInset = 0;
  double _workspaceRightInset = 0;
  double _workspaceTopInset = 0;
  double _workspaceBottomInset = 0;
""",
        "deck transform metrics",
    )

    # Restore the saved translation too; clamping is delayed until the current
    # page/work-area dimensions are known.
    text = text.replace(
        """final restored = Matrix4.fromList(values);
      final scale = restored.getMaxScaleOnAxis().clamp(.35, 3.2).toDouble();
      _deckTransform.value = Matrix4.diagonal3Values(scale, scale, 1);""",
        """_pendingDeckRestore = Matrix4.fromList(values);
      WidgetsBinding.instance.addPostFrameCallback((_) => _applyPendingDeckRestore());""",
    )

    # "Default view" is now deterministic: scale 1.0 and center at the original
    # work-area center. Insets only push the deck when it would actually overlap
    # an opened auxiliary panel.
    text = replace_between(
        text,
        "  void _fitDeck() {",
        "\n  @override\n  void didChangeDependencies() {",
        r'''  void _fitDeck() {
    _deckReturnController.stop();
    if (_deckViewportSize.isEmpty || _deckCanvasSize.isEmpty) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _fitDeck();
      });
      return;
    }

    final begin = _deckTransform.value.clone();
    final preferredDx = (_workspaceRightInset - _workspaceLeftInset) / 2;
    final preferredDy = (_workspaceBottomInset - _workspaceTopInset) / 2;
    final target = _boundedDeckMatrix(
      Matrix4.diagonal3Values(1.0, 1.0, 1.0)
        ..setTranslationRaw(preferredDx, preferredDy, 0),
      keepFullyVisible: true,
    );

    _deckFitMode = true;
    _deckUserTransformBeforeFit = null;
    _deckReturnAnimation = Matrix4Tween(begin: begin, end: target)
        .animate(CurvedAnimation(parent: _deckReturnController, curve: Curves.easeOutCubic));
    _deckReturnController.forward(from: 0);
  }

''',
        "default deck view",
    )

    # Work-area boundaries use the exact occupied dimensions: no decorative gap.
    workspace_start = "  Widget _workspaceBody(List<Widget> pages, bool compact) {"
    control_start = "  Widget _controlOverlay(Widget child, {required bool showKeyboard}) {"
    workspace = r'''  Widget _workspaceBody(List<Widget> pages, bool compact) {
    final tablet = widget.formFactor == ClientFormFactor.tablet;
    if (!tablet && !compact) {
      _workspaceLeftInset = 0;
      _workspaceRightInset = 0;
      _workspaceTopInset = 0;
      _workspaceBottomInset = 0;
      return pages[tab];
    }

    final keyboardCapability = tablet && !externalKeyboardConnected && tab == 0;
    final keyboardShown = keyboardCapability && tabletKeyboardVisible;

    // Exact visible sizes of the side/top panels and their dedicated handle strip.
    final leftPanel = (profileRailVisible && profileDock == ProfileDockSide.left ? 48.0 : 0.0)
        + (bottomNavVisible && navDock == ProfileDockSide.left ? 52.0 : 0.0);
    final rightPanel = (profileRailVisible && profileDock == ProfileDockSide.right ? 48.0 : 0.0)
        + (bottomNavVisible && navDock == ProfileDockSide.right ? 52.0 : 0.0);
    final topPanel = (profileRailVisible && profileDock == ProfileDockSide.top ? 48.0 : 0.0)
        + (bottomNavVisible && navDock == ProfileDockSide.top ? 52.0 : 0.0);

    final leftControls = profileDock == ProfileDockSide.left || navDock == ProfileDockSide.left ? 30.0 : 0.0;
    final rightControls = profileDock == ProfileDockSide.right || navDock == ProfileDockSide.right ? 30.0 : 0.0;
    final topControls = profileDock == ProfileDockSide.top || navDock == ProfileDockSide.top ? 30.0 : 0.0;

    final bottomProfile = profileDock == ProfileDockSide.bottom && profileRailVisible;
    final bottomNav = navDock == ProfileDockSide.bottom && bottomNavVisible;
    final hasBottomControls = keyboardCapability || profileDock == ProfileDockSide.bottom || navDock == ProfileDockSide.bottom;

    _workspaceLeftInset = leftPanel + leftControls;
    _workspaceRightInset = rightPanel + rightControls;
    _workspaceTopInset = topPanel + topControls;
    _workspaceBottomInset =
        (bottomProfile ? profileBottomHeight : 0.0)
        + (bottomNav ? navBottomHeight : 0.0)
        + (keyboardShown ? tabletKeyboardHeight : 0.0)
        + (hasBottomControls ? 31.0 : 0.0);

    final content = Column(children: [
      Expanded(
        child: Padding(
          padding: EdgeInsets.only(
            left: _workspaceLeftInset,
            right: _workspaceRightInset,
            top: _workspaceTopInset,
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
    text = replace_between(text, workspace_start, control_start, workspace, "exact work-area boundaries")

    text = text.replace(
        "_handleTranslation(profileDock, profileRailVisible, 50)",
        "_handleTranslation(profileDock, profileRailVisible, 48)",
    )
    text = text.replace(
        "_handleTranslation(navDock, bottomNavVisible, 54)",
        "_handleTranslation(navDock, bottomNavVisible, 52)",
    )

    # Side/top panels are flush with the edge; the old 4px padding made the
    # invisible work-area boundary disagree with the visible panel boundary.
    text = replace_between(
        text,
        "  Widget _edgePosition({",
        "\n  Widget _workspaceBody(List<Widget> pages, bool compact) {",
        r'''  Widget _edgePosition({
    required Widget child,
    required ProfileDockSide side,
    required double offset,
    Offset translation = Offset.zero,
  }) =>
      Positioned.fill(
        child: Align(
          alignment: _dockAlignment(side, offset),
          child: Transform.translate(offset: translation, child: child),
        ),
      );

''',
        "flush auxiliary panels",
    )

    # Replace the deck viewer completely. InteractiveViewer gets enough boundary
    # space to move freely; our clamp enforces "at least one cell remains visible"
    # instead of preventing panning altogether.
    text = replace_between(
        text,
        "  Widget _deckCanvas(ProfileSnapshot p) {",
        "\n  Widget _remoteTile(TileSnapshot tile, double scale) {",
        r'''  double _minimumDeckScale(int rows, int columns) {
    final cellCount = max(1, rows * columns);
    // At the minimum zoom the area of the whole deck is approximately the area
    // of one unscaled cell: s^2 * N = 1.
    return (1 / sqrt(cellCount)).clamp(0.06, 1.0).toDouble();
  }

  double _maximumDeckScale(int rows, int columns) {
    final cellCount = max(1, rows * columns);
    // At maximum zoom one cell may occupy roughly twice the original total
    // grid area: s^2 = 2N. This keeps the limit proportional to cell count.
    return sqrt(cellCount * 2.0).clamp(1.414, 18.0).toDouble();
  }

  Matrix4 _boundedDeckMatrix(Matrix4 candidate, {bool keepFullyVisible = false}) {
    if (_deckViewportSize.isEmpty || _deckCanvasSize.isEmpty) return candidate;

    final scale = candidate.getMaxScaleOnAxis().clamp(_deckMinScale, _deckMaxScale).toDouble();
    var tx = candidate.storage[12];
    var ty = candidate.storage[13];

    final transformedW = _deckCanvasSize.width * scale;
    final transformedH = _deckCanvasSize.height * scale;
    final baseLeft = (_deckViewportSize.width - transformedW) / 2;
    final baseTop = (_deckViewportSize.height - transformedH) / 2;

    double minTx;
    double maxTx;
    double minTy;
    double maxTy;

    if (keepFullyVisible && transformedW <= _deckViewportSize.width) {
      minTx = -baseLeft;
      maxTx = _deckViewportSize.width - transformedW - baseLeft;
    } else {
      final visibleW = min(_deckCellSize.width * scale, _deckViewportSize.width);
      minTx = visibleW - transformedW - baseLeft;
      maxTx = _deckViewportSize.width - visibleW - baseLeft;
    }

    if (keepFullyVisible && transformedH <= _deckViewportSize.height) {
      minTy = -baseTop;
      maxTy = _deckViewportSize.height - transformedH - baseTop;
    } else {
      final visibleH = min(_deckCellSize.height * scale, _deckViewportSize.height);
      minTy = visibleH - transformedH - baseTop;
      maxTy = _deckViewportSize.height - visibleH - baseTop;
    }

    if (minTx > maxTx) {
      final center = (minTx + maxTx) / 2;
      minTx = center;
      maxTx = center;
    }
    if (minTy > maxTy) {
      final center = (minTy + maxTy) / 2;
      minTy = center;
      maxTy = center;
    }

    tx = tx.clamp(minTx, maxTx).toDouble();
    ty = ty.clamp(minTy, maxTy).toDouble();

    return Matrix4.diagonal3Values(scale, scale, 1)
      ..setTranslationRaw(tx, ty, 0);
  }

  void _clampDeckTransform({bool keepFullyVisible = false}) {
    if (_deckClampGuard || _deckViewportSize.isEmpty || _deckCanvasSize.isEmpty) return;
    final current = _deckTransform.value;
    final bounded = _boundedDeckMatrix(current, keepFullyVisible: keepFullyVisible);

    final currentScale = current.getMaxScaleOnAxis();
    final nextScale = bounded.getMaxScaleOnAxis();
    final changed = (currentScale - nextScale).abs() > .0005
        || (current.storage[12] - bounded.storage[12]).abs() > .2
        || (current.storage[13] - bounded.storage[13]).abs() > .2;
    if (!changed) return;

    _deckClampGuard = true;
    _deckTransform.value = bounded;
    _deckClampGuard = false;
  }

  void _applyPendingDeckRestore() {
    final pending = _pendingDeckRestore;
    if (pending == null || _deckViewportSize.isEmpty || _deckCanvasSize.isEmpty) return;
    _pendingDeckRestore = null;
    _deckReturnController.stop();
    _deckTransform.value = _boundedDeckMatrix(pending);
  }

  Widget _deckCanvas(ProfileSnapshot p) {
    return LayoutBuilder(
      builder: (_, constraints) {
        final columns = p.columns.clamp(1, 12).toInt();
        final rows = p.rows.clamp(1, 12).toInt();
        const gapBase = 7.0;
        const padBase = 10.0;
        final compact = widget.formFactor == ClientFormFactor.phone && MediaQuery.orientationOf(context) == Orientation.landscape;

        final availableW = (constraints.maxWidth - padBase * 2 - gapBase * (columns - 1)).clamp(1.0, double.infinity);
        final availableH = (constraints.maxHeight - padBase * 2 - gapBase * (rows - 1)).clamp(1.0, double.infinity);
        final fitW = availableW / columns;
        final fitH = availableH / rows;
        final cellW = min(fitW, fitH / .76).clamp(18.0, 150.0);
        final cellH = cellW * .76;
        final uiScale = (cellW / 105).clamp(.38, 1.18);
        final packed = packTiles(p.tiles, rows, columns);
        final totalW = padBase * 2 + columns * cellW + (columns - 1) * gapBase;
        final totalH = padBase * 2 + rows * cellH + (rows - 1) * gapBase;

        _deckViewportSize = Size(constraints.maxWidth, constraints.maxHeight);
        _deckCanvasSize = Size(totalW, totalH);
        _deckCellSize = Size(cellW + gapBase, cellH + gapBase);
        _deckMinScale = _minimumDeckScale(rows, columns);
        _deckMaxScale = _maximumDeckScale(rows, columns);

        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (!mounted) return;
          if (_pendingDeckRestore != null) {
            _applyPendingDeckRestore();
          } else {
            _clampDeckTransform();
          }
        });

        final canvas = SizedBox(
          width: totalW,
          height: totalH,
          child: Stack(children: [
            for (final item in packed)
              Positioned(
                left: padBase + item.column * (cellW + gapBase),
                top: padBase + item.row * (cellH + gapBase),
                width: item.columnSpan * cellW + (item.columnSpan - 1) * gapBase,
                height: item.rowSpan * cellH + (item.rowSpan - 1) * gapBase,
                child: _remoteTile(item.tile, uiScale),
              ),
          ]),
        );

        // InteractiveViewer's own boundary must be generous. The custom clamp
        // below is the real boundary and keeps at least one full cell visible.
        final interactionMargin = max(
              max(totalW, totalH) * _deckMaxScale,
              max(constraints.maxWidth, constraints.maxHeight),
            ) +
            max(constraints.maxWidth, constraints.maxHeight);

        return Stack(children: [
          Center(
            child: InteractiveViewer(
              transformationController: _deckTransform,
              panEnabled: !panLocked,
              scaleEnabled: !scaleLocked,
              panAxis: PanAxis.free,
              minScale: _deckMinScale,
              maxScale: _deckMaxScale,
              boundaryMargin: EdgeInsets.all(interactionMargin),
              constrained: false,
              alignment: Alignment.center,
              clipBehavior: Clip.hardEdge,
              onInteractionStart: (_) {
                _deckReturnController.stop();
                _deckFitMode = false;
                _deckUserTransformBeforeFit = null;
              },
              onInteractionUpdate: (_) => _clampDeckTransform(),
              onInteractionEnd: (_) {
                _clampDeckTransform();
                unawaited(_saveDeckView());
                unawaited(_saveWorkspaceUi());
              },
              child: canvas,
            ),
          ),
          Positioned(
            right: compact ? 5 : 8,
            top: compact ? 5 : 8,
            child: Material(
              color: const Color(0xee202326),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(10),
                side: const BorderSide(color: mpBorder),
              ),
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                IconButton(
                  tooltip: scaleLocked ? 'Разблокировать масштаб' : 'Зафиксировать масштаб',
                  onPressed: _toggleScaleLock,
                  icon: Icon(scaleLocked ? Icons.lock : Icons.lock_open),
                  iconSize: compact ? 16 : 19,
                  visualDensity: VisualDensity.compact,
                ),
                IconButton(
                  tooltip: panLocked ? 'Разблокировать перемещение' : 'Заблокировать перемещение',
                  onPressed: _togglePanLock,
                  icon: Icon(panLocked ? Icons.pan_tool_alt : Icons.pan_tool_outlined),
                  iconSize: compact ? 16 : 19,
                  visualDensity: VisualDensity.compact,
                ),
                IconButton(
                  tooltip: 'Вид по умолчанию',
                  onPressed: _fitDeck,
                  icon: const Icon(Icons.center_focus_strong),
                  iconSize: compact ? 16 : 19,
                  visualDensity: VisualDensity.compact,
                ),
              ]),
            ),
          ),
        ]);
      },
    );
  }

''',
        "dynamic mobile deck pan and zoom",
    )

    path.write_text(text, encoding="utf-8")
    print(f"Applied NEXO v1.4.2 mobile pan/zoom fixes: {path}")


if __name__ == "__main__":
    main()
