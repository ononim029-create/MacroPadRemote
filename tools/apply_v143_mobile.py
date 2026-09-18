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

    text = replace_once(
        text,
        """  Matrix4? _pendingDeckRestore;
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
        """  Matrix4? _pendingDeckRestore;
  Size _deckViewportSize = Size.zero;
  Size _deckCanvasSize = Size.zero;
  Size _deckModelSize = Size.zero;
  double _deckMinScale = 1.0;
  double _deckMaxScale = 2.0;
  bool _deckClampGuard = false;
  Offset _deckGestureCenterAnchor = Offset.zero;
  double _deckGestureScaleAnchor = 1.0;
  bool _deckGeometryInitialized = false;
  Offset _deckPreviousWorkOrigin = Offset.zero;
  Size _deckPreviousViewport = Size.zero;
  Size _deckPreviousCanvas = Size.zero;
  Offset _deckModelCenter = Offset.zero;
  double _workspaceLeftInset = 0;
  double _workspaceRightInset = 0;
  double _workspaceTopInset = 0;
  double _workspaceBottomInset = 0;
""",
        "v1.4.3 deck geometry state",
    )

    text = replace_between(
        text,
        "  void _fitDeck() {",
        "\n  @override\n  void didChangeDependencies() {",
        r'''  void _fitDeck() {
    _deckReturnController.stop();
    if (_deckViewportSize.isEmpty || _deckCanvasSize.isEmpty) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) {
          _fitDeck();
        }
      });
      return;
    }

    // Default view = exact center of the current work area + full fit of the
    // complete tile block. The limiting side (width or height) defines scale.
    final fitScale = min(
      _deckViewportSize.width / _deckCanvasSize.width,
      _deckViewportSize.height / _deckCanvasSize.height,
    ).clamp(0.02, _deckMaxScale).toDouble();

    _deckMinScale = fitScale;
    _deckModelCenter = Offset.zero;

    final begin = _deckTransform.value.clone();
    final target = Matrix4.diagonal3Values(fitScale, fitScale, 1)
      ..setTranslationRaw(0, 0, 0);

    _deckReturnAnimation = Matrix4Tween(begin: begin, end: target)
        .animate(CurvedAnimation(parent: _deckReturnController, curve: Curves.easeOutCubic));
    final resetFuture = _deckReturnController.forward(from: 0);
    resetFuture.whenComplete(() {
      if (mounted) {
        unawaited(_saveDeckView());
      }
    });
  }

''',
        "v1.4.3 default fit view",
    )

    text = replace_between(
        text,
        "  double _minimumDeckScale(int rows, int columns) {",
        "\n  Widget _remoteTile(TileSnapshot tile, double scale) {",
        r'''  double _maximumDeckZoomFactor(int rows, int columns) {
    final cellCount = max(1, rows * columns);
    // More cells allow a deeper close-up, while 1x1 still has a useful 2x zoom.
    return sqrt(cellCount * 2.0).clamp(2.0, 18.0).toDouble();
  }

  Size _calculateDeckModelSpace(Size deck, Size viewport) {
    if (deck.isEmpty || viewport.isEmpty) {
      return deck;
    }

    // Hidden model space area is always EXACTLY twice the tile-block area.
    // Its aspect ratio follows the current usable work area, but is clamped so
    // neither model-space dimension can become smaller than the tile block.
    final deckArea = deck.width * deck.height;
    final modelArea = deckArea * 2.0;
    final deckAspect = deck.width / deck.height;
    final workAspect = viewport.width / viewport.height;
    final minAspect = deckAspect / 2.0;
    final maxAspect = deckAspect * 2.0;
    final modelAspect = workAspect.clamp(minAspect, maxAspect).toDouble();

    final width = sqrt(modelArea * modelAspect);
    final height = sqrt(modelArea / modelAspect);
    return Size(width, height);
  }

  Matrix4 _matrixWithScaleAndCenter(double scale, Offset center) {
    return Matrix4.diagonal3Values(scale, scale, 1)
      ..setTranslationRaw(center.dx, center.dy, 0);
  }

  Matrix4 _boundedDeckMatrix(Matrix4 candidate) {
    if (_deckViewportSize.isEmpty || _deckCanvasSize.isEmpty || _deckModelSize.isEmpty) {
      return candidate;
    }

    final scale = candidate.getMaxScaleOnAxis().clamp(_deckMinScale, _deckMaxScale).toDouble();
    var tx = candidate.storage[12];
    var ty = candidate.storage[13];

    // The tile block must stay completely inside the hidden model-space rect.
    // Model space and tiles are scaled together, so its area remains 2x.
    final allowanceX = max(0.0, (_deckModelSize.width - _deckCanvasSize.width) * scale / 2);
    final allowanceY = max(0.0, (_deckModelSize.height - _deckCanvasSize.height) * scale / 2);

    tx = tx.clamp(_deckModelCenter.dx - allowanceX, _deckModelCenter.dx + allowanceX).toDouble();
    ty = ty.clamp(_deckModelCenter.dy - allowanceY, _deckModelCenter.dy + allowanceY).toDouble();

    return _matrixWithScaleAndCenter(scale, Offset(tx, ty));
  }

  Offset _keepDeckOutOfOpenedPanels(Offset center, double scale, Size viewport) {
    final transformedW = _deckCanvasSize.width * scale;
    final transformedH = _deckCanvasSize.height * scale;
    var x = center.dx;
    var y = center.dy;

    // A panel changes the block position only if it really overlaps the tiles.
    // When the whole block fits in the reduced work area, move it by the
    // minimum distance required to clear the panel edge.
    if (transformedW <= viewport.width) {
      final halfFreeX = (viewport.width - transformedW) / 2;
      x = x.clamp(-halfFreeX, halfFreeX).toDouble();
    }
    if (transformedH <= viewport.height) {
      final halfFreeY = (viewport.height - transformedH) / 2;
      y = y.clamp(-halfFreeY, halfFreeY).toDouble();
    }

    return Offset(x, y);
  }

  void _handleDeckGeometryChange({
    required Offset workOrigin,
    required Size viewport,
    required Size canvas,
    required int rows,
    required int columns,
  }) {
    if (viewport.isEmpty || canvas.isEmpty) {
      return;
    }

    _deckViewportSize = viewport;
    _deckCanvasSize = canvas;
    _deckModelSize = _calculateDeckModelSpace(canvas, viewport);

    final fit = min(viewport.width / canvas.width, viewport.height / canvas.height)
        .clamp(0.02, double.infinity)
        .toDouble();

    final current = _deckTransform.value;
    final rawScale = current.getMaxScaleOnAxis();
    var scale = rawScale;
    var center = Offset(current.storage[12], current.storage[13]);

    if (!_deckGeometryInitialized) {
      _deckMinScale = fit;
      _deckMaxScale = max(fit, fit * _maximumDeckZoomFactor(rows, columns));
      _deckGeometryInitialized = true;
      _deckPreviousWorkOrigin = workOrigin;
      _deckPreviousViewport = viewport;
      _deckPreviousCanvas = canvas;
      _deckModelCenter = Offset.zero;

      if (_pendingDeckRestore != null) {
        _applyPendingDeckRestore();
      } else {
        final target = _matrixWithScaleAndCenter(fit, Offset.zero);
        _deckTransform.value = target;
      }
      return;
    }

    final workChanged = (_deckPreviousWorkOrigin - workOrigin).distanceSquared > .01
        || (_deckPreviousViewport.width - viewport.width).abs() > .1
        || (_deckPreviousViewport.height - viewport.height).abs() > .1;
    final canvasChanged = (_deckPreviousCanvas.width - canvas.width).abs() > .1
        || (_deckPreviousCanvas.height - canvas.height).abs() > .1;

    // Panel geometry itself never forces a zoom jump.
    _deckMinScale = workChanged ? min(fit, rawScale) : fit;
    _deckMaxScale = max(_deckMinScale, fit * _maximumDeckZoomFactor(rows, columns));
    scale = scale.clamp(_deckMinScale, _deckMaxScale).toDouble();

    if (workChanged) {
      // Preserve the block's absolute screen position first. Opening a panel
      // therefore does NOT move tiles if the new panel does not overlap them.
      final oldScreenCenter = Offset(
        _deckPreviousWorkOrigin.dx + _deckPreviousViewport.width / 2 + center.dx,
        _deckPreviousWorkOrigin.dy + _deckPreviousViewport.height / 2 + center.dy,
      );
      center = Offset(
        oldScreenCenter.dx - workOrigin.dx - viewport.width / 2,
        oldScreenCenter.dy - workOrigin.dy - viewport.height / 2,
      );

      // Only an actual overlap causes a minimal corrective shift.
      center = _keepDeckOutOfOpenedPanels(center, scale, viewport);

      // Hidden model space follows the preserved position when its shape changes.
      // This prevents a harmless panel opening from causing an extra jump.
      _deckModelCenter = center;
    }

    if (canvasChanged && !workChanged) {
      // Grid size/count changed. Keep the current visual center but rebuild the
      // model space around the new block dimensions.
      _deckModelCenter = center;
      scale = max(scale, fit).clamp(_deckMinScale, _deckMaxScale).toDouble();
    }

    _deckPreviousWorkOrigin = workOrigin;
    _deckPreviousViewport = viewport;
    _deckPreviousCanvas = canvas;

    final next = _boundedDeckMatrix(_matrixWithScaleAndCenter(scale, center));
    _deckClampGuard = true;
    _deckTransform.value = next;
    _deckClampGuard = false;
  }

  void _clampDeckTransform() {
    if (_deckClampGuard || _deckViewportSize.isEmpty || _deckCanvasSize.isEmpty) {
      return;
    }

    final current = _deckTransform.value;
    final bounded = _boundedDeckMatrix(current);
    final changed = (current.getMaxScaleOnAxis() - bounded.getMaxScaleOnAxis()).abs() > .0005
        || (current.storage[12] - bounded.storage[12]).abs() > .2
        || (current.storage[13] - bounded.storage[13]).abs() > .2;
    if (!changed) {
      return;
    }

    _deckClampGuard = true;
    _deckTransform.value = bounded;
    _deckClampGuard = false;
  }

  void _applyPendingDeckRestore() {
    final pending = _pendingDeckRestore;
    if (pending == null || _deckViewportSize.isEmpty || _deckCanvasSize.isEmpty) {
      return;
    }

    _pendingDeckRestore = null;
    _deckReturnController.stop();
    final restoredScale = pending.getMaxScaleOnAxis().clamp(_deckMinScale, _deckMaxScale).toDouble();
    final restoredCenter = Offset(pending.storage[12], pending.storage[13]);
    _deckModelCenter = Offset.zero;
    _deckTransform.value = _boundedDeckMatrix(
      _matrixWithScaleAndCenter(restoredScale, restoredCenter),
    );
  }

  void _beginDeckInteraction() {
    _deckReturnController.stop();
    final current = _deckTransform.value;
    _deckGestureScaleAnchor = current.getMaxScaleOnAxis();
    _deckGestureCenterAnchor = Offset(current.storage[12], current.storage[13]);
  }

  void _updateDeckInteraction(ScaleUpdateDetails details) {
    if (_deckClampGuard) {
      return;
    }

    final current = _deckTransform.value;
    Matrix4 candidate;

    if (!scaleLocked && details.pointerCount > 1) {
      // Ignore InteractiveViewer's finger-centered translation completely.
      // Rebuild the transform from the gesture scale around the block center.
      final desiredScale = (_deckGestureScaleAnchor * details.scale)
          .clamp(_deckMinScale, _deckMaxScale)
          .toDouble();
      candidate = _matrixWithScaleAndCenter(desiredScale, _deckGestureCenterAnchor);
    } else {
      candidate = current;
    }

    final bounded = _boundedDeckMatrix(candidate);
    _deckClampGuard = true;
    _deckTransform.value = bounded;
    _deckClampGuard = false;
  }

  Widget _deckCanvas(ProfileSnapshot p) {
    return LayoutBuilder(
      builder: (_, constraints) {
        final columns = p.columns.clamp(1, 12).toInt();
        final rows = p.rows.clamp(1, 12).toInt();
        const gapBase = 7.0;
        const padBase = 10.0;
        final compact = widget.formFactor == ClientFormFactor.phone
            && MediaQuery.orientationOf(context) == Orientation.landscape;

        // Reconstruct the full deck area before auxiliary panels reduced it.
        // Tile base size must remain stable when a panel merely opens/closes.
        final baseViewportW = constraints.maxWidth + _workspaceLeftInset + _workspaceRightInset;
        final baseViewportH = constraints.maxHeight + _workspaceTopInset + _workspaceBottomInset;
        final availableW =
            (baseViewportW - padBase * 2 - gapBase * (columns - 1)).clamp(1.0, double.infinity);
        final availableH =
            (baseViewportH - padBase * 2 - gapBase * (rows - 1)).clamp(1.0, double.infinity);
        final fitW = availableW / columns;
        final fitH = availableH / rows;
        final cellW = min(fitW, fitH / .76).clamp(18.0, 150.0);
        final cellH = cellW * .76;
        final uiScale = (cellW / 105).clamp(.38, 1.18);
        final packed = packTiles(p.tiles, rows, columns);
        final totalW = padBase * 2 + columns * cellW + (columns - 1) * gapBase;
        final totalH = padBase * 2 + rows * cellH + (rows - 1) * gapBase;
        final viewport = Size(constraints.maxWidth, constraints.maxHeight);
        final canvasSize = Size(totalW, totalH);
        final workOrigin = Offset(_workspaceLeftInset, _workspaceTopInset);

        final fitScale = min(viewport.width / totalW, viewport.height / totalH)
            .clamp(0.02, double.infinity)
            .toDouble();
        final maxScale = max(fitScale, fitScale * _maximumDeckZoomFactor(rows, columns));

        // Update values immediately so InteractiveViewer gets correct limits in
        // this frame, then reconcile positions after layout completes.
        _deckViewportSize = viewport;
        _deckCanvasSize = canvasSize;
        _deckModelSize = _calculateDeckModelSpace(canvasSize, viewport);
        final currentScale = _deckTransform.value.getMaxScaleOnAxis();
        final geometryAlreadyKnown = _deckGeometryInitialized;
        _deckMinScale = geometryAlreadyKnown ? min(fitScale, currentScale) : fitScale;
        _deckMaxScale = max(maxScale, _deckMinScale);

        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (!mounted) {
            return;
          }
          _handleDeckGeometryChange(
            workOrigin: workOrigin,
            viewport: viewport,
            canvas: canvasSize,
            rows: rows,
            columns: columns,
          );
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

        final interactionMargin = max(
              max(_deckModelSize.width, _deckModelSize.height) * _deckMaxScale,
              max(viewport.width, viewport.height),
            ) +
            max(viewport.width, viewport.height);

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
              onInteractionStart: (_) => _beginDeckInteraction(),
              onInteractionUpdate: _updateDeckInteraction,
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
        "v1.4.3 centered zoom and model space",
    )

    path.write_text(text, encoding="utf-8")
    print(f"Applied NEXO v1.4.3 model-space/centered-zoom fixes: {path}")


if __name__ == "__main__":
    main()
