from pathlib import Path
import re

def rep(text, old, new, label):
    if old not in text:
        raise SystemExit(f'missing marker: {label}')
    return text.replace(old, new, 1)

# ---------- mobile ----------
p=Path('src/mobile/macropad_mobile/lib/main.dart')
s=p.read_text(encoding='utf-8')
s=rep(s,"  bool viewLocked = true;\n  final TransformationController _deckTransform = TransformationController();", "  bool scaleLocked = false;\n  bool panLocked = false;\n  bool bottomNavVisible = false;\n  Orientation? _lastOrientation;\n  final TransformationController _deckTransform = TransformationController();", 'mobile state')
s=rep(s,"  Future<void> _sendTile(TileSnapshot tile) => widget.transport.send({'type': 'press', 'tileId': tile.id});", "  Future<void> _sendTile(TileSnapshot tile, {bool longPress = false}) async {\n    await HapticFeedback.selectionClick();\n    await widget.transport.send({'type': longPress ? 'longPress' : 'press', 'tileId': tile.id});\n  }", 'tile send')
s=rep(s,"  Future<void> _switchProfile(String profileId) => widget.transport.send({'type': 'switchProfile', 'profileId': profileId});", "  Future<void> _switchProfile(String profileId) => widget.transport.send({'type': 'switchProfile', 'profileId': profileId, 'force': true});", 'force profile')
old="""  void _toggleViewLock() {
    final next = !viewLocked;
    setState(() => viewLocked = next);
    if (next) {
      _deckReturnController.stop();
      _deckReturnAnimation = Matrix4Tween(begin: _deckTransform.value.clone(), end: Matrix4.identity()).animate(CurvedAnimation(parent: _deckReturnController, curve: Curves.easeOutCubic));
      _deckReturnController.forward(from: 0);
    }
  }
"""
new="""  void _toggleScaleLock() => setState(() => scaleLocked = !scaleLocked);
  void _togglePanLock() => setState(() => panLocked = !panLocked);
  void _fitDeck() {
    _deckReturnController.stop();
    _deckReturnAnimation = Matrix4Tween(begin: _deckTransform.value.clone(), end: Matrix4.identity())
        .animate(CurvedAnimation(parent: _deckReturnController, curve: Curves.easeOutCubic));
    _deckReturnController.forward(from: 0);
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final o = MediaQuery.orientationOf(context);
    if (_lastOrientation != null && _lastOrientation != o) {
      WidgetsBinding.instance.addPostFrameCallback((_) { if (mounted) _fitDeck(); });
      if (o == Orientation.landscape) bottomNavVisible = false;
    }
    _lastOrientation = o;
  }
"""
s=rep(s,old,new,'view locks')
# appbar lock -> only rotation/status; controls live over canvas
s=s.replace("            IconButton(tooltip: viewLocked ? 'Разблокировать вид' : 'Заблокировать вид', visualDensity: compact ? VisualDensity.compact : VisualDensity.standard, onPressed: _toggleViewLock, icon: Icon(viewLocked ? Icons.lock : Icons.lock_open, size: compact ? 19 : 23)),\n","")
# bottom nav hidden in landscape
s=rep(s,"        body: SafeArea(child: connectionError == null ? pages[tab] : _connectionErrorView()),\n        bottomNavigationBar: connectionError == null ? _SharpBottomNav(compact: compact, selectedIndex: tab, onSelected: (value) => setState(() => tab = value), items: const [_SharpNavItem(Icons.grid_view, 'Deck'), _SharpNavItem(Icons.play_circle_outline, 'Media')]) : null,", "        body: SafeArea(child: connectionError == null ? _workspaceBody(pages, compact) : _connectionErrorView()),\n        bottomNavigationBar: connectionError == null && !compact ? _SharpBottomNav(compact: false, selectedIndex: tab, onSelected: (value) => setState(() => tab = value), items: const [_SharpNavItem(Icons.grid_view, 'Deck'), _SharpNavItem(Icons.play_circle_outline, 'Media')]) : null,", 'mobile body')
insert="""
  Widget _workspaceBody(List<Widget> pages, bool compact) {
    if (!compact) return pages[tab];
    return Stack(children: [
      Positioned.fill(child: pages[tab]),
      if (bottomNavVisible)
        Positioned(left: 18, right: 18, bottom: 26, child: ClipRRect(
          borderRadius: BorderRadius.circular(14),
          child: _SharpBottomNav(compact: true, selectedIndex: tab, onSelected: (value) => setState(() => tab = value), items: const [_SharpNavItem(Icons.grid_view, 'Deck'), _SharpNavItem(Icons.play_circle_outline, 'Media')]),
        )),
      Positioned(left: 0, right: 0, bottom: 2, child: Center(child: Material(
        color: mpPanel2,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12), side: const BorderSide(color: mpBorder)),
        child: InkWell(borderRadius: BorderRadius.circular(12), onTap: () => setState(() => bottomNavVisible = !bottomNavVisible),
          child: Padding(padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 3), child: Icon(bottomNavVisible ? Icons.keyboard_arrow_down : Icons.keyboard_arrow_up, size: 18))),
      ))),
    ]);
  }

"""
s=rep(s,"  Widget _drawer({required bool compact}) {",insert+"  Widget _drawer({required bool compact}) {",'workspace body insert')
# page selector below workspace
s=rep(s,"    return Column(\n      children: [\n        _pageSelector(p),\n        Expanded(child: _deckCanvas(p)),\n      ],\n    );", "    return Column(\n      children: [\n        Expanded(child: _deckCanvas(p)),\n        _pageSelector(p),\n      ],\n    );", 'selector below')
# fit all cells / centered
s=s.replace("final cellW = min(fitW, fitH / .76).clamp(compact ? 42.0 : 36.0, 150.0);","final cellW = min(fitW, fitH / .76).clamp(18.0, 150.0);")
# interactive viewer controls + 3 buttons
old2="""          Center(child: InteractiveViewer(
            transformationController: _deckTransform,
            panEnabled: !viewLocked, scaleEnabled: !viewLocked,
            minScale: .45, maxScale: 3.2, boundaryMargin: const EdgeInsets.all(500), constrained: false,
            child: canvas,
          )),
          Positioned(right: compact ? 5 : 8, top: compact ? 5 : 8, child: Material(
            color: const Color(0xee202326),
            shape: const RoundedRectangleBorder(borderRadius: BorderRadius.zero, side: BorderSide(color: mpBorder)),
            child: InkWell(onTap: _toggleViewLock, child: Padding(padding: EdgeInsets.all(compact ? 6 : 8), child: Icon(viewLocked ? Icons.lock : Icons.lock_open, size: compact ? 16 : 19, color: Colors.white))),
          )),
"""
new2="""          Center(child: InteractiveViewer(
            transformationController: _deckTransform,
            panEnabled: !panLocked, scaleEnabled: !scaleLocked,
            minScale: .35, maxScale: 3.2, boundaryMargin: const EdgeInsets.all(500), constrained: false,
            child: canvas,
          )),
          Positioned(right: compact ? 5 : 8, top: compact ? 5 : 8, child: Material(
            color: const Color(0xee202326),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10), side: const BorderSide(color: mpBorder)),
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              IconButton(tooltip: scaleLocked ? 'Разблокировать масштаб' : 'Зафиксировать масштаб', onPressed: _toggleScaleLock, icon: Icon(scaleLocked ? Icons.lock : Icons.lock_open), iconSize: compact ? 16 : 19, visualDensity: VisualDensity.compact),
              IconButton(tooltip: panLocked ? 'Разблокировать перемещение' : 'Заблокировать перемещение', onPressed: _togglePanLock, icon: Icon(panLocked ? Icons.pan_tool_alt : Icons.pan_tool_outlined), iconSize: compact ? 16 : 19, visualDensity: VisualDensity.compact),
              IconButton(tooltip: 'Вписать и центрировать', onPressed: _fitDeck, icon: const Icon(Icons.center_focus_strong), iconSize: compact ? 16 : 19, visualDensity: VisualDensity.compact),
            ]),
          )),
"""
s=rep(s,old2,new2,'interactive controls')
# long press + haptic once
s=rep(s,"        onTap: blank ? null : () => _sendTile(tile),", "        onTap: blank ? null : () => _sendTile(tile),\n        onLongPress: blank ? null : () => _sendTile(tile, longPress: true),", 'long press')
# bump title hints (optional)
s=s.replace('NEXO v0.9','NEXO v1.0')
p.write_text(s,encoding='utf-8')

