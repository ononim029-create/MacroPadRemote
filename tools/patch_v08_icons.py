from pathlib import Path


def replace_once(path: str, old: str, new: str, label: str) -> None:
    p = Path(path)
    text = p.read_text()
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 occurrence, got {count}")
    p.write_text(text.replace(old, new, 1))


cs = "src/windows/MacroPadRemote/MainWindow.xaml.cs"
replace_once(cs,
    "        _state.Profiles ??= new List<Profile>();\n        _state.TrustedDevices ??= new List<TrustedClient>();",
    "        _state.Profiles ??= new List<Profile>();\n        _state.TrustedDevices ??= new List<TrustedClient>();\n        _state.IconLibrary ??= new List<IconAsset>();",
    "initialize icon library")
replace_once(cs,
    "        stack.Children.Add(new TextBlock { Text = Glyph(tile), FontSize = 26, HorizontalAlignment = HorizontalAlignment.Center, Margin = new Thickness(0, 0, 0, 7), Foreground = blank ? Brushes.Gray : Brushes.White });",
    "        stack.Children.Add(CreateTileIcon(tile, blank));",
    "render tile icon")
replace_once(cs,
    "        _updating = false;\n    }\n\n    private static string ActionTypeName(string type)",
    "        _updating = false;\n        RefreshIconInspector();\n    }\n\n    private static string ActionTypeName(string type)",
    "refresh icon inspector")
replace_once(cs,
    "        tile.Title = \"Добавить\"; tile.ActionType = \"\"; tile.ActionValue = \"\"; tile.Hotkey = \"\"; tile.ColumnSpan = tile.RowSpan = 1; tile.Steps.Clear();",
    "        tile.Title = \"Добавить\"; tile.ActionType = \"\"; tile.ActionValue = \"\"; tile.Hotkey = \"\"; tile.IconKind = \"auto\"; tile.IconValue = \"\"; tile.ColumnSpan = tile.RowSpan = 1; tile.Steps.Clear();",
    "clear tile icon")
replace_once(cs,
    "                    hotkey = t.Hotkey,\n                    rowSpan = t.RowSpan,",
    "                    hotkey = t.Hotkey,\n                    iconKind = SnapshotIconKind(t),\n                    iconValue = SnapshotIconValue(t),\n                    rowSpan = t.RowSpan,",
    "snapshot icon fields")
replace_once(cs,
    "    public List<Profile> Profiles { get; set; } = new();\n    public List<TrustedClient> TrustedDevices { get; set; } = new();",
    "    public List<Profile> Profiles { get; set; } = new();\n    public List<TrustedClient> TrustedDevices { get; set; } = new();\n    public List<IconAsset> IconLibrary { get; set; } = new();",
    "appstate icon library")
replace_once(cs,
    "    public string Hotkey { get; set; } = \"\";\n    public int RowSpan { get; set; } = 1;",
    "    public string Hotkey { get; set; } = \"\";\n    public string IconKind { get; set; } = \"auto\";\n    public string IconValue { get; set; } = \"\";\n    public int RowSpan { get; set; } = 1;",
    "tile icon fields")

xaml = "src/windows/MacroPadRemote/MainWindow.xaml"
replace_once(xaml, "  v0.7 preview", "  v0.8 preview", "header version")
old = '''                            <TextBlock Text="Горячая клавиша" Foreground="{StaticResource Muted}" FontSize="10"/>
                            <Grid Margin="0,3,0,8"><Grid.ColumnDefinitions><ColumnDefinition/><ColumnDefinition Width="112"/></Grid.ColumnDefinitions><TextBox x:Name="InspectorHotkeyBox" Height="32" IsReadOnly="True"/><Button x:Name="RecordHotkeyButton" Grid.Column="1" Content="Записать" Margin="6,0,0,0" Click="RecordHotkey_Click" PreviewKeyDown="RecordHotkey_PreviewKeyDown"/></Grid>
                            <StackPanel Orientation="Horizontal" HorizontalAlignment="Right"><Button Content="Очистить" Width="84" Margin="0,0,7,0" Click="ClearTile_Click"/><Button Content="Применить" Width="94" Click="ApplyInspector_Click"/></StackPanel>'''
new = '''                            <TextBlock Text="Горячая клавиша" Foreground="{StaticResource Muted}" FontSize="10"/>
                            <Grid Margin="0,3,0,8"><Grid.ColumnDefinitions><ColumnDefinition/><ColumnDefinition Width="112"/></Grid.ColumnDefinitions><TextBox x:Name="InspectorHotkeyBox" Height="32" IsReadOnly="True"/><Button x:Name="RecordHotkeyButton" Grid.Column="1" Content="Записать" Margin="6,0,0,0" Click="RecordHotkey_Click" PreviewKeyDown="RecordHotkey_PreviewKeyDown"/></Grid>
                            <TextBlock Text="Иконка" Foreground="{StaticResource Muted}" FontSize="10"/>
                            <Grid Margin="0,4,0,9">
                                <Grid.ColumnDefinitions><ColumnDefinition Width="48"/><ColumnDefinition/><ColumnDefinition Width="88"/></Grid.ColumnDefinitions>
                                <Border x:Name="InspectorIconPreview" Width="42" Height="42" Background="#111315" BorderBrush="{StaticResource Border}" BorderThickness="1" Padding="5"/>
                                <StackPanel Grid.Column="1" Margin="7,0,7,0" VerticalAlignment="Center"><TextBlock x:Name="InspectorIconStatus" Text="Автоматически" FontSize="10" TextWrapping="Wrap"/><Button x:Name="IconLibraryButton" Content="Библиотека…" Height="25" Margin="0,3,0,0" Click="IconLibrary_Click"/></StackPanel>
                                <StackPanel Grid.Column="2"><Button x:Name="IconImportButton" Content="Импорт" Height="25" Click="IconImport_Click"/><Button x:Name="IconScreenshotButton" Content="Снимок" Height="25" Margin="0,3,0,0" Click="IconScreenshot_Click"/></StackPanel>
                            </Grid>
                            <Grid Margin="0,0,0,8"><Grid.ColumnDefinitions><ColumnDefinition/><ColumnDefinition Width="90"/></Grid.ColumnDefinitions><TextBlock Text="ПКМ по пользовательской иконке в библиотеке — удалить." Foreground="{StaticResource Muted}" FontSize="9" TextWrapping="Wrap" VerticalAlignment="Center"/><Button x:Name="IconResetButton" Grid.Column="1" Content="Авто" Height="26" Click="IconReset_Click"/></Grid>
                            <StackPanel Orientation="Horizontal" HorizontalAlignment="Right"><Button Content="Очистить" Width="84" Margin="0,0,7,0" Click="ClearTile_Click"/><Button Content="Применить" Width="94" Click="ApplyInspector_Click"/></StackPanel>'''
