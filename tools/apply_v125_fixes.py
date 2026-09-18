from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    path = ROOT / "src/windows/MacroPadRemote/MainWindow.xaml"
    text = path.read_text(encoding="utf-8")
    old = 'Text="  v1.2.4 preview"'
    new = 'Text="  v1.2.5 preview"'
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"desktop version label: expected 1 match, got {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"Applied v1.2.5 Windows fixes: {path}")


if __name__ == "__main__":
    main()
