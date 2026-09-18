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
        "\n  void _fitDeck() {",
        r'''  Size _realModelSpaceSize(Size deck, Size viewport) {
    if (deck.isEmpty || viewport.isEmpty) {
      return deck;
    }

    // Exact invariant requested by the user:
    // S(model space) = 2 * S(tile block).
    final blockArea = deck.width * deck.height;
    final modelArea = blockArea * 2.0;
    final blockAspect = deck.width / deck.height;
    final workspaceAspect = viewport.width / viewport.height;

    // These limits guarantee that model width/height never become smaller
    // than the tile block while still following the work-area proportions.
    final modelAspect = workspaceAspect
        .clamp(blockAspect / 2.0, blockAspect * 2.0)
        .toDouble();

    return Size(
      sqrt(modelArea * modelAspect),
      sqrt(modelArea / modelAspect),
    );
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
    final verticalAllowance = max(
      0.0,
      (model.height - canvas.height) * scale / 2,
    );
    final desiredUp = viewport.height * .13;
    return Offset(0, -min(desiredUp, verticalAllowance));
  }

''',
        "exact 2x-area model helpers",
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
        .animate(CurvedAnimation(
          parent: _deckReturnController,
          curve: Curves.easeOutCubic,
        ));
    final resetFuture = _deckReturnController.forward(from: 0);
    resetFuture.whenComplete(() {
      if (mounted) {
        unawaited(_saveDeckView());
      }
    });
  }

