from pathlib import Path
import re


def sub(path, pattern, repl, flags=0, count=1, label='replace'):
    p=Path(path); s=p.read_text(encoding='utf-8')
    n=re.subn(pattern,repl,s,count=count,flags=flags)
    if n[1] != count:
        raise SystemExit(f'{label}: expected {count}, got {n[1]} in {path}')
    p.write_text(n[0],encoding='utf-8')


def rep(path, old, new, label):
    p=Path(path); s=p.read_text(encoding='utf-8')
    if old not in s: raise SystemExit(f'{label}: not found in {path}')
    p.write_text(s.replace(old,new),encoding='utf-8')

mobile='src/mobile/macropad_mobile/lib/main.dart'
cs='src/windows/MacroPadRemote/MainWindow.xaml.cs'
xaml='src/windows/MacroPadRemote/MainWindow.xaml'
app='src/windows/MacroPadRemote/App.xaml'
proj='src/windows/MacroPadRemote/MacroPadRemote.csproj'
pub='src/mobile/macropad_mobile/pubspec.yaml'
workflow='.github/workflows/release.yml'

# Branding: protocol/namespace/storage keys stay compatible, visible product name becomes NEXO.
for path in (mobile, cs, xaml):
    p=Path(path); s=p.read_text(encoding='utf-8')
    s=s.replace('MacroPad Remote','NEXO').replace('MacroPad PC','NEXO PC')
    p.write_text(s,encoding='utf-8')
rep(proj,'<Product>MacroPad Remote</Product>','<Product>NEXO</Product>','product name')
rep(proj,'<Version>0.8.0</Version>','<Version>0.9.0</Version>','windows version')
rep(proj,'<InformationalVersion>0.8.0-preview</InformationalVersion>','<InformationalVersion>0.9.0-preview</InformationalVersion>','windows info version')
rep(pub,'version: 0.8.0+31','version: 0.9.0+40','android version')

# Per-tile label visibility in Windows model/snapshot/grid/inspector.
rep(cs,'    public string IconValue { get; set; } = "";\n    public int RowSpan { get; set; } = 1;',
       '    public string IconValue { get; set; } = "";\n    public bool ShowLabel { get; set; } = true;\n    public int RowSpan { get; set; } = 1;','tile show label model')
rep(cs,'                    iconValue = SnapshotIconValue(t),\n                    rowSpan = t.RowSpan,',
       '                    iconValue = SnapshotIconValue(t),\n                    showLabel = t.ShowLabel,\n                    rowSpan = t.RowSpan,','snapshot label')
rep(cs,'        stack.Children.Add(CreateTileIcon(tile, blank));\n        stack.Children.Add(new TextBlock { Text = tile.Title, TextAlignment = TextAlignment.Center, TextWrapping = TextWrapping.Wrap, FontWeight = FontWeights.SemiBold, Foreground = blank ? Brushes.Gray : Brushes.White, MaxWidth = 180 });',
       '        stack.Children.Add(CreateTileIcon(tile, blank));\n        if (tile.ShowLabel)\n            stack.Children.Add(new TextBlock { Text = tile.Title, TextAlignment = TextAlignment.Center, TextWrapping = TextWrapping.Wrap, FontWeight = FontWeights.SemiBold, Foreground = blank ? Brushes.Gray : Brushes.White, MaxWidth = 180 });','desktop tile label')
rep(cs,'        RecordHotkeyButton.IsEnabled = enabled;\n', '        RecordHotkeyButton.IsEnabled = enabled;\n        InspectorShowLabel.IsEnabled = enabled;\n','enable label checkbox')
rep(cs,'            InspectorValueLabel.Text = "Параметр";\n', '            InspectorValueLabel.Text = "Параметр";\n            InspectorShowLabel.IsChecked = true;\n','clear label checkbox')
rep(cs,'            InspectorHotkeyBox.Text = _selected.Hotkey;\n', '            InspectorHotkeyBox.Text = _selected.Hotkey;\n            InspectorShowLabel.IsChecked = _selected.ShowLabel;\n','load label checkbox')
rep(cs,'        _selected.ActionValue = InspectorValueBox.Text.Trim();\n', '        _selected.ActionValue = InspectorValueBox.Text.Trim();\n        _selected.ShowLabel = InspectorShowLabel.IsChecked != false;\n','apply label checkbox')
rep(cs,'        tile.Title = "Добавить"; tile.ActionType = ""; tile.ActionValue = ""; tile.Hotkey = ""; tile.IconKind = "auto"; tile.IconValue = ""; tile.ColumnSpan = tile.RowSpan = 1; tile.Steps.Clear();',
       '        tile.Title = "Добавить"; tile.ActionType = ""; tile.ActionValue = ""; tile.Hotkey = ""; tile.IconKind = "auto"; tile.IconValue = ""; tile.ShowLabel = true; tile.ColumnSpan = tile.RowSpan = 1; tile.Steps.Clear();','reset show label')
