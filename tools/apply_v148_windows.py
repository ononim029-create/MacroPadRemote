from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)

def main() -> None:
    path = ROOT / "src/windows/MacroPadRemote/MainWindow.xaml"
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        '<ColumnDefinition x:Name="ResponsiveProfilesColumn" Width="0"/>',
        '<ColumnDefinition x:Name="ResponsiveProfilesColumn" Width="225"/>',
        "restore profile sidebar",
    )
    text = replace_once(
        text,
        'Text="  v1.4.7 preview"',
        'Text="  v1.4.8 preview"',
        "v1.4.8 version label",
    )
    path.write_text(text, encoding="utf-8")
    print(f"Applied NEXO v1.4.8 profile sidebar recovery: {path}")

if __name__ == "__main__":
    main()
