from pathlib import Path

root = Path('.')
cs_path = root / 'src/windows/MacroPadRemote/MainWindow.xaml.cs'
xaml_path = root / 'src/windows/MacroPadRemote/MainWindow.xaml'


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f'Missing pattern: {label}')
    return text.replace(old, new, 1)

cs = cs_path.read_text(encoding='utf-8')

cs = replace_once(
    cs,
    '    private readonly Dictionary<string, List<ushort>> _heldRemoteKeys = new();\n',
    '    private readonly Dictionary<string, List<ushort>> _heldRemoteKeys = new();\n'
    '    private System.Windows.Forms.NotifyIcon? _trayIcon;\n'
    '    private bool _allowExit;\n'
    '    private bool _trayHintShown;\n',
    'tray fields')

cs = replace_once(
    cs,
    '        RefreshProfiles();\n        Loaded += MainWindow_Loaded;\n',
    '        RefreshProfiles();\n'
    '        SetupTrayIcon();\n'
    '        Loaded += MainWindow_Loaded;\n'
    '        StateChanged += MainWindow_StateChanged;\n'
    '        Closing += MainWindow_Closing;\n',
    'tray event hooks')

old_loaded = '''    private async void MainWindow_Loaded(object sender, RoutedEventArgs e)
    {
        BeginStartupAnimation();
        UpdateZoom();
        try
        {
            await StartSelectedTransportAsync();
        }
        catch (Exception ex)
        {
            DeviceStatus.Text = $"Ошибка связи: {ex.Message}";
        }
        await Task.Delay(420);
        HideStartupOverlay();
    }'''
new_loaded = '''    private async void MainWindow_Loaded(object sender, RoutedEventArgs e)
    {
        BeginStartupAnimation();
        StartupStatus.Text = "Подготовка рабочего пространства…";
        UpdateZoom();
        await Task.Delay(120);
        try
        {
            StartupStatus.Text = "Запуск связи с устройствами…";
            await StartSelectedTransportAsync();
            StartupStatus.Text = "Готово";
        }
        catch (Exception ex)
        {
            DeviceStatus.Text = $"Ошибка связи: {ex.Message}";
            StartupStatus.Text = "NEXO запущен • связь можно перезапустить в настройках";
        }
        await Task.Delay(260);
        HideStartupOverlay();
    }'''
cs = replace_once(cs, old_loaded, new_loaded, 'startup loading state')

tray_methods = r'''

    private void SetupTrayIcon()
    {
        try
        {
            var menu = new System.Windows.Forms.ContextMenuStrip();
            menu.Items.Add("Открыть NEXO", null, (_, _) => Dispatcher.BeginInvoke(ShowFromTray));
            menu.Items.Add(new System.Windows.Forms.ToolStripSeparator());
            menu.Items.Add("Выход", null, (_, _) => Dispatcher.BeginInvoke(new Action(() => _ = ExitFromTrayAsync())));

            var icon = System.Drawing.Icon.ExtractAssociatedIcon(Environment.ProcessPath ?? Process.GetCurrentProcess().MainModule?.FileName ?? "");
            _trayIcon = new System.Windows.Forms.NotifyIcon
            {
                Text = "NEXO — удалённое управление компьютером",
                Visible = true,
                ContextMenuStrip = menu,
                Icon = icon
            };
            _trayIcon.DoubleClick += (_, _) => Dispatcher.BeginInvoke(ShowFromTray);
        }
        catch
        {
            _trayIcon = null;
        }
    }

    private void MainWindow_StateChanged(object? sender, EventArgs e)
    {
        if (WindowState == WindowState.Minimized)
            HideToTray();
    }

    private void MainWindow_Closing(object? sender, CancelEventArgs e)
    {
        if (_allowExit) return;
        e.Cancel = true;
        HideToTray();
    }

    private void HideToTray()
    {
        ShowInTaskbar = false;
        Hide();
        if (_trayIcon is not null && !_trayHintShown)
        {
            _trayHintShown = true;
            _trayIcon.BalloonTipTitle = "NEXO продолжает работать";
            _trayIcon.BalloonTipText = "Приложение скрыто в системный трей и продолжает принимать команды с телефона и планшета.";
            _trayIcon.ShowBalloonTip(2600);
        }
    }

    private void ShowFromTray()
    {
        ShowInTaskbar = true;
        Show();
        WindowState = WindowState.Normal;
        Activate();
        Topmost = true;
        Topmost = false;
        Focus();
    }

    private async Task ExitFromTrayAsync()
    {
        _allowExit = true;
        if (_trayIcon is not null)
        {
            _trayIcon.Visible = false;
            _trayIcon.Dispose();
            _trayIcon = null;
        }
        try { await StopAllTransportsAsync(); } catch { }
        System.Windows.Application.Current.Shutdown();
    }
'''
cs = replace_once(cs, '\n    private void LoadState()\n', tray_methods + '\n    private void LoadState()\n', 'tray methods')
cs_path.write_text(cs, encoding='utf-8')

xaml = xaml_path.read_text(encoding='utf-8')
old_xaml = '''                    <TextBlock Text="NEXO" HorizontalAlignment="Center" Margin="0,18,0,0" FontSize="25" FontWeight="Bold" CharacterSpacing="220"/>
                    <ProgressBar Width="120" Height="2" IsIndeterminate="True" Margin="0,22,0,0" Foreground="#1688FF" Background="#24272A"/>'''
new_xaml = '''                    <TextBlock Text="NEXO" HorizontalAlignment="Center" Margin="0,18,0,0" FontSize="25" FontWeight="Bold" CharacterSpacing="220"/>
                    <TextBlock x:Name="StartupStatus" Text="Загрузка…" HorizontalAlignment="Center" Margin="0,10,0,0" FontSize="11" Foreground="#9DA3A8"/>
                    <ProgressBar Width="120" Height="2" IsIndeterminate="True" Margin="0,16,0,0" Foreground="#1688FF" Background="#24272A"/>'''
xaml = replace_once(xaml, old_xaml, new_xaml, 'startup status text')
xaml_path.write_text(xaml, encoding='utf-8')

print('NEXO Windows tray + startup loading patch applied')
