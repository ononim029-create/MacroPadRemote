from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_between(text: str, start: str, end: str, replacement: str, label: str) -> str:
    a = text.find(start)
    if a < 0:
        raise RuntimeError(f"{label}: start marker not found")
    b = text.find(end, a + len(start))
    if b < 0:
        raise RuntimeError(f"{label}: end marker not found")
    return text[:a] + replacement + text[b:]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)


def main() -> None:
    path = ROOT / "src/mobile/macropad_mobile/lib/main.dart"
    text = path.read_text(encoding="utf-8")

    # Keep the Deck widget full-size at all times. Auxiliary panels are overlays;
    # their dimensions only define an invisible usable rectangle. This removes
    # the one-frame re-layout jump when a panel opens/closes.
    text = replace_between(
        text,
        "  Widget _workspaceBody(List<Widget> pages, bool compact) {",
        "\n  Widget _controlOverlay(Widget child, {required bool showKeyboard}) {",
        r'''  Widget _workspaceBody(List<Widget> pages, bool compact) {
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

    final leftPanel = (profileRailVisible && profileDock == ProfileDockSide.left ? 48.0 : 0.0)
        + (bottomNavVisible && navDock == ProfileDockSide.left ? 52.0 : 0.0);
    final rightPanel = (profileRailVisible && profileDock == ProfileDockSide.right ? 48.0 : 0.0)
        + (bottomNavVisible && navDock == ProfileDockSide.right ? 52.0 : 0.0);
    final topPanel = (profileRailVisible && profileDock == ProfileDockSide.top ? 48.0 : 0.0)
        + (bottomNavVisible && navDock == ProfileDockSide.top ? 52.0 : 0.0);

    final leftControls =
        profileDock == ProfileDockSide.left || navDock == ProfileDockSide.left ? 30.0 : 0.0;
    final rightControls =
        profileDock == ProfileDockSide.right || navDock == ProfileDockSide.right ? 30.0 : 0.0;
    final topControls =
        profileDock == ProfileDockSide.top || navDock == ProfileDockSide.top ? 30.0 : 0.0;

    final bottomProfile = profileDock == ProfileDockSide.bottom && profileRailVisible;
    final bottomNav = navDock == ProfileDockSide.bottom && bottomNavVisible;
    final hasBottomControls =
        keyboardCapability || profileDock == ProfileDockSide.bottom || navDock == ProfileDockSide.bottom;

    _workspaceLeftInset = leftPanel + leftControls;
    _workspaceRightInset = rightPanel + rightControls;
    _workspaceTopInset = topPanel + topControls;
    _workspaceBottomInset =
        (bottomProfile ? profileBottomHeight : 0.0)
        + (bottomNav ? navBottomHeight : 0.0)
        + (keyboardShown ? tabletKeyboardHeight : 0.0)
        + (hasBottomControls ? 31.0 : 0.0);

    final controlsBottom = hasBottomControls ? 31.0 : 0.0;
    final keyboardBottom = controlsBottom;
    final navBottom =
        keyboardBottom + (keyboardShown ? tabletKeyboardHeight : 0.0);
    final profileBottom =
        navBottom + (bottomNav ? navBottomHeight : 0.0);

    final content = Stack(
      clipBehavior: Clip.hardEdge,
      children: [
        Positioned.fill(child: ClipRect(child: pages[tab])),
        if (bottomProfile)
          Positioned(
            left: 0,
            right: 0,
            bottom: profileBottom,
            height: profileBottomHeight,
            child: _bottomProfilePanel(),
          ),
        if (bottomNav)
          Positioned(
            left: 0,
            right: 0,
            bottom: navBottom,
            height: navBottomHeight,
            child: _bottomModePanel(),
          ),
        if (keyboardShown)
          Positioned(
            left: 0,
            right: 0,
            bottom: keyboardBottom,
            height: tabletKeyboardHeight,
            child: _bottomKeyboardPanel(),
          ),
        if (hasBottomControls)
          Positioned(
            left: 0,
            right: 0,
            bottom: 0,
            height: 31,
            child: Center(
              child: _bottomControlCluster(showKeyboard: keyboardCapability),
            ),
          ),
      ],
    );

    return _controlOverlay(content, showKeyboard: false);
  }

''',
        "stable overlay workspace",
    )

    # State used for virtual work-area geometry and two-position view toggle.
    text = replace_once(
        text,
        """  int _deckGesturePointerCount = 0;
  bool _deckGeometryInitialized = false;
""",
        """  int _deckGesturePointerCount = 0;
  bool _deckGeometryInitialized = false;
  Size _deckFullViewportSize = Size.zero;
  Matrix4? _deckUserTransformBeforeFit;
  Offset? _deckUserModelCenterBeforeFit;
  bool _deckShowingDefaultView = false;
""",
        "view toggle and full viewport state",
    )

    # Model-space AREA is now 3.5x the tile-block area.
    text = replace_between(
        text,
        "  Size _realModelSpaceSize(Size deck, Size viewport) {",
        "\n  void _fitDeck() {",
        r'''  Size _realModelSpaceSize(Size deck, Size viewport) {
    if (deck.isEmpty || viewport.isEmpty) {
      return deck;
    }

    // Invisible model-space area:
    // S(model) = 3.5 * S(tile block).
    const areaFactor = 3.5;
    final blockArea = deck.width * deck.height;
    final modelArea = blockArea * areaFactor;
    final blockAspect = deck.width / deck.height;
    final workspaceAspect = viewport.width / viewport.height;

    // Both model dimensions always remain >= the tile block.
    final modelAspect = workspaceAspect
        .clamp(blockAspect / areaFactor, blockAspect * areaFactor)
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

  Offset _workspaceCenterInFullViewport() => Offset(
        (_workspaceLeftInset - _workspaceRightInset) / 2,
        (_workspaceTopInset - _workspaceBottomInset) / 2,
      );

  Offset _defaultBlockCenter(Size viewport, Size canvas, double scale) {
    final model = _realModelSpaceSize(canvas, viewport);
    final verticalAllowance = max(
      0.0,
      (model.height - canvas.height) * scale / 2,
    );
    final desiredUp = viewport.height * .13;
    final workCenter = _workspaceCenterInFullViewport();
    return workCenter + Offset(0, -min(desiredUp, verticalAllowance));
  }

''',
        "3.5x model-space helpers",
    )

    # Two-position restore/default-view button.
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

    if (_deckShowingDefaultView && _deckUserTransformBeforeFit != null) {
      final saved = _deckUserTransformBeforeFit!.clone();
      if (_deckUserModelCenterBeforeFit != null) {
        _deckModelCenter = _deckUserModelCenterBeforeFit!;
      }

      final target = _boundedDeckMatrix(saved);
      _deckShowingDefaultView = false;

      _deckReturnAnimation = Matrix4Tween(
        begin: _deckTransform.value.clone(),
        end: target,
      ).animate(CurvedAnimation(
        parent: _deckReturnController,
        curve: Curves.easeOutCubic,
      ));
      _deckReturnController.forward(from: 0);
      return;
    }

    _deckUserTransformBeforeFit = _deckTransform.value.clone();
    _deckUserModelCenterBeforeFit = _deckModelCenter;
    _deckShowingDefaultView = true;

    final fitScale = _defaultDeckScale(
      _deckViewportSize,
      _deckCanvasSize,
    );
    _deckMinScale = min(_deckMinScale, fitScale);
    _deckMaxScale = max(_deckMaxScale, fitScale * 2);
    _deckModelCenter = _workspaceCenterInFullViewport();

    final target = _matrixWithScaleAndCenter(
      fitScale,
      _defaultBlockCenter(
        _deckViewportSize,
        _deckCanvasSize,
        fitScale,
      ),
    );

    _deckReturnAnimation = Matrix4Tween(
      begin: _deckTransform.value.clone(),
      end: target,
    ).animate(CurvedAnimation(
      parent: _deckReturnController,
      curve: Curves.easeOutCubic,
    ));
    _deckReturnController.forward(from: 0);
  }