rep(xaml,'                            <TextBlock Text="Название" Foreground="{StaticResource Muted}" FontSize="10"/><TextBox x:Name="InspectorTitleBox" Height="32" Margin="0,3,0,8" TextChanged="InspectorChanged"/>',
         '                            <TextBlock Text="Название" Foreground="{StaticResource Muted}" FontSize="10"/><TextBox x:Name="InspectorTitleBox" Height="32" Margin="0,3,0,5" TextChanged="InspectorChanged"/>\n                            <CheckBox x:Name="InspectorShowLabel" Content="Показывать название функции на этой клавише" IsChecked="True" Margin="0,0,0,8"/>','inspector label checkbox')

# PC remembered-device menu: three-dot button per device and remove old footer-only action.
rep(xaml,'                                    <Grid.ColumnDefinitions><ColumnDefinition Width="30"/><ColumnDefinition/></Grid.ColumnDefinitions>',
         '                                    <Grid.ColumnDefinitions><ColumnDefinition Width="30"/><ColumnDefinition/><ColumnDefinition Width="34"/></Grid.ColumnDefinitions>','trusted device columns')
rep(xaml,'                                    </StackPanel>\n                                </Grid>\n                            </DataTemplate>',
         '                                    </StackPanel>\n                                    <Button Grid.Column="2" Content="⋮" FontSize="18" Padding="0" Background="Transparent" BorderThickness="0" Tag="{Binding}" Click="TrustedDeviceMenu_Click" ToolTip="Меню устройства"/>\n                                </Grid>\n                            </DataTemplate>','trusted menu button')
rep(xaml,'                    <Button Grid.Row="4" Content="Забыть выбранное устройство" Margin="0,5,0,0" Click="ForgetTrustedDevice_Click"/>',
         '                    <TextBlock Grid.Row="4" Text="⋮ рядом с устройством — забыть и потребовать новую привязку по QR" Foreground="{StaticResource Muted}" FontSize="9" TextWrapping="Wrap" Margin="0,6,0,0"/>','trusted footer')

# Add per-device popup handler; forgetting active Wi-Fi also closes that socket and invalidates trust.
insert='''\n    private async void TrustedDeviceMenu_Click(object sender, RoutedEventArgs e)\n    {\n        if (sender is not Button { Tag: TrustedClient device } button) return;\n        var menu = new ContextMenu();\n        var forget = new MenuItem { Header = "Забыть устройство (отключиться)" };\n        forget.Click += async (_, _) => await ForgetTrustedClientAsync(device);\n        menu.Items.Add(forget);\n        button.ContextMenu = menu; menu.PlacementTarget = button; menu.IsOpen = true; e.Handled = true;\n    }\n\n    private async Task ForgetTrustedClientAsync(TrustedClient device)\n    {\n        List<WebSocket> close = new();\n        lock (_clients)\n            foreach (var pair in _clientIds.Where(x => x.Value == device.Id).ToList()) close.Add(pair.Key);\n        foreach (var socket in close)\n            try { await socket.CloseAsync(WebSocketCloseStatus.NormalClosure, "Device forgotten", CancellationToken.None); } catch { }\n        if (_bleClientId == device.Id) { _bleAuthenticated = false; _bleClientId = ""; }\n        _state.TrustedDevices.RemoveAll(x => x.Id == device.Id);\n        SaveState(); RefreshTrustedDevices(); UpdateConnectionStatus();\n    }\n'''
rep(cs,'    private void HeaderSettingsButton_Click(object sender, RoutedEventArgs e)\n',insert+'\n    private void HeaderSettingsButton_Click(object sender, RoutedEventArgs e)\n','insert trusted handler')

