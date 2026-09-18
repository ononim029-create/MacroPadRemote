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
        """  Offset _deckGestureCenterAnchor = Offset.zero;
  double _deckGestureScaleAnchor = 1.0;
  bool _deckGeometryInitialized = false;
""",
        """  Offset _deckGestureCenterAnchor = Offset.zero;
  Offset _deckGestureFocalAnchor = Offset.zero;
  double _deckGestureScaleAnchor = 1.0;
  bool _deckGeometryInitialized = false;
""",
        "v1.4.4 gesture focal anchor",
    )

    text = replace_between(
        text,
        "  void _fitDeck() {",
        "\n  @override\n  void didChangeDependencies() {",
        r'''  Offset _defaultModelCenter(Size viewport, Size canvas, double scale) {
    // Stream Deck-like zero position: horizontally centered and slightly above
    // the geometric middle, but never so high that the whole hidden model-space
    // rectangle would leave the usable work area.
    final modelHalfHeight = canvas.height * scale; // model height = 2 x deck height
    final availableUp = max(0.0, viewport.height / 2 - modelHalfHeight);
    final desiredUp = viewport.height * .13;
    return Offset(0, -min(desiredUp, availableUp));
  }

  double _defaultDeckScale(Size viewport, Size canvas) {
    // At zero position the hidden model space is exactly 2x the deck in both
    // dimensions and the ENTIRE model space fits into the current work area.
    return min(
      viewport.width / (canvas.width * 2),
      viewport.height / (canvas.height * 2),
    ).clamp(0.02, double.infinity).toDouble();
  }

  void _fitDeck() {
    _deckReturnController.stop();
    if (_deckViewportSize.isEmpty || _deckCanvasSize.isEmpty) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) {
          _fitDeck();
        }
      });
      return;
    }

    final fitScale = _defaultDeckScale(_deckViewportSize, _deckCanvasSize);
    _deckMinScale = fitScale;
    _deckMaxScale = max(_deckMaxScale, fitScale * 2);
    _deckModelSize = Size(_deckCanvasSize.width * 2, _deckCanvasSize.height * 2);
    _deckModelCenter = _defaultModelCenter(_deckViewportSize, _deckCanvasSize, fitScale);

    final begin = _deckTransform.value.clone();
    final target = _matrixWithScaleAndCenter(fitScale, _deckModelCenter);
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
        "v1.4.4 default view",
    )

    text = replace_between(
        text,
        "  double _maximumDeckZoomFactor(int rows, int columns) {",
        "\n  Widget _remoteTile(TileSnapshot tile, double scale) {",
        r'''  double _maximumDeckZoomFactor(int rows, int columns) {
    final cellCount = max(1, rows * columns);
    return sqrt(cellCount * 2.0).clamp(2.0, 18.0).toDouble();
  }

  Matrix4 _matrixWithScaleAndCenter(double scale, Offset center) {
    return Matrix4.diagonal3Values(scale, scale, 1)
      ..setTranslationRaw(center.dx, center.dy, 0);
  }

  Matrix4 _boundedDeckMatrix(Matrix4 candidate) {
    if (_deckViewportSize.isEmpty || _deckCanvasSize.isEmpty) {
      return candidate;
    }

    final scale = candidate.getMaxScaleOnAxis().clamp(_deckMinScale, _deckMaxScale).toDouble();
    var center = Offset(candidate.storage[12], candidate.storage[13]);

    // REAL hidden model space: exactly 2x tile-block width and 2x tile-block
    // height. Because the block itself is centered in that model space at zero,
    // it may move by at most half of its own transformed dimensions.
    _deckModelSize = Size(_deckCanvasSize.width * 2, _deckCanvasSize.height * 2);
    final allowance = Offset(
      _deckCanvasSize.width * scale / 2,
      _deckCanvasSize.height * scale / 2,
    );

    center = Offset(
      center.dx.clamp(
        _deckModelCenter.dx - allowance.dx,
        _deckModelCenter.dx + allowance.dx,
      ).toDouble(),
      center.dy.clamp(
        _deckModelCenter.dy - allowance.dy,
        _deckModelCenter.dy + allowance.dy,
      ).toDouble(),
    );

    return _matrixWithScaleAndCenter(scale, center);
  }

  Offset _clearActualPanelOverlap(Offset center, double scale, Size viewport) {
    final halfW = _deckCanvasSize.width * scale / 2;
    final halfH = _deckCanvasSize.height * scale / 2;
    var x = center.dx;
    var y = center.dy;

    // Do not move anything just because a panel opened. Shift only when the
    // current block rectangle really falls outside the newly usable rectangle.
    if (halfW * 2 <= viewport.width) {
      x = x.clamp(
        -viewport.width / 2 + halfW,
        viewport.width / 2 - halfW,
      ).toDouble();
    }
    if (halfH * 2 <= viewport.height) {
      y = y.clamp(
        -viewport.height / 2 + halfH,
        viewport.height / 2 - halfH,
      ).toDouble();
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

    final previousViewport = _deckPreviousViewport;
    final previousOrigin = _deckPreviousWorkOrigin;
    final previousModelCenter = _deckModelCenter;

    _deckViewportSize = viewport;
    _deckCanvasSize = canvas;
    _deckModelSize = Size(canvas.width * 2, canvas.height * 2);

    final zeroScale = _defaultDeckScale(viewport, canvas);
    final current = _deckTransform.value;
    final rawScale = current.getMaxScaleOnAxis();
    final scale = rawScale.clamp(
      min(zeroScale, rawScale),
      max(zeroScale * _maximumDeckZoomFactor(rows, columns), zeroScale),
    ).toDouble();

    final workChangedPrecheck = !_deckPreviousViewport.isEmpty
        && ((_deckPreviousWorkOrigin - workOrigin).distanceSquared > .01
            || (_deckPreviousViewport.width - viewport.width).abs() > .1
            || (_deckPreviousViewport.height - viewport.height).abs() > .1);
    _deckMinScale = workChangedPrecheck ? min(zeroScale, rawScale) : zeroScale;
    _deckMaxScale = max(_deckMinScale, zeroScale * _maximumDeckZoomFactor(rows, columns));

    if (!_deckGeometryInitialized) {
      _deckGeometryInitialized = true;
      _deckPreviousWorkOrigin = workOrigin;
      _deckPreviousViewport = viewport;
      _deckPreviousCanvas = canvas;
      _deckModelCenter = _defaultModelCenter(viewport, canvas, zeroScale);

      if (_pendingDeckRestore != null) {
        _applyPendingDeckRestore();
      } else {
        _deckTransform.value = _matrixWithScaleAndCenter(zeroScale, _deckModelCenter);
      }
      return;
    }

    var blockCenter = Offset(current.storage[12], current.storage[13]);
    var modelCenter = previousModelCenter;

    final workChanged = (previousOrigin - workOrigin).distanceSquared > .01
        || (previousViewport.width - viewport.width).abs() > .1
        || (previousViewport.height - viewport.height).abs() > .1;
    final canvasChanged = (_deckPreviousCanvas.width - canvas.width).abs() > .1
        || (_deckPreviousCanvas.height - canvas.height).abs() > .1;

    if (workChanged && !previousViewport.isEmpty) {
      // Preserve ABSOLUTE screen position. Therefore a remote panel does not
      // move tiles at all when it does not overlap them.
      final oldBlockScreenCenter = Offset(
        previousOrigin.dx + previousViewport.width / 2 + blockCenter.dx,
        previousOrigin.dy + previousViewport.height / 2 + blockCenter.dy,
      );
      final oldModelScreenCenter = Offset(
        previousOrigin.dx + previousViewport.width / 2 + modelCenter.dx,
        previousOrigin.dy + previousViewport.height / 2 + modelCenter.dy,
      );

      blockCenter = Offset(
        oldBlockScreenCenter.dx - workOrigin.dx - viewport.width / 2,
        oldBlockScreenCenter.dy - workOrigin.dy - viewport.height / 2,
      );
      modelCenter = Offset(
        oldModelScreenCenter.dx - workOrigin.dx - viewport.width / 2,
        oldModelScreenCenter.dy - workOrigin.dy - viewport.height / 2,
      );

      final cleared = _clearActualPanelOverlap(blockCenter, scale, viewport);
      final correction = cleared - blockCenter;
      blockCenter = cleared;
      modelCenter += correction;
    }

    if (canvasChanged && !workChanged) {
      // Grid count/size changed: rebuild the hidden 2x model around the current
      // visual center without snapping to the default position.
      modelCenter = blockCenter;
    }

    _deckModelCenter = modelCenter;
    _deckPreviousWorkOrigin = workOrigin;
    _deckPreviousViewport = viewport;
    _deckPreviousCanvas = canvas;

    _deckClampGuard = true;
    _deckTransform.value = _boundedDeckMatrix(
      _matrixWithScaleAndCenter(scale, blockCenter),
    );
    _deckClampGuard = false;
  }

  void _clampDeckTransform() {
    if (_deckClampGuard || _deckViewportSize.isEmpty || _deckCanvasSize.isEmpty) {
      return;
    }
    final bounded = _boundedDeckMatrix(_deckTransform.value);
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
    final zeroScale = _defaultDeckScale(_deckViewportSize, _deckCanvasSize);
    final restoredScale = pending.getMaxScaleOnAxis().clamp(
      zeroScale,
      _deckMaxScale,
    ).toDouble();
    _deckModelCenter = _defaultModelCenter(_deckViewportSize, _deckCanvasSize, zeroScale);
    _deckTransform.value = _boundedDeckMatrix(
      _matrixWithScaleAndCenter(
        restoredScale,
        Offset(pending.storage[12], pending.storage[13]),
      ),
    );
  }

  void _beginDeckInteraction(ScaleStartDetails details) {
    _deckReturnController.stop();
    final current = _deckTransform.value;
    _deckGestureScaleAnchor = current.getMaxScaleOnAxis();
    _deckGestureCenterAnchor = Offset(current.storage[12], current.storage[13]);
    _deckGestureFocalAnchor = details.focalPoint;
  }

  void _updateDeckInteraction(ScaleUpdateDetails details) {
    if (_deckClampGuard) {
      return;
    }

    var scale = _deckGestureScaleAnchor;
    var center = _deckGestureCenterAnchor;

    if (!scaleLocked && details.pointerCount > 1) {
      // Two fingers control ONLY zoom. Focus is rigidly fixed at the geometric
      // center of the complete tile block; finger position never translates it.
      scale = (_deckGestureScaleAnchor * details.scale)
          .clamp(_deckMinScale, _deckMaxScale)
          .toDouble();
    } else if (!panLocked && details.pointerCount == 1) {
      // One finger controls ONLY movement.
      final delta = details.focalPoint - _deckGestureFocalAnchor;
      center = _deckGestureCenterAnchor + delta;
    }

    _deckClampGuard = true;
    _deckTransform.value = _boundedDeckMatrix(
      _matrixWithScaleAndCenter(scale, center),
    );
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

        // Base tile size is derived from the FULL deck area, not from a panel-
        // reduced viewport. Opening a panel can never resize the tiles itself.
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
        final zeroScale = _defaultDeckScale(viewport, canvasSize);
        final maxScale = zeroScale * _maximumDeckZoomFactor(rows, columns);

        _deckViewportSize = viewport;
        _deckCanvasSize = canvasSize;
        _deckModelSize = Size(totalW * 2, totalH * 2);
        _deckMinScale = zeroScale;
        _deckMaxScale = max(zeroScale, maxScale);

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

        return Stack(children: [
          Positioned.fill(
            child: GestureDetector(
              behavior: HitTestBehavior.translucent,
              onScaleStart: _beginDeckInteraction,
              onScaleUpdate: _updateDeckInteraction,
              onScaleEnd: (_) {
                _clampDeckTransform();
                unawaited(_saveDeckView());
                unawaited(_saveWorkspaceUi());
              },
              child: ClipRect(
                child: AnimatedBuilder(
                  animation: _deckTransform,
                  child: canvas,
                  builder: (_, child) {
                    final matrix = _deckTransform.value;
                    final scale = matrix.getMaxScaleOnAxis();
                    final center = Offset(matrix.storage[12], matrix.storage[13]);
                    return Center(
                      child: Transform.translate(
                        offset: center,
                        child: Transform.scale(
                          scale: scale,
                          alignment: Alignment.center,
                          child: child,
                        ),
                      ),
                    );
                  },
                ),
              ),
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
        "v1.4.4 real hidden model space",
    )

    path.write_text(text, encoding="utf-8")
    print(f"Applied NEXO v1.4.4 real model-space fixes: {path}")


if __name__ == "__main__":
    main()
