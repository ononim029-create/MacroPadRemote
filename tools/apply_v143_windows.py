from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    path = ROOT / "src/windows/MacroPadRemote/MainWindow.xaml"
    text = path.read_text(encoding="utf-8")
    text = text.replace('Text="  v1.4.2 preview"', 'Text="  v1.4.3 preview"', 1)
    path.write_text(text, encoding="utf-8")
    print(f"Applied NEXO v1.4.3 Windows version label: {path}")


if __name__ == "__main__":
    main()