''',
        "toggle default and user view",
    )

    # Virtual work-area edges are expressed inside a stable full-size Deck.
    text = replace_between(
        text,
        "  Offset _clearActualPanelOverlap(Offset center, double scale, Size viewport) {",
        "\n  Offset _modelCenterThatContainsBlock(",
        r'''  Offset _clearActualPanelOverlap(
    Offset center,
    double scale,
    Size viewport,
  ) {
    if (_deckFullViewportSize.isEmpty) {
      return center;
    }

    final halfW = _deckCanvasSize.width * scale / 2;
    final halfH = _deckCanvasSize.height * scale / 2;

    final leftEdge =
        -_deckFullViewportSize.width / 2 + _workspaceLeftInset;
    final rightEdge =
        _deckFullViewportSize.width / 2 - _workspaceRightInset;
    final topEdge =
        -_deckFullViewportSize.height / 2 + _workspaceTopInset;
    final bottomEdge =
        _deckFullViewportSize.height / 2 - _workspaceBottomInset;

    var x = center.dx;
    var y = center.dy;

    // No correction at all when the panel does not intersect the tile block.
    if (halfW * 2 <= rightEdge - leftEdge) {
      x = x.clamp(leftEdge + halfW, rightEdge - halfW).toDouble();
    }
    if (halfH * 2 <= bottomEdge - topEdge) {
      y = y.clamp(topEdge + halfH, bottomEdge - halfH).toDouble();
    }

    return Offset(x, y);
  }

