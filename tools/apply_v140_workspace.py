from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_between(text: str, start: str, end: str, replacement: str, label: str) -> str:
    a = text.find(start)
    if a < 0:
        raise RuntimeError(f"{label}: start marker not found")
    b = text.find(end, a)
    if b < 0:
        raise RuntimeError(f"{label}: end marker not found")
    return text[:a] + replacement + text[b:]


def main() -> None:
    path = ROOT / "src/mobile/macropad_mobile/lib/v12_workspace.dart"
    text = path.read_text(encoding="utf-8")

    text = replace_between(
        text,
        "  void _step(double amount) {",
        "\n  @override\n  Widget build(BuildContext context) {",
        r'''  void _centerIndex(int index, double itemExtent) {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || !_scroll.hasClients || widget.items.isEmpty) return;
      final viewport = _scroll.position.viewportDimension;
      final raw = (index + .5) * itemExtent - viewport / 2;
      final target = raw.clamp(0.0, _scroll.position.maxScrollExtent).toDouble();
      _scroll.animateTo(target, duration: const Duration(milliseconds: 210), curve: Curves.easeOutCubic);
    });
  }

  void _activateIndex(int index, double itemExtent) {
    if (widget.items.isEmpty) return;
    final normalized = ((index % widget.items.length) + widget.items.length) % widget.items.length;
    widget.onSelected(widget.items[normalized].id);
    _centerIndex(normalized, itemExtent);
  }

  void _selectRelative(int delta, double itemExtent) {
    if (widget.items.isEmpty) return;
    var current = widget.items.indexWhere((x) => x.id == widget.activeId);
    if (current < 0) current = 0;
    _activateIndex(current + delta, itemExtent);
  }

  @override
  void didUpdateWidget(covariant NexoProfileRail oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.activeId != widget.activeId ||
        oldWidget.dock != widget.dock ||
        oldWidget.items.length != widget.items.length) {
      final index = widget.items.indexWhere((x) => x.id == widget.activeId);
      if (index >= 0) _centerIndex(index, 44.0);
    }
  }

''',
        "profile rail selection helpers",
    )

    text = text.replace(
        "arrow(Icons.keyboard_arrow_up, () => _step(-itemExtent))",
        "arrow(Icons.keyboard_arrow_up, () => _selectRelative(-1, itemExtent))",
    )
    text = text.replace(
        "arrow(Icons.keyboard_arrow_down, () => _step(itemExtent))",
        "arrow(Icons.keyboard_arrow_down, () => _selectRelative(1, itemExtent))",
    )
    text = text.replace(
        "arrow(Icons.keyboard_arrow_left, () => _step(-itemExtent))",
        "arrow(Icons.keyboard_arrow_left, () => _selectRelative(-1, itemExtent))",
    )
    text = text.replace(
        "arrow(Icons.keyboard_arrow_right, () => _step(itemExtent))",
        "arrow(Icons.keyboard_arrow_right, () => _selectRelative(1, itemExtent))",
    )
    text = text.replace(
        "onTap: () => widget.onSelected(item.id),",
        "onTap: () => _activateIndex(index, itemExtent),",
    )

    path.write_text(text, encoding="utf-8")
    print(f"Applied v1.4 profile rail fixes: {path}")


if __name__ == "__main__":
    main()