# Contrast pass on Windows selected/hover menu states.
rep(app,'        <Style TargetType="MenuItem"><Setter Property="Background" Value="{StaticResource Panel2}"/><Setter Property="Foreground" Value="{StaticResource Text}"/><Setter Property="Padding" Value="10,6"/></Style>',
        '        <Style TargetType="MenuItem"><Setter Property="Background" Value="{StaticResource Panel2}"/><Setter Property="Foreground" Value="{StaticResource Text}"/><Setter Property="Padding" Value="10,6"/><Style.Triggers><Trigger Property="IsHighlighted" Value="True"><Setter Property="Background" Value="#353A3E"/><Setter Property="Foreground" Value="White"/></Trigger></Style.Triggers></Style>','menu contrast')

# Mobile branding + contrast theme additions.
rep(mobile,"      title: 'NEXO',", "      title: 'NEXO',\n      builder: (context, child) => MediaQuery(data: MediaQuery.of(context).copyWith(textScaler: MediaQuery.of(context).textScaler.clamp(minScaleFactor: .85, maxScaleFactor: 1.15)), child: child!),",'material title anchor')
rep(mobile,'        dialogTheme: const DialogThemeData(backgroundColor: mpPanel, shape: RoundedRectangleBorder(borderRadius: BorderRadius.zero, side: BorderSide(color: mpBorder))),',
           '        dialogTheme: const DialogThemeData(backgroundColor: mpPanel, titleTextStyle: TextStyle(color: Colors.white, fontSize: 19, fontWeight: FontWeight.w600), contentTextStyle: TextStyle(color: mpText), shape: RoundedRectangleBorder(borderRadius: BorderRadius.zero, side: BorderSide(color: mpBorder))),\n        popupMenuTheme: const PopupMenuThemeData(color: mpPanel2, textStyle: TextStyle(color: Colors.white)),\n        listTileTheme: const ListTileThemeData(textColor: Colors.white, iconColor: Colors.white, selectedColor: Colors.white, selectedTileColor: mpHover),','mobile contrast')

# Mobile tile snapshot label field.
rep(mobile,'  final String iconValue;\n  final int rowSpan;', '  final String iconValue;\n  final bool showLabel;\n  final int rowSpan;','mobile showLabel field')
rep(mobile,'  const TileSnapshot({required this.id, required this.title, required this.actionType, required this.iconKind, required this.iconValue, required this.rowSpan, required this.columnSpan});',
           '  const TileSnapshot({required this.id, required this.title, required this.actionType, required this.iconKind, required this.iconValue, required this.showLabel, required this.rowSpan, required this.columnSpan});','mobile showLabel ctor')
rep(mobile,"        iconValue: '${json['iconValue'] ?? ''}',\n        rowSpan:", "        iconValue: '${json['iconValue'] ?? ''}',\n        showLabel: json['showLabel'] != false,\n        rowSpan:",'mobile showLabel json')
rep(mobile,'            SizedBox(height: (5 * scale).clamp(1.0, 6.0)),\n            Flexible(child: Text(tile.title, textAlign: TextAlign.center, maxLines: scale < .52 ? 1 : 2, overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: fontSize, color: blank ? const Color(0xff7c8287) : Colors.white, fontWeight: FontWeight.w600, height: 1.05))),',
           '            if (tile.showLabel) ...[\n              SizedBox(height: (5 * scale).clamp(1.0, 6.0)),\n              Flexible(child: Text(tile.title, textAlign: TextAlign.center, maxLines: scale < .52 ? 1 : 2, overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: fontSize, color: blank ? const Color(0xff7c8287) : Colors.white, fontWeight: FontWeight.w600, height: 1.05))),\n            ],','mobile hide tile label')