''',
        "exact 2x-area default view",
    )

    text = replace_between(
        text,
        "  Matrix4 _boundedDeckMatrix(Matrix4 candidate) {",
        "\n  Offset _clearActualPanelOverlap(Offset center, double scale, Size viewport) {",
        r'''  Matrix4 _boundedDeckMatrix(Matrix4 candidate) {
    if (_deckViewportSize.isEmpty || _deckCanvasSize.isEmpty) {
      return candidate;
    }

    final scale = candidate.getMaxScaleOnAxis()
        .clamp(_deckMinScale, _deckMaxScale)
        .toDouble();
    var center = Offset(candidate.storage[12], candidate.storage[13]);
    final model = _realModelSpaceSize(
      _deckCanvasSize,
      _deckViewportSize,
    );

    // The entire tile block remains inside the hidden model-space rectangle.
    final allowanceX = max(
      0.0,
      (model.width - _deckCanvasSize.width) * scale / 2,
    );
    final allowanceY = max(
      0.0,
      (model.height - _deckCanvasSize.height) * scale / 2,
    );

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

''',
        "exact model bounds",
    )

    text = replace_between(
        text,
        "  Offset _clearActualPanelOverlap(Offset center, double scale, Size viewport) {",
        "\n  void _handleDeckGeometryChange({",
        r'''  Offset _clearActualPanelOverlap(Offset center, double scale, Size viewport) {
    final halfW = _deckCanvasSize.width * scale / 2;
    final halfH = _deckCanvasSize.height * scale / 2;
    var x = center.dx;
    var y = center.dy;

    // The usable viewport already excludes open panels. Correct position only
    // when the tile rectangle actually crosses the newly available edge.
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
    final allowanceX = max(
      0.0,
      (model.width - canvas.width) * scale / 2,
    );
    final allowanceY = max(
      0.0,
      (model.height - canvas.height) * scale / 2,
    );

    return Offset(
      preferredModelCenter.dx
          .clamp(blockCenter.dx - allowanceX, blockCenter.dx + allowanceX)
          .toDouble(),
      preferredModelCenter.dy
          .clamp(blockCenter.dy - allowanceY, blockCenter.dy + allowanceY)
          .toDouble(),
    );
  }

''',
        "panel overlap and model center",
    )

    text = replace_between(
        text,
        "  void _handleDeckGeometryChange({",
        "\n  void _clampDeckTransform() {",
        r'''  void _handleDeckGeometryChange({
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

    // A panel opening/closing must not cause an automatic zoom jump.
    _deckMinScale = workChanged ? min(zeroScale, rawScale) : zeroScale;
    _deckMaxScale = max(
      _deckMinScale,
      zeroScale * _maximumDeckZoomFactor(rows, columns),
    );
    final scale = rawScale
        .clamp(_deckMinScale, _deckMaxScale)
        .toDouble();

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
      // Preserve absolute screen position first, so a panel that does not
      // overlap the tiles does not move them.
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

      // Reshape/recenter the hidden model around the preserved block when
      // necessary instead of moving the visible block for no reason.
      modelCenter = _modelCenterThatContainsBlock(
        modelCenter,
        blockCenter,
        scale,
        canvas,
        viewport,
      );

      // Only actual intersection with the reduced visible work area moves it.
      final cleared = _clearActualPanelOverlap(
        blockCenter,
        scale,
        viewport,
      );
      final correction = cleared - blockCenter;
      blockCenter = cleared;
      modelCenter += correction;
    }

    if (canvasChanged && !workChanged) {
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

''',
        "exact model geometry changes",
    )

    text = replace_between(
        text,
        "  void _applyPendingDeckRestore() {",
        "\n  void _beginDeckInteraction(ScaleStartDetails details) {",
        r'''  void _applyPendingDeckRestore() {
    final pending = _pendingDeckRestore;
    if (pending == null || _deckViewportSize.isEmpty || _deckCanvasSize.isEmpty) {
      return;
    }

    _pendingDeckRestore = null;
    _deckReturnController.stop();
    final zeroScale = _defaultDeckScale(
      _deckViewportSize,
      _deckCanvasSize,
    );
    final restoredScale = pending.getMaxScaleOnAxis()
        .clamp(zeroScale, _deckMaxScale)
        .toDouble();
    final restoredCenter = Offset(
      pending.storage[12],
      pending.storage[13],
    );

    _deckModelCenter = _modelCenterThatContainsBlock(
      Offset.zero,
      restoredCenter,
      restoredScale,
      _deckCanvasSize,
      _deckViewportSize,
    );
    _deckTransform.value = _boundedDeckMatrix(
      _matrixWithScaleAndCenter(
        restoredScale,
        restoredCenter,
      ),
    );
  }

''',
        "restore exact model space",
    )

    text = replace_between(
        text,
        "  void _beginDeckInteraction(ScaleStartDetails details) {",
        "\n  void _updateDeckInteraction(ScaleUpdateDetails details) {",
        r'''  void _beginDeckInteraction(ScaleStartDetails details) {
    _deckReturnController.stop();
    final current = _deckTransform.value;
    _deckGestureScaleAnchor = current.getMaxScaleOnAxis();
    _deckGestureCenterAnchor = Offset(
      current.storage[12],
      current.storage[13],
    );
    _deckGestureFocalAnchor = details.focalPoint;
    _deckGestureScaleFactorAnchor = 1.0;
    _deckGesturePointerCount = 0;
  }

''',
        "gesture start anchors",
    )

    text = replace_between(
        text,
        "  void _updateDeckInteraction(ScaleUpdateDetails details) {",
        "\n  Widget _deckCanvas(ProfileSnapshot p) {",
        r'''  void _updateDeckInteraction(ScaleUpdateDetails details) {
    if (_deckClampGuard) {
      return;
    }

    final current = _deckTransform.value;

    // When a second finger is added/removed, use the CURRENT state as the new
    // anchor. This prevents jumps between pan and zoom.
    if (_deckGesturePointerCount != details.pointerCount) {
      _deckGesturePointerCount = details.pointerCount;
      _deckGestureScaleAnchor = current.getMaxScaleOnAxis();
      _deckGestureCenterAnchor = Offset(
        current.storage[12],
        current.storage[13],
      );
      _deckGestureFocalAnchor = details.focalPoint;
      _deckGestureScaleFactorAnchor = details.scale;
      return;
    }

    var scale = _deckGestureScaleAnchor;
    var center = _deckGestureCenterAnchor;

    if (!scaleLocked && details.pointerCount > 1) {
      // Multi-touch changes scale ONLY. Tile-block center stays fixed.
      final factor = _deckGestureScaleFactorAnchor == 0
          ? 1.0
          : details.scale / _deckGestureScaleFactorAnchor;
      scale = (_deckGestureScaleAnchor * factor)
          .clamp(_deckMinScale, _deckMaxScale)
          .toDouble();
    } else if (!panLocked && details.pointerCount == 1) {
      // One finger changes position ONLY.
      center = _deckGestureCenterAnchor
          + (details.focalPoint - _deckGestureFocalAnchor);
    }

    _deckClampGuard = true;
    _deckTransform.value = _boundedDeckMatrix(
      _matrixWithScaleAndCenter(scale, center),
    );
    _deckClampGuard = false;
  }

''',
        "seamless pan zoom switching",
    )

    path.write_text(text, encoding="utf-8")
    print(f"Applied NEXO v1.4.5 exact 2x-area model-space fixes: {path}")


if __name__ == "__main__":
    main()