# ---------- windows XAML ----------
p=Path('src/windows/MacroPadRemote/MainWindow.xaml')
x=p.read_text(encoding='utf-8')
x=x.replace('  v0.8 preview','  v1.0 preview')
x=x.replace('<Grid.RowDefinitions><RowDefinition Height="*"/><RowDefinition Height="1"/><RowDefinition Height="330"/></Grid.RowDefinitions>','<Grid.RowDefinitions><RowDefinition Height="*"/><RowDefinition Height="0"/><RowDefinition Height="0"/></Grid.RowDefinitions>')
x=x.replace('<StackPanel Grid.Column="1" Orientation="Horizontal" VerticalAlignment="Center"><ComboBox x:Name="PageBox" Width="170" DisplayMemberPath="Name" SelectionChanged="PageBox_SelectionChanged"/><Button Content="＋" Width="38" Margin="7,0,0,0" Click="AddPage_Click" ToolTip="Добавить страницу"/></StackPanel>', '<StackPanel Grid.Column="1" Orientation="Horizontal" VerticalAlignment="Center"><Button x:Name="ProfileSettingsButton" Content="⚙" Width="38" Height="32" Click="ProfileSettingsButton_Click" ToolTip="Свойства профиля"/></StackPanel>')
start=x.index('        <!-- Bottom profile properties -->')
end=x.index('        <!-- Connection settings:')
replacement=r'''        <!-- Bottom action properties -->
        <Border Grid.Row="2" Grid.Column="1" Background="#191B1D" BorderBrush="{StaticResource Border}" BorderThickness="0,1,0,0">
            <ScrollViewer VerticalScrollBarVisibility="Auto"><Grid Margin="18,10">
                <Grid.RowDefinitions><RowDefinition Height="28"/><RowDefinition/></Grid.RowDefinitions>
                <TextBlock Text="Свойства действия" FontSize="15" FontWeight="SemiBold"/>
                <Grid Grid.Row="1"><Grid.ColumnDefinitions><ColumnDefinition Width="1.1*"/><ColumnDefinition/><ColumnDefinition/></Grid.ColumnDefinitions>
                    <StackPanel Margin="0,0,12,0"><TextBlock x:Name="InspectorHint" Text="Выберите плитку." Foreground="{StaticResource Muted}" FontSize="10"/><TextBlock Text="Название" Foreground="{StaticResource Muted}" FontSize="10"/><TextBox x:Name="InspectorTitleBox" Height="30" TextChanged="InspectorChanged"/><CheckBox x:Name="InspectorShowLabel" Content="Показывать название функции" IsChecked="True" Margin="0,5,0,0"/></StackPanel>
                    <StackPanel Grid.Column="1" Margin="0,0,12,0"><TextBlock Text="Тип действия" Foreground="{StaticResource Muted}" FontSize="10"/><TextBox x:Name="InspectorTypeBox" Height="30" IsReadOnly="True"/><TextBlock x:Name="InspectorValueLabel" Text="Параметр" Foreground="{StaticResource Muted}" FontSize="10" Margin="0,5,0,0"/><TextBox x:Name="InspectorValueBox" Height="30" TextChanged="InspectorChanged"/></StackPanel>
                    <StackPanel Grid.Column="2"><TextBlock Text="Горячая клавиша" Foreground="{StaticResource Muted}" FontSize="10"/><Grid><Grid.ColumnDefinitions><ColumnDefinition/><ColumnDefinition Width="90"/></Grid.ColumnDefinitions><TextBox x:Name="InspectorHotkeyBox" Height="30" IsReadOnly="True"/><Button x:Name="RecordHotkeyButton" Grid.Column="1" Content="Записать" Margin="5,0,0,0" Click="RecordHotkey_Click" PreviewKeyDown="RecordHotkey_PreviewKeyDown"/></Grid><StackPanel Orientation="Horizontal" Margin="0,8,0,0"><Border x:Name="InspectorIconPreview" Width="38" Height="38" Background="#111315" BorderBrush="{StaticResource Border}" BorderThickness="1" Padding="4"/><TextBlock x:Name="InspectorIconStatus" Width="70" Margin="6,0" VerticalAlignment="Center" FontSize="9"/><Button x:Name="IconLibraryButton" Content="Иконка" Width="66" Click="IconLibrary_Click"/><Button x:Name="IconImportButton" Content="Импорт" Width="62" Margin="5,0,0,0" Click="IconImport_Click"/><Button x:Name="IconScreenshotButton" Content="Снимок" Width="62" Margin="5,0,0,0" Click="IconScreenshot_Click"/><Button x:Name="IconResetButton" Content="Авто" Width="52" Margin="5,0,0,0" Click="IconReset_Click"/></StackPanel><StackPanel Orientation="Horizontal" HorizontalAlignment="Right" Margin="0,8,0,0"><Button Content="Очистить" Width="84" Click="ClearTile_Click"/><Button Content="Применить" Width="94" Margin="6,0,0,0" Click="ApplyInspector_Click"/></StackPanel></StackPanel>
                </Grid>
            </Grid></ScrollViewer>
        </Border>

        <!-- Right: action library -->
        <Border Grid.Row="1" Grid.RowSpan="2" Grid.Column="2" Background="#1B1D1F" BorderBrush="{StaticResource Border}" BorderThickness="1,0,0,0">
            <Grid><Grid.RowDefinitions><RowDefinition Height="60"/><RowDefinition Height="*"/></Grid.RowDefinitions>
                <Grid Margin="14,12"><Grid.ColumnDefinitions><ColumnDefinition/><ColumnDefinition Width="38"/></Grid.ColumnDefinitions><TextBox x:Name="ActionSearchBox" Height="34" VerticalContentAlignment="Center" ToolTip="Поиск действий" TextChanged="ActionSearchBox_TextChanged"/><Button Grid.Column="1" Content="☷" Margin="6,0,0,0" Padding="0"/></Grid>
                <TabControl Grid.Row="1" x:Name="ActionTabs"><TabItem Header="Клавиша"><ListBox x:Name="ActionLibraryList" Margin="8" PreviewMouseLeftButtonDown="ActionLibrary_PreviewMouseLeftButtonDown" PreviewMouseMove="ActionLibrary_PreviewMouseMove" MouseDoubleClick="ActionLibrary_DoubleClick"><ListBox.ItemTemplate><DataTemplate><Grid Margin="7,6"><Grid.ColumnDefinitions><ColumnDefinition Width="34"/><ColumnDefinition/></Grid.ColumnDefinitions><TextBlock Text="{Binding Icon}" FontSize="20" HorizontalAlignment="Center" VerticalAlignment="Center"/><StackPanel Grid.Column="1" Margin="8,0,0,0"><TextBlock Text="{Binding Title}" FontWeight="SemiBold"/><TextBlock Text="{Binding Description}" Foreground="{StaticResource Muted}" FontSize="10" TextWrapping="Wrap"/></StackPanel></Grid></DataTemplate></ListBox.ItemTemplate><ListBox.GroupStyle><GroupStyle><GroupStyle.HeaderTemplate><DataTemplate><Border Background="#202326" BorderBrush="{StaticResource Border}" BorderThickness="0,1,0,1" Padding="10,8"><TextBlock Text="{Binding Name}" FontWeight="SemiBold"/></Border></DataTemplate></GroupStyle.HeaderTemplate></GroupStyle></ListBox.GroupStyle></ListBox></TabItem><TabItem Header="Информационная"><StackPanel Margin="14"><TextBlock Text="Информационные плитки" FontSize="16" FontWeight="SemiBold"/></StackPanel></TabItem></TabControl>
            </Grid>
        </Border>

        <primitives:Popup x:Name="ProfileSettingsPopup" PlacementTarget="{Binding ElementName=ProfileSettingsButton}" Placement="Bottom" StaysOpen="False" AllowsTransparency="True" PopupAnimation="Fade">
            <Border Width="470" Background="#202326" BorderBrush="#4A5055" BorderThickness="1" Padding="16" Margin="0,6,0,0"><StackPanel><TextBlock Text="Свойства профиля" FontSize="17" FontWeight="SemiBold"/><TextBlock Text="Название" Foreground="{StaticResource Muted}" FontSize="10" Margin="0,10,0,3"/><TextBox x:Name="ProfileName" Height="32"/><TextBlock Text="Описание" Foreground="{StaticResource Muted}" FontSize="10" Margin="0,7,0,3"/><TextBox x:Name="ProfileDescription" Height="55" AcceptsReturn="True" TextWrapping="Wrap"/><Grid Margin="0,9,0,0"><Grid.ColumnDefinitions><ColumnDefinition/><ColumnDefinition Width="10"/><ColumnDefinition/></Grid.ColumnDefinitions><StackPanel><TextBlock Text="Столбцы" Foreground="{StaticResource Muted}" FontSize="10"/><TextBox x:Name="ColumnsBox" Height="32"/></StackPanel><StackPanel Grid.Column="2"><TextBlock Text="Строки" Foreground="{StaticResource Muted}" FontSize="10"/><TextBox x:Name="RowsBox" Height="32"/></StackPanel></Grid><TextBlock Text="Масштаб" Foreground="{StaticResource Muted}" FontSize="10" Margin="0,8,0,2"/><Slider x:Name="ZoomSlider" Minimum="0.55" Maximum="2.5" Value="1" ValueChanged="ZoomSlider_ValueChanged"/><StackPanel Orientation="Horizontal" Margin="0,7,0,0"><CheckBox x:Name="ShowNumbers" Content="Номера клавиш" IsChecked="True"/><CheckBox x:Name="ShowLabels" Content="Подписи" IsChecked="True" Margin="12,0,0,0"/></StackPanel><Button Content="Сохранить" HorizontalAlignment="Right" Width="110" Margin="0,12,0,0" Click="SaveProfile_Click"/></StackPanel></Border>
        </primitives:Popup>

'''
x=x[:start]+replacement+x[end:]
p.write_text(x,encoding='utf-8')