# Remote workspace state: lock/pan/zoom and smooth return home.
rep(mobile,'class _RemotePageState extends State<RemotePage> {', 'class _RemotePageState extends State<RemotePage> with SingleTickerProviderStateMixin {','ticker state')
rep(mobile,"  String serverName = '';\n", "  String serverName = '';\n  bool viewLocked = true;\n  final TransformationController _deckTransform = TransformationController();\n  late final AnimationController _deckReturnController;\n  Animation<Matrix4>? _deckReturnAnimation;\n",'deck fields')
rep(mobile,'    serverName = widget.initialServerName;\n    _connect();',
           '    serverName = widget.initialServerName;\n    _deckReturnController = AnimationController(vsync: this, duration: const Duration(milliseconds: 260))\n      ..addListener(() { if (_deckReturnAnimation != null) _deckTransform.value = _deckReturnAnimation!.value; });\n    _connect();','deck animation init')
rep(mobile,'  Future<void> _switchPage(String pageId) => widget.transport.send({\'type\': \'switchPage\', \'pageId\': pageId});\n',
           '''  Future<void> _switchPage(String pageId) => widget.transport.send({'type': 'switchPage', 'pageId': pageId});\n\n  void _toggleViewLock() {\n    final next = !viewLocked;\n    setState(() => viewLocked = next);\n    if (next) {\n      _deckReturnController.stop();\n      _deckReturnAnimation = Matrix4Tween(begin: _deckTransform.value.clone(), end: Matrix4.identity()).animate(CurvedAnimation(parent: _deckReturnController, curve: Curves.easeOutCubic));\n      _deckReturnController.forward(from: 0);\n    }\n  }\n\n  Future<void> _forgetCurrentDevice() async {\n    if (serverId.isEmpty) return;\n    await DeviceStore.remove(serverId);\n    await widget.transport.close();\n    if (mounted) Navigator.of(context).pop();\n  }\n''','deck methods')
rep(mobile,'    subscription?.cancel();\n    widget.transport.close();\n    super.dispose();',
           '    subscription?.cancel();\n    _deckReturnController.dispose();\n    _deckTransform.dispose();\n    widget.transport.close();\n    super.dispose();','deck dispose')

# Replace RemotePage build with responsive landscape controls + PopScope blocking route-back.
sub(mobile,r"  @override\n  Widget build\(BuildContext context\) \{\n    final pages = <Widget>\[deck\(\), media\(\)\];.*?\n  \}\n\n  Widget _drawer\(\)",'''  @override\n  Widget build(BuildContext context) {\n    final pages = <Widget>[deck(), media()];\n    if (tab >= pages.length) tab = 0;\n    final compact = widget.formFactor == ClientFormFactor.phone && MediaQuery.orientationOf(context) == Orientation.landscape;\n    return PopScope(\n      canPop: false,\n      child: Scaffold(\n        drawer: _drawer(compact: compact),\n        appBar: AppBar(\n          toolbarHeight: compact ? 38 : null,\n          titleSpacing: compact ? 8 : null,\n          title: Row(mainAxisSize: MainAxisSize.min, children: [MacroPadMark(size: compact ? 17 : 22), SizedBox(width: compact ? 6 : 9), Flexible(child: Text(profile?.name ?? 'NEXO', overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: compact ? 13 : null)))]),\n          actions: [\n            IconButton(tooltip: viewLocked ? 'Разблокировать вид' : 'Заблокировать вид', visualDensity: compact ? VisualDensity.compact : VisualDensity.standard, onPressed: _toggleViewLock, icon: Icon(viewLocked ? Icons.lock : Icons.lock_open, size: compact ? 19 : 23)),\n            IconButton(tooltip: 'Повернуть экран', visualDensity: compact ? VisualDensity.compact : VisualDensity.standard, onPressed: () => toggleScreenOrientation(context), icon: Icon(Icons.screen_rotation, size: compact ? 19 : 23)),\n            Padding(padding: EdgeInsets.only(right: compact ? 5 : 10), child: Center(child: Row(children: [Icon(Icons.circle, size: 7, color: connectionError == null && status != 'Отключено' ? mpGreen : mpMuted), const SizedBox(width: 5), if (!compact) Text(status, style: const TextStyle(fontSize: 11))]))),\n          ],\n        ),\n        body: SafeArea(child: connectionError == null ? pages[tab] : _connectionErrorView()),\n        bottomNavigationBar: connectionError == null ? _SharpBottomNav(compact: compact, selectedIndex: tab, onSelected: (value) => setState(() => tab = value), items: const [_SharpNavItem(Icons.grid_view, 'Deck'), _SharpNavItem(Icons.play_circle_outline, 'Media')]) : null,\n      ),\n    );\n  }\n\n  Widget _drawer({required bool compact})''',flags=re.S,label='remote build')

