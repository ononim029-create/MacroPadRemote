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
        """  Offset _deckGestureFocalAnchor = Offset.zero;
  double _deckGestureScaleAnchor = 1.0;
  bool _deckGeometryInitialized = false;
""",
        """  Offset _deckGestureFocalAnchor = Offset.zero;
  double _deckGestureScaleAnchor = 1.0;
  double _deckGestureScaleFactorAnchor = 1.0;
  int _deckGesturePointerCount = 0;
  bool _deckGeometryInitialized = false;
""",
        "gesture transition anchors",
    )

    text = replace_between(
        text,
        "  Offset _defaultModelCenter(Size viewport, Size canvas, double scale) {",
        "\n  Widget _remoteTile(TileSnapshot tile, double scale) {",
        r'''  Size _realModelSpaceSize(Size deck, Size viewport) {
    if (deck.isEmpty || viewport.isEmpty) {
      return deck;
    }

    // User-defined invariant: S(model) = 2 * S(tile block), exactly.
    // The aspect ratio follows the current usable workspace as far as possible,
    // while both model dimensions are guaranteed to remain >= the tile block.
    final blockArea = deck.width * deck.height;
    final modelArea = blockArea * 2.0;
    final blockAspect = deck.width / deck.height;
    final workspaceAspect = viewport.width / viewport.height;
    final modelAspect = workspaceAspect
        .clamp(blockAspect / 2.0, blockAspect * 2.0)
        .toDouble();

    return Size(
      sqrt(modelArea * modelAspect),
      sqrt(modelArea / modelAspect),
    );
  }

  double _maximumDeckZoomFactor(int rows, int columns) {
    final cellCount = max(1, rows * columns);
    return sqrt(cellCount * 2.0).clamp(2.0, 18.0).toDouble();
  }

  double _defaultDeckScale(Size viewport, Size canvas) {
    final model = _realModelSpaceSize(canvas, viewport);
    return min(
      viewport.width / model.width,
      viewport.height / model.height,
    ).clamp(0.02, double.infinity).toDouble();
  }

  Offset _defaultBlockCenter(Size viewport, Size canvas, double scale) {
    final model = _realModelSpaceSize(canvas, viewport);
    final verticalAllowance = max(0.0, (model.height - canvas.height) * scale / 2);
    final desiredUp = viewport.height * .13;
    return Offset(0, -min(desiredUp, verticalAllowance));
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
    final model = _realModelSpaceSize(_deckCanvasSize, _deckViewportSize);

    // The whole tile block must remain inside the hidden model-space rectangle.
    final allowanceX = max(0.0, (model.width - _deckCanvasSize.width) * scale / 2);
    final allowanceY = max(0.0, (model.height - _deckCanvasSize.height) * scale / 2);

    center = Offset(
      center.dx.clamp(
        _deckModelCenter.dx - allowanceX,
        _deckModelCenter.dx + allowanceX,
      ).toDouble(),
      center.dy.clamp(
        _deckModelCenter.dy - allowanceY,
        _deckModelCenter.dy + allowanceY,
      ).toDouble(),
    );

    return _matrixWithScaleAndCenter(scale, center);
  }

  Offset _clearActualPanelOverlap(Offset center, double scale, Size viewport) {
    final halfW = _deckCanvasSize.width * scale / 2;
    final halfH = _deckCanvasSize.height * scale / 2;
    var x = center.dx;
    var y = center.dy;

    // The usable viewport already excludes opened auxiliary panels.
    // Shift only when the tile rectangle ACTUALLY crosses that viewport edge.
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

  Offset _modelCenterThatContainsBlock(
    Offset preferredModelCenter,
    Offset blockCenter,
    double scale,
    Size canvas,
    Size viewport,
  ) {
    final model = _realModelSpaceSize(canvas, viewport);
    final allowanceX = max(0.0, (model.width - canvas.width) * scale / 2);
    final allowanceY = max(0.0, (model.height - canvas.height) * scale / 2);

    return Offset(
      preferredModelCenter.dx
          .clamp(blockCenter.dx - allowanceX, blockCenter.dx + allowanceX)
          .toDouble(),
      preferredModelCenter.dy
          .clamp(blockCenter.dy - allowanceY, blockCenter.dy + allowanceY)
          .toDouble(),
    );
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

    final zeroScale = _defaultDeckScale(viewport, canvas);
    final current = _deckTransform.value;
    final rawScale = current.getMaxScaleOnAxis();

    final workChanged = !_deckPreviousViewport.isEmpty
        && ((previousOrigin - workOrigin).distanceSquared > .01
            || (previousViewport.width - viewport.width).abs() > .1
            || (previousViewport.height - viewport.height).abs() > .1);
    final canvasChanged = (_deckPreviousCanvas.width - canvas.width).abs() > .1
        || (_deckPreviousCanvas.height - canvas.height).abs() > .1;

    // Opening/closing a panel never forces a zoom jump.
    _deckMinScale = workChanged ? min(zeroScale, rawScale) : zeroScale;
    _deckMaxScale = max(
      _deckMinScale,
      zeroScale * _maximumDeckZoomFactor(rows, columns),
    );
    final scale = rawScale.clamp(_deckMinScale, _deckMaxScale).toDouble();

    if (!_deckGeometryInitialized) {
      _deckGeometryInitialized = true;
      _deckPreviousWorkOrigin = workOrigin;
      _deckPreviousViewport = viewport;
      _deckPreviousCanvas = canvas;
      _deckModelCenter = Offset.zero;

      if (_pendingDeckRestore != null) {
        _applyPendingDeckRestore();
      } else {
        _deckTransform.value = _matrixWithScaleAndCenter(
          zeroScale,
          _defaultBlockCenter(viewport, canvas, zeroScale),
        );
      }
      return;
    }

    var blockCenter = Offset(current.storage[12], current.storage[13]);
    var modelCenter = previousModelCenter;

    if (workChanged && !previousViewport.isEmpty) {
      // Keep absolute screen coordinates first. A panel that does not overlap
      // the tiles therefore produces no visual movement at all.
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

      // Reshape the hidden model space around the preserved block if needed,
      // instead of moving the block merely because panel geometry changed.
      modelCenter = _modelCenterThatContainsBlock(
        modelCenter,
        blockCenter,
        scale,
        canvas,
        viewport,
      );

      // Only real overlap with the newly reduced work area causes movement.
      final cleared = _clearActualPanelOverlap(blockCenter, scale, viewport);
      final correction = cleared - blockCenter;
      blockCenter = cleared;
      modelCenter += correction;
    }

    if (canvasChanged && !workChanged) {
      // Grid count/size changed: rebuild the 2x-area model around the current
      // visual location without an arbitrary snap.
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

    _deckClampGuard = true;
    _deckTransform.value = _boundedDeckMatrix(_deckTransform.value);
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
    final restoredScale = pending.getMaxScaleOnAxis()
        .clamp(zeroScale, _deckMaxScale)
        .toDouble();
    final restoredCenter = Offset(pending.storage[12], pending.storage[13]);

    _deckModelCenter = _modelCenterThatContainsBlock(
      Offset.zero,
      restoredCenter,
      restoredScale,
      _deckCanvasSize,
      _deckViewportSize,
    );
    _deckTransform.value = _boundedDeckMatrix(
      _matrixWithScaleAndCenter(restoredScale, restoredCenter),
    );
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
    _deckModelCenter = Offset.zero;

    final begin = _deckTransform.value.clone();
    final target = _matrixWithScaleAndCenter(
      fitScale,
      _defaultBlockCenter(_deckViewportSize, _deckCanvasSize, fitScale),
    );
    _deckReturnAnimation = Matrix4Tween(begin: begin, end: target)
        .animate(CurvedAnimation(parent: _deckReturnController, curve: Curves.easeOutCubic));
    final resetFuture = _deckReturnController.forward(from: 0);
    resetFuture.whenComplete(() {
      if (mounted) {
        unawaited(_saveDeckView());
      }
    });
  }

  void _beginDeckInteraction(ScaleStartDetails details) {
    _deckReturnController.stop();
    final current = _deckTransform.value;
    _deckGestureScaleAnchor = current.getMaxScaleOnAxis();
    _deckGestureCenterAnchor = Offset(current.storage[12], current.storage[13]);
    _deckGestureFocalAnchor = details.focalPoint;
    _deckGestureScaleFactorAnchor = 1.0;
    _deckGesturePointerCount = 0;
  }

  void _updateDeckInteraction(ScaleUpdateDetails details) {
    if (_deckClampGuard) {
      return;
    }

    final current = _deckTransform.value;

    if (_deckGesturePointerCount != details.pointerCount) {
      _deckGesturePointerCount = details.pointerCount;
      _deckGestureScaleAnchor = current.getMaxScaleOnAxis();
      _deckGestureCenterAnchor = Offset(current.storage[12], current.storage[13]);
      _deckGestureFocalAnchor = details.focalPoint;
      _deckGestureScaleFactorAnchor = details.scale;
      return;
    }

    var scale = _deckGestureScaleAnchor;
    var center = _deckGestureCenterAnchor;

    if (!scaleLocked && details.pointerCount > 1) {
      // Multi-touch changes ONLY scale. The full tile-block center is fixed.
      final factor = _deckGestureScaleFactorAnchor == 0
          ? 1.0
          : details.scale / _deckGestureScaleFactorAnchor;
      scale = (_deckGestureScaleAnchor * factor)
          .clamp(_deckMinScale, _deckMaxScale)
          .toDouble();
    } else if (!panLocked && details.pointerCount == 1) {
      // Single touch changes ONLY position.
      center = _deckGestureCenterAnchor + (details.focalPoint - _deckGestureFocalAnchor);
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

        // Cell geometry is based on the full pre-panel workspace. Panels can
        // shrink the usable work area but never resize the tiles themselves.
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
        final currentScale = _deckTransform.value.getMaxScaleOnAxis();

        _deckViewportSize = viewport;
        _deckCanvasSize = canvasSize;
        _deckMinScale = _deckGeometryInitialized ? min(zeroScale, currentScale) : zeroScale;
        _deckMaxScale = max(
          _deckMinScale,
          zeroScale * _maximumDeckZoomFactor(rows, columns),
        );

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
        "real model area exactly 2x",
    )

    path.write_text(text, encoding="utf-8")
    print(f"Applied NEXO v1.4.5 exact 2x-area model-space fixes: {path}")


if __name__ == "__main__":
    main()