replace_once(xaml, old, new, "icon inspector UI")

dart = "src/mobile/macropad_mobile/lib/main.dart"
replace_once(dart,
'''          child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
            Icon(_iconFor(tile), size: iconSize, color: blank ? const Color(0xff7c8287) : Colors.white),
            SizedBox(height: (5 * scale).clamp(1.0, 6.0)),''',
'''          child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
            _tileIcon(tile, iconSize, blank),
            SizedBox(height: (5 * scale).clamp(1.0, 6.0)),''',
"mobile tile icon widget")
replace_once(dart,
'''  IconData _iconFor(TileSnapshot tile) => switch (tile.actionType) {''',
'''  Widget _tileIcon(TileSnapshot tile, double size, bool blank) {
    final color = blank ? const Color(0xff7c8287) : Colors.white;
    if (tile.iconKind == 'image' && tile.iconValue.isNotEmpty) {
      try {
        final comma = tile.iconValue.indexOf(',');
        final payload = comma >= 0 ? tile.iconValue.substring(comma + 1) : tile.iconValue;
        final bytes = base64Decode(payload);
        return SizedBox(width: size * 1.55, height: size * 1.55, child: Image.memory(bytes, fit: BoxFit.contain, gaplessPlayback: true));
      } catch (_) {}
    }
    if (tile.iconKind == 'glyph' && tile.iconValue.isNotEmpty) {
      return Text(tile.iconValue, style: TextStyle(fontSize: size, color: color, fontWeight: FontWeight.w600, height: 1));
    }
    return Icon(_iconFor(tile), size: size, color: color);
  }

  IconData _iconFor(TileSnapshot tile) => switch (tile.actionType) {''',
"mobile icon renderer")
replace_once(dart,
'''class TileSnapshot {
  final String id;
  final String title;
  final String actionType;
  final int rowSpan;
  final int columnSpan;
  const TileSnapshot({required this.id, required this.title, required this.actionType, required this.rowSpan, required this.columnSpan});
  factory TileSnapshot.fromJson(Map<String, dynamic> json) => TileSnapshot(
        id: '${json['id'] ?? ''}',
        title: '${json['title'] ?? 'Кнопка'}',
        actionType: '${json['actionType'] ?? ''}',
        rowSpan: ((json['rowSpan'] as num?)?.toInt() ?? 1).clamp(1, 12).toInt(),
        columnSpan: ((json['columnSpan'] as num?)?.toInt() ?? 1).clamp(1, 12).toInt(),
      );
}''',
'''class TileSnapshot {
  final String id;
  final String title;
  final String actionType;
  final String iconKind;
  final String iconValue;
  final int rowSpan;
  final int columnSpan;
  const TileSnapshot({required this.id, required this.title, required this.actionType, required this.iconKind, required this.iconValue, required this.rowSpan, required this.columnSpan});
  factory TileSnapshot.fromJson(Map<String, dynamic> json) => TileSnapshot(
        id: '${json['id'] ?? ''}',
        title: '${json['title'] ?? 'Кнопка'}',
        actionType: '${json['actionType'] ?? ''}',
        iconKind: '${json['iconKind'] ?? 'auto'}',
        iconValue: '${json['iconValue'] ?? ''}',
        rowSpan: ((json['rowSpan'] as num?)?.toInt() ?? 1).clamp(1, 12).toInt(),
        columnSpan: ((json['columnSpan'] as num?)?.toInt() ?? 1).clamp(1, 12).toInt(),
      );
}''',
"mobile tile snapshot icon fields")

proj = "src/windows/MacroPadRemote/MacroPadRemote.csproj"
replace_once(proj,
    "<Version>0.7.0</Version>\n    <InformationalVersion>0.7.0-preview</InformationalVersion>",
    "<Version>0.8.0</Version>\n    <InformationalVersion>0.8.0-preview</InformationalVersion>",
    "windows version")

workflow = ".github/workflows/release.yml"
replace_once(workflow, '"version":"0.7.0-preview"', '"version":"0.8.0-preview"', "preview manifest version")
replace_once(workflow,
    '"notes":"v0.7: trusted devices, no-repeat QR, profile/page drawer, portrait phone scaling, connection settings, action hotfix"',
    '"notes":"v0.8: per-macro icon library, custom image import, reusable user icons and screen-region screenshot icons synced to phone"',
    "preview manifest notes")

print("v0.8 icon feature patch applied")