# ---------- windows code ----------
p=Path('src/windows/MacroPadRemote/MainWindow.xaml.cs')
c=p.read_text(encoding='utf-8')
c=c.replace('    private Point _actionDragStart;','    private Point _actionDragStart;\n    private Point _tileDragStart;\n    private Window? _qrWindow;')
# PageBox removed: guard references by removing assignment and handler body references
c=c.replace('        PageBox.ItemsSource = null;\n        PageBox.ItemsSource = _profile.Pages;\n        PageBox.SelectedItem = _page;\n','')
c=re.sub(r'\n    private void PageBox_SelectionChanged\(object sender, SelectionChangedEventArgs e\)\n    \{.*?\n    \}\n', '\n', c, count=1, flags=re.S)
# tile drag swap
c=c.replace('        button.Click += (_, _) => SelectTile(button, tile);', '        button.PreviewMouseLeftButtonDown += (_, e) => _tileDragStart = e.GetPosition(this);\n        button.PreviewMouseMove += (_, e) => Tile_PreviewMouseMove(button, tile, e);\n        button.Click += (_, _) => SelectTile(button, tile);',1)
old='''    private void Tile_DragOver(object sender, DragEventArgs e)
    {
        e.Effects = e.Data.GetDataPresent("MacroPadAction") ? DragDropEffects.Copy : DragDropEffects.None;
        e.Handled = true;
    }

    private void Tile_Drop(object sender, DragEventArgs e)
    {
        if (sender is not Button { Tag: Tile tile } button || e.Data.GetData("MacroPadAction") is not ActionItem action) return;
        AssignAction(tile, action);
        SelectTile(button, tile);
        SaveAndBroadcast();
        e.Handled = true;
    }
'''
new='''    private void Tile_PreviewMouseMove(Button button, Tile tile, MouseEventArgs e)
    {
        if (e.LeftButton != MouseButtonState.Pressed || _page is null) return;
        var current = e.GetPosition(this);
        if (Math.Abs(current.X - _tileDragStart.X) < SystemParameters.MinimumHorizontalDragDistance && Math.Abs(current.Y - _tileDragStart.Y) < SystemParameters.MinimumVerticalDragDistance) return;
        DragDrop.DoDragDrop(button, new DataObject("NexoTile", tile.Id), DragDropEffects.Move);
    }

    private void Tile_DragOver(object sender, DragEventArgs e)
    {
        e.Effects = e.Data.GetDataPresent("MacroPadAction") ? DragDropEffects.Copy : e.Data.GetDataPresent("NexoTile") ? DragDropEffects.Move : DragDropEffects.None;
        e.Handled = true;
    }

    private void Tile_Drop(object sender, DragEventArgs e)
    {
        if (sender is not Button { Tag: Tile tile } button || _page is null) return;
        if (e.Data.GetData("MacroPadAction") is ActionItem action)
        {
            AssignAction(tile, action); SelectTile(button, tile); SaveAndBroadcast(); e.Handled = true; return;
        }
        if (e.Data.GetData("NexoTile") is string sourceId)
        {
            var source = _page.Tiles.FirstOrDefault(t => t.Id == sourceId);
            if (source is null || ReferenceEquals(source, tile)) return;
            var a = _page.Tiles.IndexOf(source); var b = _page.Tiles.IndexOf(tile);
            if (a < 0 || b < 0) return;
            (_page.Tiles[a], _page.Tiles[b]) = (_page.Tiles[b], _page.Tiles[a]);
            SaveAndBroadcast(); e.Handled = true;
        }
    }
'''
if old not in c: raise SystemExit('missing tile drop block')
c=c.replace(old,new,1)
# profile gear
c=c.replace('    private void HeaderSettingsButton_Click(object sender, RoutedEventArgs e)\n    {\n        SettingsPopup.IsOpen = !SettingsPopup.IsOpen;\n    }', '''    private void ProfileSettingsButton_Click(object sender, RoutedEventArgs e) => ProfileSettingsPopup.IsOpen = !ProfileSettingsPopup.IsOpen;

    private async void HeaderSettingsButton_Click(object sender, RoutedEventArgs e)
    {
        var win = new Window { Owner = this, Title = "NEXO — подключение и устройства", Width = 560, Height = 560, WindowStartupLocation = WindowStartupLocation.CenterOwner, Background = (Brush)FindResource("Bg") };
        var root = new StackPanel { Margin = new Thickness(18) };
        root.Children.Add(new TextBlock { Text = "Подключение", FontSize = 20, FontWeight = FontWeights.SemiBold });
        var combo = new ComboBox { Height = 34, Margin = new Thickness(0,10,0,10), ItemsSource = new[] { "Wi‑Fi", "Bluetooth LE" }, SelectedIndex = SelectedTransport() == "Bluetooth" ? 1 : 0 };
        root.Children.Add(combo);
        var qr = new Button { Content = "Показать QR-код", Height = 34, Margin = new Thickness(0,0,0,16) }; qr.Click += ShowQr_Click; root.Children.Add(qr);
        root.Children.Add(new TextBlock { Text = "Привязанные устройства", FontSize = 16, FontWeight = FontWeights.SemiBold, Margin = new Thickness(0,4,0,8) });
        foreach (var d in _state.TrustedDevices.OrderByDescending(x => x.LastSeenUtc))
        {
            var row = new Grid { Height = 46, Margin = new Thickness(0,0,0,4) }; row.ColumnDefinitions.Add(new ColumnDefinition()); row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(42) });
            row.Children.Add(new TextBlock { Text = $"{d.Name}   •   {d.Transport}", VerticalAlignment = VerticalAlignment.Center, Foreground = Brushes.White });
            var more = new Button { Content = "⋮", Tag = d }; more.Click += TrustedDeviceMenu_Click; Grid.SetColumn(more,1); row.Children.Add(more); root.Children.Add(row);
        }
        combo.SelectionChanged += async (_, _) => { await StopAllTransportsAsync(); _state.Transport = combo.SelectedIndex == 1 ? "Bluetooth" : "Wifi"; ApplyTransport(); SaveState(); await StartSelectedTransportAsync(); };
        win.Content = new ScrollViewer { Content = root }; win.ShowDialog();
    }''')
