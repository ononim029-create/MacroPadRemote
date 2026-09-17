from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, got {count}")
    return text.replace(old, new, 1)

def main() -> None:
    path = ROOT / "src/mobile/macropad_mobile/lib/main.dart"
    text = path.read_text(encoding="utf-8")

    text = replace_once(
        text,
        """  bool controlsLocked = false;
  bool _deckFitMode = false;""",
        """  bool controlsLocked = false;
  String _pendingProfileId = '';
  bool _deckFitMode = false;""",
        "pending profile state",
    )

    text = replace_once(
        text,
        """        if (mounted) setState(() { profile = p; profiles = summaries; keyboardLayouts = layouts; activeKeyboardLayout = activeLayout; });""",
        """        if (mounted) setState(() {
          profile = p;
          profiles = summaries;
          keyboardLayouts = layouts;
          activeKeyboardLayout = activeLayout;
          _pendingProfileId = '';
        });""",
        "clear pending profile on snapshot",
    )

    text = replace_once(
        text,
        """  Future<void> _switchProfile(String profileId) => widget.transport.send({'type': 'switchProfile', 'profileId': profileId, 'force': true});""",
        """  Future<void> _switchProfile(String profileId) async {
    if (profileId.isEmpty || profileId == profile?.id) return;
    if (mounted) setState(() => _pendingProfileId = profileId);
    try {
      await widget.transport.send({'type': 'switchProfile', 'profileId': profileId, 'force': true});
    } catch (_) {
      if (mounted && _pendingProfileId == profileId) setState(() => _pendingProfileId = '');
      rethrow;
    }
  }""",
        "robust mobile profile switch",
    )

    text = replace_once(
        text,
        """    final activeId = profile?.id;""",
        """    final activeId = _pendingProfileId.isNotEmpty ? _pendingProfileId : profile?.id;""",
        "drawer pending active profile",
    )

    text = replace_once(
        text,
        """                      onTap: () async { Navigator.of(context).pop(); if (item.id != activeId) await _switchProfile(item.id); },""",
        """                      onTap: () async {
                        if (item.id != activeId) await _switchProfile(item.id);
                        if (mounted) Navigator.of(context).pop();
                      },""",
        "drawer switch before close",
    )

    text = replace_once(
        text,
        """        activeId: profile?.id ?? '',""",
        """        activeId: _pendingProfileId.isNotEmpty ? _pendingProfileId : (profile?.id ?? ''),""",
        "profile rail pending active profile",
    )

    path.write_text(text, encoding="utf-8")
    print(f"Applied v1.2.2 mobile profile switching: {path}")

if __name__ == "__main__":
    main()
