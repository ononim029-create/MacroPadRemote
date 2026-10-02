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
        'Title="NEXO" Width="1680" Height="960" MinWidth="1180" MinHeight="720"\n        WindowStartupLocation="CenterScreen" Background="{StaticResource Bg}">',
        'Title="NEXO" Width="1480" Height="900" MinWidth="760" MinHeight="520"\n        WindowStartupLocation="CenterScreen" Background="{StaticResource Bg}"\n        Loaded="ResponsiveWindow_Loaded" SizeChanged="ResponsiveWindow_SizeChanged">',
        "responsive window bounds",
    )

    text = replace_once(
        text,
        '<RowDefinition Height="48"/>\n            <RowDefinition Height="*"/>\n            <RowDefinition Height="250"/>',
        '<RowDefinition x:Name="ResponsiveHeaderRow" Height="48"/>\n            <RowDefinition Height="*"/>\n            <RowDefinition x:Name="ResponsiveInspectorRow" Height="250"/>',
        "responsive root rows",
    )

    text = replace_once(
        text,
        '<ColumnDefinition Width="0"/>\n            <ColumnDefinition Width="*"/>\n            <ColumnDefinition Width="385"/>',
        '<ColumnDefinition x:Name="ResponsiveProfilesColumn" Width="0"/>\n            <ColumnDefinition Width="*"/>\n            <ColumnDefinition x:Name="ResponsiveActionLibraryColumn" Width="385"/>',
        "responsive root columns",
    )

    text = replace_once(
        text,
        '<Border Background="#202326" BorderBrush="{StaticResource Border}" BorderThickness="1" Padding="10,5" Margin="0,0,8,0">',
        '<Border x:Name="ResponsiveHeaderStatus" Background="#202326" BorderBrush="{StaticResource Border}" BorderThickness="1" Padding="10,5" Margin="0,0,8,0">',
        "responsive header status",
    )

    text = replace_once(
        text,
        '<Grid.RowDefinitions><RowDefinition Height="92"/><RowDefinition Height="*"/><RowDefinition Height="52"/></Grid.RowDefinitions>',
        '<Grid.RowDefinitions><RowDefinition x:Name="ResponsiveDeckHeaderRow" Height="92"/><RowDefinition Height="*"/><RowDefinition x:Name="ResponsiveDeckPagerRow" Height="52"/></Grid.RowDefinitions>',
        "responsive deck rows",
    )

    text = replace_once(
        text,
        '<Grid Grid.Row="1"><Grid.ColumnDefinitions><ColumnDefinition Width="1.1*"/><ColumnDefinition/><ColumnDefinition/></Grid.ColumnDefinitions>',
        '<Grid x:Name="ResponsiveInspectorGrid" Grid.Row="1"><Grid.ColumnDefinitions><ColumnDefinition Width="1.1*"/><ColumnDefinition/><ColumnDefinition/></Grid.ColumnDefinitions>',
        "responsive inspector grid",
    )

    text = replace_once(
        text,
        '<StackPanel Margin="0,0,12,0"><TextBlock x:Name="InspectorHint"',
        '<StackPanel x:Name="ResponsiveInspectorGeneral" Margin="0,0,12,0"><TextBlock x:Name="InspectorHint"',
        "responsive inspector general panel",
    )

    text = replace_once(
        text,
        '<StackPanel Grid.Column="1" Margin="0,0,12,0"><TextBlock Text="Тип действия"',
        '<StackPanel x:Name="ResponsiveInspectorValue" Grid.Column="1" Margin="0,0,12,0"><TextBlock Text="Тип действия"',
        "responsive inspector value panel",
    )

    text = replace_once(
        text,
        '<StackPanel Grid.Column="2"><TextBlock Text="Горячая клавиша"',
        '<StackPanel x:Name="ResponsiveInspectorHotkey" Grid.Column="2"><TextBlock Text="Горячая клавиша"',
        "responsive inspector hotkey panel",
    )

    text = replace_once(
        text,
        'Text="  v1.4.6 preview"',
        'Text="  v1.4.7 preview"',
        "v1.4.7 version label",
    )

    path.write_text(text, encoding="utf-8")
    print(f"Applied NEXO v1.4.7 responsive Windows layout: {path}")


if __name__ == "__main__":
    main()