# auto close QR
c=c.replace('        SaveState();\n        RefreshTrustedDevices();\n        return device;', '        SaveState();\n        RefreshTrustedDevices();\n        Dispatcher.BeginInvoke(() => { if (_qrWindow is not null) { _qrWindow.Close(); _qrWindow = null; } });\n        return device;',1)
c=c.replace('        var window = new Window { Owner = this, Title = "Быстрое подключение", Width = 440, Height = 525, ResizeMode = ResizeMode.NoResize, WindowStartupLocation = WindowStartupLocation.CenterOwner, Background = (Brush)FindResource("Bg") };', '        var window = new Window { Owner = this, Title = "Быстрое подключение", Width = 440, Height = 525, ResizeMode = ResizeMode.NoResize, WindowStartupLocation = WindowStartupLocation.CenterOwner, Background = (Brush)FindResource("Bg") };\n        _qrWindow = window;\n        window.Closed += (_, _) => { if (ReferenceEquals(_qrWindow, window)) _qrWindow = null; };')
# long press accepted as distinct protocol, execute once
c=c.replace('            if (root.TryGetProperty("tileId", out var tileIdProp))', '            if ((messageType == "press" || messageType == "longPress") && root.TryGetProperty("tileId", out var tileIdProp))')
# user forced profile switching explicitly wins
c=c.replace('                var profileId = profileIdProp.GetString() ?? "";', '                var profileId = profileIdProp.GetString() ?? "";\n                var forced = root.TryGetProperty("force", out var forceProp) && forceProp.ValueKind == JsonValueKind.True;')
c=c.replace('                    await BroadcastSnapshotAsync();\n                }\n                return;\n            }\n\n            if (messageType == "switchPage"', '                    if (forced) Dispatcher.Invoke(() => DeviceStatus.Text = $"Профиль выбран с телефона: {profile.Name}");\n                    await BroadcastSnapshotAsync();\n                }\n                return;\n            }\n\n            if (messageType == "switchPage"',1)
p.write_text(c,encoding='utf-8')

# versions
p=Path('src/mobile/macropad_mobile/pubspec.yaml'); t=p.read_text(); t=re.sub(r'^version: .*$', 'version: 1.0.0+40', t, flags=re.M); p.write_text(t)
p=Path('src/windows/MacroPadRemote/MacroPadRemote.csproj'); t=p.read_text(); t=t.replace('<Version>0.9.0</Version>','<Version>1.0.0</Version>').replace('<InformationalVersion>0.9.0-preview</InformationalVersion>','<InformationalVersion>1.0.0-preview</InformationalVersion>'); p.write_text(t)
print('patched NEXO v1.0')
