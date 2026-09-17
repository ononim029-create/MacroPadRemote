from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main() -> None:
    path = ROOT / "src/windows/MacroPadRemote/MainWindow.xaml.cs"
    text = path.read_text(encoding="utf-8")

    old = """                    await Dispatcher.InvokeAsync(() =>
                    {
                        _state.ActiveProfileId = profile.Id;
                        SaveState();
                        RefreshProfiles();
                    });"""

    new = """                    await Dispatcher.InvokeAsync(() =>
                    {
                        // Apply the remote profile before saving. SaveState() mirrors
                        // _profile.Id back into ActiveProfileId, so saving while _profile
                        // still points to the old profile cancels the phone selection.
                        _state.ActiveProfileId = profile.Id;
                        _profile = profile;
                        RefreshProfiles();
                        SaveState();
                    });"""

    if text.count(old) != 1:
        raise RuntimeError(f"profile switch handler: expected one match, got {text.count(old)}")

    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"Fixed remote profile switching: {path}")

if __name__ == "__main__":
    main()