# Compact drawer and explicit switch/forget controls in hidden drawer.
rep(mobile,'    return Drawer(\n      child: SafeArea(', '    return Drawer(\n      width: compact ? 250 : null,\n      child: SafeArea(','drawer width')
rep(mobile,"                  const Padding(padding: EdgeInsets.fromLTRB(16, 14, 16, 6), child: Text('УСТРОЙСТВА', style: TextStyle(color: mpMuted, fontSize: 10, letterSpacing: 1))),",
           "                  const Padding(padding: EdgeInsets.fromLTRB(16, 14, 16, 6), child: Text('СМЕНИТЬ УСТРОЙСТВО', style: TextStyle(color: mpMuted, fontSize: 10, letterSpacing: 1))),",'switch device label')
rep(mobile,'                      subtitle: Text(pc.serverId == serverId ? \'Текущее устройство\' : \'Переключить без QR\', style: const TextStyle(fontSize: 10, color: mpMuted)),',
           '                      subtitle: Text(pc.serverId == serverId ? \'Текущее устройство\' : \'Переключить без QR\', style: const TextStyle(fontSize: 10, color: mpMuted)),','drawer device')
rep(mobile,'                    ),\n                ],\n              ),',
           '''                    ),\n                  const Divider(height: 1),\n                  ListTile(\n                    dense: true,\n                    leading: const Icon(Icons.devices_other, size: 20),\n                    title: const Text('Сменить устройство'),\n                    subtitle: const Text('Вернуться к списку устройств', style: TextStyle(fontSize: 10, color: mpMuted)),\n                    onTap: () { Navigator.of(context).pop(); Future<void>.delayed(const Duration(milliseconds: 100), () { if (mounted) Navigator.of(context).pop('__device_list__'); }); },\n                  ),\n                  ListTile(\n                    dense: true,\n                    leading: const Icon(Icons.link_off, size: 20),\n                    title: const Text('Забыть текущее устройство'),\n                    subtitle: const Text('Для следующего подключения потребуется QR', style: TextStyle(fontSize: 10, color: mpMuted)),\n                    onTap: () async { Navigator.of(context).pop(); await _forgetCurrentDevice(); },\n                  ),\n                ],\n              ),''',label='drawer commands')

# Handle explicit return to device list without trying saved-id lookup.
rep(mobile,'      if (switchTo != null && mounted) {\n        final target = savedPcs[switchTo];\n        if (target != null) await _connectSaved(target);\n      }',
           "      if (switchTo != null && mounted) {\n        if (switchTo == '__device_list__') return;\n        final target = savedPcs[switchTo];\n        if (target != null) await _connectSaved(target);\n      }",'device list return')

# Make connection error not offer gesture-style/back route exit.
rep(mobile,"Row(children: [Expanded(child: OutlinedButton(onPressed: () => Navigator.of(context).pop(), child: const Text('Назад'))), const SizedBox(width: 8), Expanded(child: FilledButton(onPressed: _connect, child: const Text('Повторить')))])",
           "Row(children: [Expanded(child: OutlinedButton(onPressed: () => Navigator.of(context).pop('__device_list__'), child: const Text('Сменить устройство'))), const SizedBox(width: 8), Expanded(child: FilledButton(onPressed: _connect, child: const Text('Повторить')))])",'error action')