''',
        "virtual panel overlap bounds",
    )

    # Work-area changes no longer translate coordinates just because layout
    # changed: full Deck coordinates stay stable. Only actual overlap is fixed.
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

    _deckViewportSize = viewport;
    _deckCanvasSize = canvas;

    final zeroScale = _defaultDeckScale(viewport, canvas);
    final current = _deckTransform.value;
    final rawScale = current.getMaxScaleOnAxis();

    final workChanged = !_deckPreviousViewport.isEmpty
        && ((_deckPreviousViewport.width - viewport.width).abs() > .1
            || (_deckPreviousViewport.height - viewport.height).abs() > .1
            || (_deckPreviousWorkOrigin - workOrigin).distanceSquared > .01);
    final canvasChanged =
        (_deckPreviousCanvas.width - canvas.width).abs() > .1
            || (_deckPreviousCanvas.height - canvas.height).abs() > .1;

    _deckMinScale = workChanged ? min(zeroScale, rawScale) : zeroScale;
    _deckMaxScale = max(
      _deckMinScale,
      zeroScale * _maximumDeckZoomFactor(rows, columns),
    );
    final scale =
        rawScale.clamp(_deckMinScale, _deckMaxScale).toDouble();

    if (!_deckGeometryInitialized) {
      _deckGeometryInitialized = true;
      _deckPreviousWorkOrigin = workOrigin;
      _deckPreviousViewport = viewport;
      _deckPreviousCanvas = canvas;
      _deckModelCenter = _workspaceCenterInFullViewport();

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

    var blockCenter =
        Offset(current.storage[12], current.storage[13]);
    var modelCenter = _deckModelCenter;

    if (workChanged && !previousViewport.isEmpty) {
      // Full Deck coordinates did not change, so leave the block untouched
      // unless an opened panel actually intersects it.
      final cleared = _clearActualPanelOverlap(
        blockCenter,
        scale,
        viewport,
      );

      if ((cleared - blockCenter).distanceSquared > .01) {
        final correction = cleared - blockCenter;
        blockCenter = cleared;
        modelCenter += correction;
      }

      modelCenter = _modelCenterThatContainsBlock(
        modelCenter,
        blockCenter,
        scale,
        canvas,
        viewport,
      );
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
        "stable virtual work-area geometry",
    )

    # A real interaction cancels the temporary default-view toggle and makes
    # the new transform the next user view.
    text = replace_between(
        text,
        "  void _beginDeckInteraction(ScaleStartDetails details) {",
        "\n  void _updateDeckInteraction(ScaleUpdateDetails details) {",
        r'''  void _beginDeckInteraction(ScaleStartDetails details) {
    _deckReturnController.stop();

    if (_deckShowingDefaultView) {
      _deckShowingDefaultView = false;
      _deckUserTransformBeforeFit = null;
      _deckUserModelCenterBeforeFit = null;
    }

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
        "interaction resets view toggle",
    )

    text = replace_once(
        text,
        """        final baseViewportW = constraints.maxWidth + _workspaceLeftInset + _workspaceRightInset;
        final baseViewportH = constraints.maxHeight + _workspaceTopInset + _workspaceBottomInset;
""",
        """        final baseViewportW = constraints.maxWidth;
        final baseViewportH = constraints.maxHeight;
""",
        "stable tile geometry with overlay panels",
    )

    # Render stays full-size; only geometry calculations use the reduced
    # invisible work rectangle.
    old_viewport = r'''        final viewport = Size(constraints.maxWidth, constraints.maxHeight);
        final canvasSize = Size(totalW, totalH);
        final workOrigin = Offset(_workspaceLeftInset, _workspaceTopInset);
        final zeroScale = _defaultDeckScale(viewport, canvasSize);
        final currentScale = _deckTransform.value.getMaxScaleOnAxis();

        _deckViewportSize = viewport;
        _deckCanvasSize = canvasSize;
'''
    new_viewport = r'''        final fullViewport = Size(
          constraints.maxWidth,
          constraints.maxHeight,
        );
        final viewport = Size(
          max(
            1.0,
            constraints.maxWidth
                - _workspaceLeftInset
                - _workspaceRightInset,
          ),
          max(
            1.0,
            constraints.maxHeight
                - _workspaceTopInset
                - _workspaceBottomInset,
          ),
        );
        final canvasSize = Size(totalW, totalH);
        final workOrigin =
            Offset(_workspaceLeftInset, _workspaceTopInset);
        final zeroScale = _defaultDeckScale(viewport, canvasSize);
        final currentScale =
            _deckTransform.value.getMaxScaleOnAxis();

        _deckFullViewportSize = fullViewport;
        _deckViewportSize = viewport;
        _deckCanvasSize = canvasSize;
'''
    text = replace_once(
        text,
        old_viewport,
        new_viewport,
        "stable full and virtual deck viewport",
    )

    # Tooltip reflects the toggle behavior.
    text = text.replace(
        "tooltip: 'Вид по умолчанию',",
        "tooltip: _deckShowingDefaultView ? 'Вернуть пользовательский вид' : 'Вид по умолчанию',",
        1,
    )

    path.write_text(text, encoding="utf-8")
    print(f"Applied NEXO v1.4.6 stable panels and view toggle: {path}")


if __name__ == "__main__":
    main()