# Replace deck canvas with fit-to-all locked view + pan/zoom unlocked view.
sub(mobile,r"  Widget _deckCanvas\(ProfileSnapshot p\) \{.*?\n  \}\n\n  Widget _remoteTile",'''  Widget _deckCanvas(ProfileSnapshot p) {\n    return LayoutBuilder(\n      builder: (_, constraints) {\n        final columns = p.columns.clamp(1, 12).toInt();\n        final rows = p.rows.clamp(1, 12).toInt();\n        const gapBase = 7.0;\n        const padBase = 10.0;\n        final compact = widget.formFactor == ClientFormFactor.phone && MediaQuery.orientationOf(context) == Orientation.landscape;\n        final availableW = (constraints.maxWidth - padBase * 2 - gapBase * (columns - 1)).clamp(1.0, double.infinity);\n        final availableH = (constraints.maxHeight - padBase * 2 - gapBase * (rows - 1)).clamp(1.0, double.infinity);\n        final fitW = availableW / columns;\n        final fitH = availableH / rows;\n        final cellW = min(fitW, fitH / .76).clamp(compact ? 42.0 : 36.0, 150.0);\n        final cellH = cellW * .76;\n        final uiScale = (cellW / 105).clamp(.38, 1.18);\n        final packed = packTiles(p.tiles, rows, columns);\n        final totalW = padBase * 2 + columns * cellW + (columns - 1) * gapBase;\n        final totalH = padBase * 2 + rows * cellH + (rows - 1) * gapBase;\n        final canvas = SizedBox(\n          width: totalW, height: totalH,\n          child: Stack(children: [\n            for (final item in packed) Positioned(\n              left: padBase + item.column * (cellW + gapBase),\n              top: padBase + item.row * (cellH + gapBase),\n              width: item.columnSpan * cellW + (item.columnSpan - 1) * gapBase,\n              height: item.rowSpan * cellH + (item.rowSpan - 1) * gapBase,\n              child: _remoteTile(item.tile, uiScale),\n            ),\n          ]),\n        );\n        return Stack(children: [\n          Center(child: InteractiveViewer(\n            transformationController: _deckTransform,\n            panEnabled: !viewLocked, scaleEnabled: !viewLocked,\n            minScale: .45, maxScale: 3.2, boundaryMargin: const EdgeInsets.all(500), constrained: false,\n            child: canvas,\n          )),\n          Positioned(right: compact ? 5 : 8, top: compact ? 5 : 8, child: Material(\n            color: const Color(0xee202326),\n            shape: const RoundedRectangleBorder(borderRadius: BorderRadius.zero, side: BorderSide(color: mpBorder)),\n            child: InkWell(onTap: _toggleViewLock, child: Padding(padding: EdgeInsets.all(compact ? 6 : 8), child: Icon(viewLocked ? Icons.lock : Icons.lock_open, size: compact ? 16 : 19, color: Colors.white))),\n          )),\n        ]);\n      },\n    );\n  }\n\n  Widget _remoteTile''',flags=re.S,label='deck canvas')
# dart:math min
rep(mobile,"import 'dart:io';\n", "import 'dart:io';\nimport 'dart:math';\n",'dart math')

# Compact page selector and bottom navigation.
rep(mobile,'      height: 48,', '      height: widget.formFactor == ClientFormFactor.phone && MediaQuery.orientationOf(context) == Orientation.landscape ? 34 : 48,','page selector height')
rep(mobile,'  final List<_SharpNavItem> items;\n  const _SharpBottomNav({required this.selectedIndex, required this.onSelected, required this.items});',
           '  final List<_SharpNavItem> items;\n  final bool compact;\n  const _SharpBottomNav({required this.selectedIndex, required this.onSelected, required this.items, this.compact = false});','bottom nav compact field')
rep(mobile,'            height: 66,', '            height: compact ? 44 : 66,','bottom nav height')
rep(mobile,'child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [Icon(items[i].icon, color: Colors.white, size: 23), const SizedBox(height: 4), Text(items[i].label, style: const TextStyle(color: Colors.white, fontSize: 11))]),',
           'child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [Icon(items[i].icon, color: Colors.white, size: compact ? 18 : 23), SizedBox(height: compact ? 1 : 4), Text(items[i].label, style: TextStyle(color: Colors.white, fontSize: compact ? 9 : 11))]),','bottom nav content')

# Update rolling preview label/notes.
p=Path(workflow); s=p.read_text(encoding='utf-8')
s=s.replace('0.8.0-preview','0.9.0-preview').replace('v0.8: macro icon library, imported images and screenshot icons','NEXO v0.9: per-key labels, landscape compact UI, lockable pan/zoom deck, explicit device switching and forget-device controls')
p.write_text(s,encoding='utf-8')

print('NEXO v0.9 patch applied')
