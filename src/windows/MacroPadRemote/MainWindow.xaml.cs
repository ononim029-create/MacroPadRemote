using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Net.NetworkInformation;
using System.Net.Sockets;
using System.Net.WebSockets;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using QRCoder;

namespace MacroPadRemote;

public partial class MainWindow : Window
{
    private const int WebSocketPort = 8765;
    private readonly string _statePath;
    private readonly ObservableCollection<Profile> _profiles = new();
    private readonly List<WebSocket> _clients = new();
    private readonly Dictionary<WebSocket, string> _clientIds = new();
    private readonly JsonSerializerOptions _json = new() { WriteIndented = true, PropertyNamingPolicy = JsonNamingPolicy.CamelCase };
    private readonly ObservableCollection<ActionItem> _actions = new();
    private readonly LanDiscoveryService _lanDiscovery;
    private readonly BleGattServer _ble = new();

    private AppState _state = new();
    private Profile? _profile;
    private DeckPage? _page;
    private Tile? _selected;
    private Button? _selectedButton;
    private WebApplication? _server;
    private string _pairToken = "";
    private bool _updating;
    private bool _capturingHotkey;
    private bool _bleAuthenticated;
    private string _bleClientId = "";
    private double _fitScale = 1;
    private double _userZoom = 1;
    private Point _actionDragStart;
    private Point _tileDragStart;
    private Window? _qrWindow;
    private readonly Dictionary<string, List<ushort>> _heldRemoteKeys = new();
    private System.Windows.Forms.NotifyIcon? _trayIcon;
    private bool _allowExit;
    private bool _trayHintShown;

    public MainWindow()
    {
        InitializeComponent();

        var dir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "MacroPadRemote");
        Directory.CreateDirectory(dir);
        _statePath = Path.Combine(dir, "presets.json");

        LoadState();
        ProfileBox.ItemsSource = _profiles;
        RefreshTrustedDevices();

        foreach (var action in BuildActionLibrary())
            _actions.Add(action);
        ConfigureActionView();

        _lanDiscovery = new LanDiscoveryService(WebSocketPort, LocalIp, () => _state.ServerId);
        _lanDiscovery.PeerSeen += endpoint => Dispatcher.InvokeAsync(() =>
        {
            DeviceStatus.Text = $"Телефон найден в сети: {endpoint.Address}";
        });

        _ble.MessageReceived += HandleBleMessageAsync;
        _ble.StatusChanged += status => Dispatcher.InvokeAsync(() =>
        {
            if (SelectedTransport() == "Bluetooth")
                DeviceStatus.Text = $"Bluetooth LE: {status}";
        });

        ApplyTransport();
        RefreshProfiles();
        SetupTrayIcon();
        Loaded += MainWindow_Loaded;
        StateChanged += MainWindow_StateChanged;
        Closing += MainWindow_Closing;
    }

    private async void MainWindow_Loaded(object sender, RoutedEventArgs e)
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
    }

    private void BeginStartupAnimation()
    {
        var scale = new DoubleAnimation(.86, 1.0, TimeSpan.FromMilliseconds(620)) { EasingFunction = new BackEase { EasingMode = EasingMode.EaseOut, Amplitude = .18 } };
        StartupMarkScale.BeginAnimation(ScaleTransform.ScaleXProperty, scale);
        StartupMarkScale.BeginAnimation(ScaleTransform.ScaleYProperty, scale);
    }

    private void HideStartupOverlay()
    {
        var fade = new DoubleAnimation(1, 0, TimeSpan.FromMilliseconds(260)) { EasingFunction = new CubicEase { EasingMode = EasingMode.EaseOut } };
        fade.Completed += (_, _) => StartupOverlay.Visibility = Visibility.Collapsed;
        StartupOverlay.BeginAnimation(OpacityProperty, fade);
    }


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

    private void LoadState()
    {
        try
        {
            if (File.Exists(_statePath))
                _state = JsonSerializer.Deserialize<AppState>(File.ReadAllText(_statePath), _json) ?? new AppState();
        }
        catch
        {
            _state = new AppState();
        }

        _state.Profiles ??= new List<Profile>();
        _state.TrustedDevices ??= new List<TrustedClient>();
        _state.IconLibrary ??= new List<IconAsset>();
        if (string.IsNullOrWhiteSpace(_state.ServerId))
            _state.ServerId = Guid.NewGuid().ToString("N");
        foreach (var device in _state.TrustedDevices)
            device.IsOnline = false;

        if (_state.Profiles.Count == 0)
        {
            _state.Profiles.Add(DefaultProfile("Revit", "R"));
            _state.Profiles.Add(DefaultProfile("NanoCAD", "N"));
            _state.Profiles.Add(DefaultProfile("Рабочий стол", "▣"));
            _state.ActiveProfileId = _state.Profiles[0].Id;
        }

        foreach (var p in _state.Profiles)
        {
            if (p.Pages.Count == 0)
                p.Pages.Add(DefaultPage("Страница 1"));
            if (string.IsNullOrWhiteSpace(p.ActivePageId))
                p.ActivePageId = p.Pages[0].Id;
            foreach (var pg in p.Pages)
                EnsureCapacity(pg);
            _profiles.Add(p);
        }

        SaveState();
    }

    private void SaveState()
    {
        _state.Profiles = _profiles.ToList();
        if (_profile is not null) _state.ActiveProfileId = _profile.Id;
        try { File.WriteAllText(_statePath, JsonSerializer.Serialize(_state, _json)); } catch { }
    }

    private void RefreshTrustedDevices()
    {
        if (!Dispatcher.CheckAccess())
        {
            Dispatcher.Invoke(RefreshTrustedDevices);
            return;
        }
        if (TrustedDevicesList is null) return;
        TrustedDevicesList.ItemsSource = null;
        TrustedDevicesList.ItemsSource = _state.TrustedDevices
            .OrderByDescending(x => x.IsOnline)
            .ThenByDescending(x => x.LastSeenUtc)
            .ToList();
    }

    private TrustedClient? TrustedById(string clientId)
        => _state.TrustedDevices.FirstOrDefault(x => string.Equals(x.Id, clientId, StringComparison.Ordinal));

    private static string NewDeviceSecret()
        => Convert.ToBase64String(RandomNumberGenerator.GetBytes(32)).TrimEnd('=').Replace('+', '-').Replace('/', '_');

    private bool TryAuthenticateTrusted(string clientId, string suppliedSecret)
    {
        var device = TrustedById(clientId);
        if (device is null || string.IsNullOrWhiteSpace(device.Secret) || string.IsNullOrWhiteSpace(suppliedSecret)) return false;
        var a = Encoding.UTF8.GetBytes(device.Secret);
        var b = Encoding.UTF8.GetBytes(suppliedSecret);
        return a.Length == b.Length && CryptographicOperations.FixedTimeEquals(a, b);
    }

    private TrustedClient PairTrustedClient(string clientId, string transport)
    {
        var device = TrustedById(clientId);
        if (device is null)
        {
            device = new TrustedClient { Id = clientId };
            _state.TrustedDevices.Add(device);
        }
        device.Secret = NewDeviceSecret();
        device.Transport = transport;
        device.LastSeenUtc = DateTime.UtcNow;
        SaveState();
        RefreshTrustedDevices();
        Dispatcher.BeginInvoke(() => { if (_qrWindow is not null) { _qrWindow.Close(); _qrWindow = null; } });
        return device;
    }

    private void MarkTrustedClient(string clientId, bool online, string? transport = null)
    {
        var device = TrustedById(clientId);
        if (device is null) return;
        device.IsOnline = online;
        if (!string.IsNullOrWhiteSpace(transport)) device.Transport = transport!;
        if (online) device.LastSeenUtc = DateTime.UtcNow;
        SaveState();
        RefreshTrustedDevices();
    }

    private void UpdateTrustedMetadata(string clientId, string formFactor, string? name, string transport)
    {
        var device = TrustedById(clientId);
        if (device is null) return;
        device.FormFactor = string.Equals(formFactor, "tablet", StringComparison.OrdinalIgnoreCase) ? "tablet" : "phone";
        device.Name = string.IsNullOrWhiteSpace(name)
            ? (device.FormFactor == "tablet" ? "Планшет" : "Телефон") + " " + (clientId.Length > 4 ? clientId[^4..] : clientId)
            : name.Trim();
        device.Transport = transport;
        device.LastSeenUtc = DateTime.UtcNow;
        SaveState();
        RefreshTrustedDevices();
    }

    private void ForgetTrustedDevice_Click(object sender, RoutedEventArgs e)
    {
        if (TrustedDevicesList.SelectedItem is not TrustedClient device) return;
        if (device.IsOnline)
        {
            MessageBox.Show(this, "Сначала отключите устройство, затем его можно забыть.", "NEXO");
            return;
        }
        _state.TrustedDevices.RemoveAll(x => x.Id == device.Id);
        SaveState();
        RefreshTrustedDevices();
    }


    private async void TrustedDeviceMenu_Click(object sender, RoutedEventArgs e)
    {
        if (sender is not Button { Tag: TrustedClient device } button) return;
        var menu = new ContextMenu();
        var forget = new MenuItem { Header = "Забыть устройство (отключиться)" };
        forget.Click += async (_, _) => await ForgetTrustedClientAsync(device);
        menu.Items.Add(forget);
        button.ContextMenu = menu; menu.PlacementTarget = button; menu.IsOpen = true; e.Handled = true;
    }

    private async Task ForgetTrustedClientAsync(TrustedClient device)
    {
        List<WebSocket> close = new();
        lock (_clients)
            foreach (var pair in _clientIds.Where(x => x.Value == device.Id).ToList()) close.Add(pair.Key);
        foreach (var socket in close)
            try { await socket.CloseAsync(WebSocketCloseStatus.NormalClosure, "Device forgotten", CancellationToken.None); } catch { }
        if (_bleClientId == device.Id) { _bleAuthenticated = false; _bleClientId = ""; }
        _state.TrustedDevices.RemoveAll(x => x.Id == device.Id);
        SaveState(); RefreshTrustedDevices(); UpdateConnectionStatus();
    }

    private void ProfileSettingsButton_Click(object sender, RoutedEventArgs e) => ProfileSettingsPopup.IsOpen = !ProfileSettingsPopup.IsOpen;

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
    }

    private static Profile DefaultProfile(string name, string icon)
    {
        var profile = new Profile { Name = name, Icon = icon };
        var page = DefaultPage("Страница 1");
        profile.Pages.Add(page);
        profile.ActivePageId = page.Id;
        return profile;
    }

    private static DeckPage DefaultPage(string name)
    {
        var page = new DeckPage { Name = name, Rows = 3, Columns = 4 };
        var defaults = new[]
        {
            new Tile { Title = "Сохранить", ActionType = "hotkey", Hotkey = "CTRL+S" },
            new Tile { Title = "Скриншот", ActionType = "hotkey", Hotkey = "WIN+SHIFT+S" },
            new Tile { Title = "Переключить окна", ActionType = "hotkey", Hotkey = "ALT+TAB" },
            new Tile { Title = "Браузер", ActionType = "url", ActionValue = "https://www.google.com" },
            new Tile { Title = "Назад", ActionType = "hotkey", Hotkey = "ESC" },
            new Tile { Title = "Воспроизведение", ActionType = "media", ActionValue = "MEDIA_PLAY" },
            new Tile { Title = "Выключить звук", ActionType = "media", ActionValue = "VOLUME_MUTE" },
            new Tile { Title = "Рабочий стол", ActionType = "hotkey", Hotkey = "WIN+D" },
            new Tile { Title = "Почта" }, new Tile { Title = "Калькулятор" }, new Tile { Title = "Открыть папку" }, new Tile()
        };
        foreach (var tile in defaults) page.Tiles.Add(tile);
        return page;
    }

    private void ConfigureActionView()
    {
        var view = CollectionViewSource.GetDefaultView(_actions);
        view.GroupDescriptions.Clear();
        view.GroupDescriptions.Add(new PropertyGroupDescription(nameof(ActionItem.Category)));
        view.Filter = FilterAction;
        ActionLibraryList.ItemsSource = view;
    }

    private bool FilterAction(object item)
    {
        if (item is not ActionItem action) return false;
        var q = ActionSearchBox?.Text?.Trim() ?? "";
        if (q.Length == 0) return true;
        return action.Title.Contains(q, StringComparison.OrdinalIgnoreCase)
            || action.Description.Contains(q, StringComparison.OrdinalIgnoreCase)
            || action.Category.Contains(q, StringComparison.OrdinalIgnoreCase);
    }

    private void ActionSearchBox_TextChanged(object sender, TextChangedEventArgs e)
        => CollectionViewSource.GetDefaultView(_actions)?.Refresh();

    private static IEnumerable<ActionItem> BuildActionLibrary()
    {
        yield return new("Система", "⌨", "Горячая клавиша", "Нажмите сочетание клавиш в инспекторе", "hotkey", "");
        yield return new("Система", "T", "Текст", "Вставить заданный текст", "text", "");
        yield return new("Система", "↗", "Открыть", "Программа, файл или папка", "open", "");
        yield return new("Система", "◎", "Веб-сайт", "Открыть URL в браузере", "url", "https://");
        yield return new("NEXO", "□", "Папка", "Открыть вложенную страницу", "folder", "");
        yield return new("NEXO", "≡", "Multi Action", "Несколько действий по очереди", "multi", "");
        yield return new("NEXO", "⇄", "Переключить профиль", "Активировать другой профиль", "profile", "");
        yield return new("Мультимедиа", "▶", "Play / Pause", "Управление воспроизведением", "media", "MEDIA_PLAY");
        yield return new("Мультимедиа", "+", "Громкость +", "Увеличить громкость", "media", "VOLUME_UP");
        yield return new("Мультимедиа", "−", "Громкость −", "Уменьшить громкость", "media", "VOLUME_DOWN");
        yield return new("Мультимедиа", "◖", "Mute", "Включить/выключить звук", "media", "VOLUME_MUTE");
        yield return new("Популярное", "▣", "Сохранить", "CTRL + S", "hotkey", "CTRL+S");
        yield return new("Популярное", "⌗", "Скриншот", "WIN + SHIFT + S", "hotkey", "WIN+SHIFT+S");
        yield return new("Популярное", "⇥", "Переключить окна", "ALT + TAB", "hotkey", "ALT+TAB");
        yield return new("Популярное", "▤", "Копировать", "CTRL + C", "hotkey", "CTRL+C");
        yield return new("Популярное", "▥", "Вставить", "CTRL + V", "hotkey", "CTRL+V");
    }

    private void RefreshProfiles()
    {
        _updating = true;
        ProfileBox.ItemsSource = null;
        ProfileBox.ItemsSource = _profiles;
        _profile = _profiles.FirstOrDefault(x => x.Id == _state.ActiveProfileId) ?? _profiles.First();
        ProfileBox.SelectedItem = _profile;
        _updating = false;
        LoadProfile();
    }

    private void LoadProfile()
    {
        if (_profile is null) return;
        if (_profile.Pages.Count == 0) _profile.Pages.Add(DefaultPage("Страница 1"));
        _page = _profile.Pages.FirstOrDefault(x => x.Id == _profile.ActivePageId) ?? _profile.Pages[0];
        _profile.ActivePageId = _page.Id;

        _updating = true;
        ProfileTitle.Text = _profile.Name;
        ProfileName.Text = _profile.Name;
        ProfileDescription.Text = _profile.Description;
        ColumnsBox.Text = _page.Columns.ToString();
        RowsBox.Text = _page.Rows.ToString();
        _userZoom = Math.Clamp(_page.Zoom, ZoomSlider.Minimum, ZoomSlider.Maximum);
        ZoomSlider.Value = _userZoom;
        _updating = false;

        _selected = null;
        _selectedButton = null;
        RefreshInspector();
        RebuildPages();
        RebuildGrid();
    }

    private void RebuildPages()
    {
        if (_profile is null || _page is null) return;
        PageButtons.Children.Clear();
        var index = _profile.Pages.IndexOf(_page) + 1;
        PageInfo.Text = $"Страница {index} из {_profile.Pages.Count}";

        for (var i = 0; i < _profile.Pages.Count; i++)
        {
            var page = _profile.Pages[i];
            var selected = page.Id == _page.Id;
            var button = new Button
            {
                Content = (i + 1).ToString(),
                Width = 34,
                Height = 32,
                Margin = new Thickness(3, 0, 3, 0),
                Tag = page,
                ToolTip = page.Name,
                Background = new SolidColorBrush(selected ? Color.FromRgb(53, 58, 62) : Color.FromRgb(36, 39, 42)),
                Foreground = Brushes.White,
                BorderBrush = selected ? (Brush)FindResource("Blue") : (Brush)FindResource("Border")
            };
            button.Click += (_, _) =>
            {
                _profile.ActivePageId = page.Id;
                SaveState();
                LoadProfile();
                _ = BroadcastSnapshotAsync();
            };

            var menu = new ContextMenu();
            var rename = new MenuItem { Header = "Переименовать страницу" };
            rename.Click += (_, _) => RenamePage(page);
            menu.Items.Add(rename);
            var delete = new MenuItem { Header = "Удалить страницу", IsEnabled = _profile.Pages.Count > 1 };
            delete.Click += (_, _) => DeletePage(page);
            menu.Items.Add(delete);
            button.ContextMenu = menu;
            PageButtons.Children.Add(button);
        }

        var plus = new Button
        {
            Content = "+",
            Width = 34,
            Height = 32,
            Margin = new Thickness(7, 0, 3, 0),
            ToolTip = "Добавить страницу",
            Foreground = Brushes.White,
            Background = (Brush)FindResource("Panel2")
        };
        plus.Click += AddPage_Click;
        PageButtons.Children.Add(plus);
    }

    private void RenamePage(DeckPage page)
    {
        var name = Prompt("Переименовать страницу", page.Name);
        if (string.IsNullOrWhiteSpace(name)) return;
        page.Name = name;
        SaveState();
        LoadProfile();
        _ = BroadcastSnapshotAsync();
    }

    private void DeletePage(DeckPage page)
    {
        if (_profile is null || _profile.Pages.Count <= 1) return;
        if (MessageBox.Show(this, $"Удалить страницу «{page.Name}»?", "NEXO", MessageBoxButton.YesNo, MessageBoxImage.Question) != MessageBoxResult.Yes) return;
        var index = _profile.Pages.IndexOf(page);
        _profile.Pages.Remove(page);
        var next = _profile.Pages[Math.Clamp(index - 1, 0, _profile.Pages.Count - 1)];
        _profile.ActivePageId = next.Id;
        SaveState();
        LoadProfile();
        _ = BroadcastSnapshotAsync();
    }

    private void RebuildGrid()
    {
        if (_page is null) return;
        EnsureCapacity(_page);
        DeckGrid.Children.Clear();
        DeckGrid.RowDefinitions.Clear();
        DeckGrid.ColumnDefinitions.Clear();
        for (var r = 0; r < _page.Rows; r++) DeckGrid.RowDefinitions.Add(new RowDefinition { Height = new GridLength(116) });
        for (var c = 0; c < _page.Columns; c++) DeckGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(142) });

        GridInfo.Text = $"{_page.Columns} × {_page.Rows}  •  {_page.Columns * _page.Rows} ячеек";
        var used = new bool[_page.Rows, _page.Columns];
        var number = 1;
        foreach (var tile in _page.Tiles)
        {
            var pos = FindSpace(used, tile, _page.Rows, _page.Columns);
            if (pos is null) continue;
            var (row, column) = pos.Value;
            var rowSpan = Math.Min(Math.Max(1, tile.RowSpan), _page.Rows - row);
            var columnSpan = Math.Min(Math.Max(1, tile.ColumnSpan), _page.Columns - column);
            Mark(used, row, column, rowSpan, columnSpan);
            var button = TileButton(tile, number++);
            Grid.SetRow(button, row); Grid.SetColumn(button, column); Grid.SetRowSpan(button, rowSpan); Grid.SetColumnSpan(button, columnSpan);
            DeckGrid.Children.Add(button);
        }
        Dispatcher.BeginInvoke(UpdateZoom, DispatcherPriority.Background);
    }

    private Button TileButton(Tile tile, int number)
    {
        var blank = IsBlank(tile);
        var button = new Button
        {
            Tag = tile, Margin = new Thickness(5), Padding = new Thickness(10), MinWidth = 125, MinHeight = 100,
            Background = new SolidColorBrush(blank ? Color.FromRgb(32, 35, 38) : Color.FromRgb(39, 43, 46)),
            BorderBrush = new SolidColorBrush(Color.FromRgb(20, 22, 24)), BorderThickness = new Thickness(2),
            AllowDrop = true
        };

        var root = new Grid();
        var stack = new StackPanel { HorizontalAlignment = HorizontalAlignment.Center, VerticalAlignment = VerticalAlignment.Center };
        stack.Children.Add(CreateTileIcon(tile, blank));
        if (tile.ShowLabel)
            stack.Children.Add(new TextBlock { Text = tile.Title, TextAlignment = TextAlignment.Center, TextWrapping = TextWrapping.Wrap, FontWeight = FontWeights.SemiBold, Foreground = blank ? Brushes.Gray : Brushes.White, MaxWidth = 180 });
        var actionCaption = ActionCaption(tile);
        if (!string.IsNullOrWhiteSpace(actionCaption))
            stack.Children.Add(new TextBlock { Text = actionCaption, FontSize = 9, Foreground = (Brush)FindResource("Muted"), HorizontalAlignment = HorizontalAlignment.Center, Margin = new Thickness(0, 4, 0, 0), MaxWidth = 180, TextTrimming = TextTrimming.CharacterEllipsis });
        root.Children.Add(stack);
        if (ShowNumbers.IsChecked == true)
            root.Children.Add(new TextBlock { Text = number.ToString(), FontSize = 10, Foreground = Brushes.Gray, HorizontalAlignment = HorizontalAlignment.Left, VerticalAlignment = VerticalAlignment.Top });
        button.Content = root;

        button.PreviewMouseLeftButtonDown += (_, e) => _tileDragStart = e.GetPosition(this);
        button.PreviewMouseMove += (_, e) => Tile_PreviewMouseMove(button, tile, e);
        button.Click += (_, _) => SelectTile(button, tile);
        button.MouseDoubleClick += (_, _) => FocusTile(button);
        button.DragOver += Tile_DragOver;
        button.Drop += Tile_Drop;
        button.ContextMenu = TileMenu(tile);
        return button;
    }

    private static string ActionCaption(Tile tile) => tile.ActionType switch
    {
        "hotkey" => tile.Hotkey,
        "text" => "Текст",
        "open" => Path.GetFileName(tile.ActionValue),
        "url" => tile.ActionValue,
        "folder" => "Папка",
        "multi" => $"{tile.Steps.Count} действий",
        "profile" => "Профиль",
        "media" => tile.ActionValue,
        _ => ""
    };

    private void SelectTile(Button button, Tile tile)
    {
        if (_selectedButton is not null) _selectedButton.BorderBrush = new SolidColorBrush(Color.FromRgb(20, 22, 24));
        _selectedButton = button;
        _selected = tile;
        button.BorderBrush = (Brush)FindResource("Blue");
        RefreshInspector();
    }

    private void RefreshInspector()
    {
        _updating = true;
        var enabled = _selected is not null;
        InspectorTitleBox.IsEnabled = enabled;
        InspectorTypeBox.IsEnabled = enabled;
        InspectorValueBox.IsEnabled = enabled;
        InspectorHotkeyBox.IsEnabled = enabled;
        RecordHotkeyButton.IsEnabled = enabled;
        InspectorShowLabel.IsEnabled = enabled;

        if (_selected is null)
        {
            InspectorHint.Text = "Выберите плитку или перетащите действие из каталога на рабочее поле.";
            InspectorTitleBox.Text = "";
            InspectorTypeBox.Text = "";
            InspectorValueBox.Text = "";
            InspectorHotkeyBox.Text = "";
            InspectorValueLabel.Text = "Параметр";
            InspectorShowLabel.IsChecked = true;
        }
        else
        {
            InspectorHint.Text = "Настройка выполняется на ПК. Изменения сразу синхронизируются с подключенным телефоном.";
            InspectorTitleBox.Text = _selected.Title;
            InspectorTypeBox.Text = ActionTypeName(_selected.ActionType);
            InspectorValueBox.Text = _selected.ActionValue;
            InspectorHotkeyBox.Text = _selected.Hotkey;
            InspectorShowLabel.IsChecked = _selected.ShowLabel;
            InspectorValueLabel.Text = _selected.ActionType switch
            {
                "text" => "Текст",
                "open" => "Путь к программе / файлу / папке",
                "url" => "URL",
                "folder" => "ID / имя страницы",
                "profile" => "ID / имя профиля",
                "media" => "Медиа-команда",
                _ => "Параметр"
            };
        }
        _updating = false;
        RefreshIconInspector();
    }

    private static string ActionTypeName(string type) => type switch
    {
        "hotkey" => "Горячая клавиша",
        "text" => "Текст",
        "open" => "Открыть",
        "url" => "Веб-сайт",
        "folder" => "Папка",
        "multi" => "Multi Action",
        "profile" => "Переключить профиль",
        "media" => "Мультимедиа",
        _ => "Не назначено"
    };

    private void ActionLibrary_PreviewMouseLeftButtonDown(object sender, MouseButtonEventArgs e)
        => _actionDragStart = e.GetPosition(this);

    private void ActionLibrary_PreviewMouseMove(object sender, MouseEventArgs e)
    {
        if (e.LeftButton != MouseButtonState.Pressed || ActionLibraryList.SelectedItem is not ActionItem action) return;
        var current = e.GetPosition(this);
        if (Math.Abs(current.X - _actionDragStart.X) < SystemParameters.MinimumHorizontalDragDistance && Math.Abs(current.Y - _actionDragStart.Y) < SystemParameters.MinimumVerticalDragDistance) return;
        DragDrop.DoDragDrop(ActionLibraryList, new DataObject("MacroPadAction", action), DragDropEffects.Copy);
    }

    private void ActionLibrary_DoubleClick(object sender, MouseButtonEventArgs e)
    {
        if (_selected is null || ActionLibraryList.SelectedItem is not ActionItem action) return;
        AssignAction(_selected, action);
        SaveAndBroadcast();
        RefreshInspector();
    }

    private void Tile_PreviewMouseMove(Button button, Tile tile, MouseEventArgs e)
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

    private void AssignAction(Tile tile, ActionItem action)
    {
        tile.Title = action.Title;
        tile.ActionType = action.Type;
        tile.ActionValue = action.Value;
        tile.Hotkey = action.Type == "hotkey" ? action.Value : "";
        if (action.Type != "multi") tile.Steps.Clear();

        if (action.Type == "folder" && _profile is not null)
        {
            var newPage = new DeckPage { Name = $"Папка {_profile.Pages.Count + 1}", Rows = 3, Columns = 4 };
            EnsureCapacity(newPage);
            _profile.Pages.Add(newPage);
            tile.ActionValue = newPage.Id;
            tile.Title = newPage.Name;
        }
        else if (action.Type == "profile" && _profiles.Count > 0)
        {
            var target = _profiles.FirstOrDefault(p => p.Id != _profile?.Id) ?? _profiles[0];
            tile.ActionValue = target.Id;
            tile.Title = target.Name;
        }
    }

    private ContextMenu TileMenu(Tile tile)
    {
        var menu = new ContextMenu();
        var properties = new MenuItem { Header = "Свойства действия" };
        properties.Click += (_, _) =>
        {
            var button = DeckGrid.Children.OfType<Button>().FirstOrDefault(b => ReferenceEquals(b.Tag, tile));
            if (button is not null) SelectTile(button, tile);
            InspectorTitleBox.Focus();
        };
        menu.Items.Add(properties);

        var test = new MenuItem { Header = "Выполнить тест" };
        test.Click += async (_, _) => await ExecuteTileAsync(tile);
        menu.Items.Add(test);

        var multi = new MenuItem { Header = "Создать Multi Action" };
        multi.Click += (_, _) =>
        {
            tile.ActionType = "multi"; tile.Title = "Multi Action"; tile.Hotkey = ""; tile.ActionValue = "";
            if (tile.Steps.Count == 0) tile.Steps.Add(new ActionStep { Type = "hotkey", Value = "CTRL+S", DelayMs = 100 });
            SaveAndBroadcast(); RefreshInspector();
        };
        menu.Items.Add(multi);

        var folder = new MenuItem { Header = "Создать папку" };
        folder.Click += (_, _) => AssignAction(tile, new ActionItem("NEXO", "□", "Папка", "", "folder", ""));
        folder.Click += (_, _) => { SaveAndBroadcast(); RefreshInspector(); };
        menu.Items.Add(folder);
        menu.Items.Add(new Separator());

        var size = new MenuItem { Header = "Размер ячейки" };
        foreach (var option in new[] { ("1 × 1", 1, 1), ("2 × 1", 2, 1), ("1 × 2", 1, 2), ("2 × 2", 2, 2), ("3 × 1", 3, 1), ("1 × 3", 1, 3) })
        {
            var columns = option.Item2; var rows = option.Item3;
            var item = new MenuItem { Header = option.Item1, IsCheckable = true, IsChecked = tile.ColumnSpan == columns && tile.RowSpan == rows };
            item.Click += (_, _) => ResizeTile(tile, columns, rows);
            size.Items.Add(item);
        }
        menu.Items.Add(size);
        menu.Items.Add(new Separator());
        var clear = new MenuItem { Header = "Очистить ячейку" };
        clear.Click += (_, _) => ClearTile(tile);
        menu.Items.Add(clear);
        return menu;
    }

    private void RecordHotkey_Click(object sender, RoutedEventArgs e)
    {
        if (_selected is null) return;
        _capturingHotkey = true;
        RecordHotkeyButton.Content = "Нажмите…";
        RecordHotkeyButton.Focus();
        Keyboard.Focus(RecordHotkeyButton);
    }

    private void RecordHotkey_PreviewKeyDown(object sender, KeyEventArgs e)
    {
        if (!_capturingHotkey || _selected is null) return;
        var key = e.Key == Key.System ? e.SystemKey : e.Key;
        if (key is Key.LeftCtrl or Key.RightCtrl or Key.LeftAlt or Key.RightAlt or Key.LeftShift or Key.RightShift or Key.LWin or Key.RWin)
        {
            e.Handled = true;
            return;
        }

        var tokens = new List<string>();
        if (Keyboard.Modifiers.HasFlag(ModifierKeys.Control)) tokens.Add("CTRL");
        if (Keyboard.Modifiers.HasFlag(ModifierKeys.Alt)) tokens.Add("ALT");
        if (Keyboard.Modifiers.HasFlag(ModifierKeys.Shift)) tokens.Add("SHIFT");
        if (Keyboard.Modifiers.HasFlag(ModifierKeys.Windows)) tokens.Add("WIN");
        tokens.Add(KeyToToken(key));
        var hotkey = string.Join('+', tokens.Where(x => !string.IsNullOrWhiteSpace(x)));

        _selected.ActionType = "hotkey";
        _selected.Hotkey = hotkey;
        _selected.ActionValue = "";
        InspectorHotkeyBox.Text = hotkey;
        InspectorTypeBox.Text = ActionTypeName("hotkey");
        _capturingHotkey = false;
        RecordHotkeyButton.Content = "Записать";
        e.Handled = true;
        SaveAndBroadcast();
    }

    private static string KeyToToken(Key key)
    {
        if (key is >= Key.D0 and <= Key.D9) return ((int)key - (int)Key.D0).ToString();
        if (key is >= Key.NumPad0 and <= Key.NumPad9) return $"NUM{(int)key - (int)Key.NumPad0}";
        return key switch
        {
            Key.Return => "ENTER", Key.Escape => "ESC", Key.Back => "BACKSPACE", Key.Delete => "DELETE", Key.Insert => "INSERT",
            Key.Space => "SPACE", Key.Tab => "TAB", Key.Left => "LEFT", Key.Right => "RIGHT", Key.Up => "UP", Key.Down => "DOWN",
            Key.Home => "HOME", Key.End => "END", Key.PageUp => "PAGEUP", Key.PageDown => "PAGEDOWN",
            _ => key.ToString().ToUpperInvariant()
        };
    }

    private void InspectorChanged(object sender, TextChangedEventArgs e)
    {
        if (_updating || _selected is null) return;
    }

    private void ApplyInspector_Click(object sender, RoutedEventArgs e)
    {
        if (_selected is null) return;
        _selected.Title = string.IsNullOrWhiteSpace(InspectorTitleBox.Text) ? "Кнопка" : InspectorTitleBox.Text.Trim();
        _selected.ActionValue = InspectorValueBox.Text.Trim();
        _selected.ShowLabel = InspectorShowLabel.IsChecked != false;
        if (_selected.ActionType == "hotkey") _selected.Hotkey = InspectorHotkeyBox.Text.Trim().ToUpperInvariant();
        SaveAndBroadcast();
        RefreshInspector();
    }

    private void ClearTile_Click(object sender, RoutedEventArgs e)
    {
        if (_selected is null) return;
        ClearTile(_selected);
    }

    private void ClearTile(Tile tile)
    {
        tile.Title = "Добавить"; tile.ActionType = ""; tile.ActionValue = ""; tile.Hotkey = ""; tile.IconKind = "auto"; tile.IconValue = ""; tile.ShowLabel = true; tile.ColumnSpan = tile.RowSpan = 1; tile.Steps.Clear();
        EnsureCapacity(_page!); SaveAndBroadcast(); RefreshInspector();
    }

    private void ResizeTile(Tile tile, int columns, int rows)
    {
        if (_page is null) return;
        columns = Math.Clamp(columns, 1, _page.Columns); rows = Math.Clamp(rows, 1, _page.Rows);
        var extra = columns * rows - Math.Max(1, tile.ColumnSpan) * Math.Max(1, tile.RowSpan);
        if (extra > 0)
        {
            var blanks = _page.Tiles.Where(x => !ReferenceEquals(x, tile) && IsBlank(x)).Take(extra).ToList();
            if (blanks.Count < extra) { MessageBox.Show(this, "Недостаточно свободных пустых ячеек.", "NEXO"); return; }
            foreach (var blank in blanks) _page.Tiles.Remove(blank);
        }
        tile.ColumnSpan = columns; tile.RowSpan = rows; EnsureCapacity(_page); SaveAndBroadcast();
    }

    private string HoldKey(string clientId, string tileId) => $"{clientId}:{tileId}";

    private void StartRemoteHold(string clientId, Tile tile)
    {
        var hotkey = tile.ActionType == "media" ? tile.ActionValue : tile.Hotkey;
        if (tile.ActionType == "hotkey" || tile.ActionType == "media" || (!string.IsNullOrWhiteSpace(hotkey) && string.IsNullOrWhiteSpace(tile.ActionType)))
        {
            var keys = HotkeyVirtualKeys(hotkey);
            if (keys.Count == 0) return;
            var key = HoldKey(clientId, tile.Id);
            if (_heldRemoteKeys.ContainsKey(key)) return;
            SendInputs(keys.Select(vk => KeyInput(vk, false)).ToArray());
            _heldRemoteKeys[key] = keys;
            DeviceStatus.Text = $"Удерживается: {tile.Title}";
            return;
        }

        _ = ExecuteTileAsync(tile);
    }

    private void EndRemoteHold(string clientId, string tileId)
    {
        var key = HoldKey(clientId, tileId);
        if (!_heldRemoteKeys.Remove(key, out var keys)) return;
        SendInputs(keys.AsEnumerable().Reverse().Select(vk => KeyInput(vk, true)).ToArray());
        DeviceStatus.Text = "Удержание завершено";
    }

    private void ReleaseRemoteHolds(string clientId)
    {
        foreach (var key in _heldRemoteKeys.Keys.Where(k => k.StartsWith(clientId + ":", StringComparison.Ordinal)).ToList())
        {
            if (!_heldRemoteKeys.Remove(key, out var keys)) continue;
            try { SendInputs(keys.AsEnumerable().Reverse().Select(vk => KeyInput(vk, true)).ToArray()); } catch { }
        }
    }

    private static List<ushort> HotkeyVirtualKeys(string hotkey)
    {
        if (string.IsNullOrWhiteSpace(hotkey)) return new List<ushort>();
        return hotkey.Split('+', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
            .Select(TokenToVk).Where(vk => vk != 0).ToList();
    }

    private async Task ExecuteTileAsync(Tile tile)
    {
        try
        {
            switch (tile.ActionType)
            {
                case "hotkey": ExecuteHotkey(tile.Hotkey); break;
                case "text": SendText(tile.ActionValue); break;
                case "open":
                    if (!string.IsNullOrWhiteSpace(tile.ActionValue)) Process.Start(new ProcessStartInfo(tile.ActionValue) { UseShellExecute = true });
                    break;
                case "url":
                    if (!string.IsNullOrWhiteSpace(tile.ActionValue)) Process.Start(new ProcessStartInfo(tile.ActionValue) { UseShellExecute = true });
                    break;
                case "media": ExecuteHotkey(tile.ActionValue); break;
                case "folder":
                    if (_profile is not null)
                    {
                        var target = _profile.Pages.FirstOrDefault(p => p.Id == tile.ActionValue || string.Equals(p.Name, tile.ActionValue, StringComparison.OrdinalIgnoreCase));
                        if (target is not null) { _profile.ActivePageId = target.Id; SaveState(); LoadProfile(); await BroadcastSnapshotAsync(); }
                    }
                    break;
                case "profile":
                    var profile = _profiles.FirstOrDefault(p => p.Id == tile.ActionValue || string.Equals(p.Name, tile.ActionValue, StringComparison.OrdinalIgnoreCase));
                    if (profile is not null) { _state.ActiveProfileId = profile.Id; SaveState(); RefreshProfiles(); await BroadcastSnapshotAsync(); }
                    break;
                case "multi":
                    foreach (var step in tile.Steps)
                    {
                        await ExecuteStepAsync(step);
                        if (step.DelayMs > 0) await Task.Delay(Math.Clamp(step.DelayMs, 0, 60000));
                    }
                    break;
                default:
                    if (!string.IsNullOrWhiteSpace(tile.Hotkey)) ExecuteHotkey(tile.Hotkey);
                    break;
            }
            Dispatcher.Invoke(() => DeviceStatus.Text = $"Выполнено: {tile.Title}");
        }
        catch (Exception ex)
        {
            Dispatcher.Invoke(() => DeviceStatus.Text = $"Ошибка действия «{tile.Title}»: {ex.Message}");
        }
    }

    private Task ExecuteStepAsync(ActionStep step)
    {
        switch (step.Type)
        {
            case "hotkey": ExecuteHotkey(step.Value); break;
            case "text": SendText(step.Value); break;
            case "open": if (!string.IsNullOrWhiteSpace(step.Value)) Process.Start(new ProcessStartInfo(step.Value) { UseShellExecute = true }); break;
            case "media": ExecuteHotkey(step.Value); break;
        }
        return Task.CompletedTask;
    }

    private void ProfileBox_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (_updating || ProfileBox.SelectedItem is not Profile selected) return;
        _profile = selected; _state.ActiveProfileId = selected.Id; SaveState(); LoadProfile(); _ = BroadcastSnapshotAsync();
    }


    private void AddProfile_Click(object sender, RoutedEventArgs e)
    {
        var name = Prompt("Новый профиль", $"Профиль {_profiles.Count + 1}");
        if (name is null) return;
        var profile = DefaultProfile(name, name[..1].ToUpperInvariant());
        _profiles.Add(profile); _state.ActiveProfileId = profile.Id; SaveState(); RefreshProfiles();
    }

    private void DeleteProfile_Click(object sender, RoutedEventArgs e)
    {
        if (_profile is null || _profiles.Count <= 1) return;
        if (MessageBox.Show(this, $"Удалить профиль «{_profile.Name}»?", "NEXO", MessageBoxButton.YesNo) != MessageBoxResult.Yes) return;
        _profiles.Remove(_profile); _state.ActiveProfileId = _profiles[0].Id; SaveState(); RefreshProfiles(); _ = BroadcastSnapshotAsync();
    }

    private void ProfileMenu_Click(object sender, RoutedEventArgs e)
    {
        if (sender is not Button { Tag: Profile profile } button) return;
        ProfileBox.SelectedItem = profile;
        var menu = new ContextMenu();
        var rename = new MenuItem { Header = "Переименовать" };
        rename.Click += (_, _) => { var name = Prompt("Переименовать профиль", profile.Name); if (name is null) return; profile.Name = name; SaveState(); RefreshProfiles(); };
        var copy = new MenuItem { Header = "Создать копию" };
        copy.Click += (_, _) =>
        {
            var clone = JsonSerializer.Deserialize<Profile>(JsonSerializer.Serialize(profile, _json), _json)!;
            clone.Id = Guid.NewGuid().ToString("N"); clone.Name += " copy";
            foreach (var pg in clone.Pages) { pg.Id = Guid.NewGuid().ToString("N"); foreach (var tile in pg.Tiles) tile.Id = Guid.NewGuid().ToString("N"); }
            clone.ActivePageId = clone.Pages[0].Id; _profiles.Add(clone); _state.ActiveProfileId = clone.Id; SaveState(); RefreshProfiles();
        };
        var delete = new MenuItem { Header = "Удалить" }; delete.Click += DeleteProfile_Click;
        menu.Items.Add(rename); menu.Items.Add(copy); menu.Items.Add(new Separator()); menu.Items.Add(delete);
        button.ContextMenu = menu; menu.PlacementTarget = button; menu.IsOpen = true; e.Handled = true;
    }

    private void AddPage_Click(object sender, RoutedEventArgs e)
    {
        if (_profile is null) return;
        var name = Prompt("Новая страница", $"Страница {_profile.Pages.Count + 1}");
        if (name is null) return;
        var page = DefaultPage(name); _profile.Pages.Add(page); _profile.ActivePageId = page.Id; SaveState(); LoadProfile(); _ = BroadcastSnapshotAsync();
    }

    private void SaveProfile_Click(object sender, RoutedEventArgs e)
    {
        if (_profile is null || _page is null) return;
        if (!string.IsNullOrWhiteSpace(ProfileName.Text)) _profile.Name = ProfileName.Text.Trim();
        _profile.Description = ProfileDescription.Text.Trim();
        var columns = int.TryParse(ColumnsBox.Text, out var c) ? Math.Clamp(c, 1, 12) : _page.Columns;
        var rows = int.TryParse(RowsBox.Text, out var r) ? Math.Clamp(r, 1, 12) : _page.Rows;
        if (ConfiguredArea(_page) > columns * rows) { MessageBox.Show(this, "Новая сетка слишком мала для уже настроенных плиток.", "NEXO"); return; }
        _page.Columns = columns; _page.Rows = rows; EnsureCapacity(_page); SaveState(); RefreshProfiles(); _ = BroadcastSnapshotAsync();
    }

    private void UpdateZoom()
    {
        if (_page is null || !IsLoaded) return;
        DeckGrid.Measure(new Size(double.PositiveInfinity, double.PositiveInfinity));
        var desired = DeckGrid.DesiredSize;
        if (desired.Width <= 0 || desired.Height <= 0) return;
        var width = Math.Max(1, DeckViewport.ViewportWidth - 48); var height = Math.Max(1, DeckViewport.ViewportHeight - 48);
        _fitScale = Math.Clamp(Math.Min(width / desired.Width, height / desired.Height), .28, 1);
        DeckScaleHost.LayoutTransform = new ScaleTransform(_fitScale * _userZoom, _fitScale * _userZoom);
    }

    private void DeckViewport_SizeChanged(object sender, SizeChangedEventArgs e) => UpdateZoom();

    private void ZoomSlider_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
    {
        if (_updating || _page is null || !IsLoaded) return;
        _userZoom = ZoomSlider.Value; _page.Zoom = _userZoom; SaveState(); UpdateZoom();
    }

    private void DeckViewport_PreviewMouseWheel(object sender, MouseWheelEventArgs e)
    {
        if ((Keyboard.Modifiers & ModifierKeys.Control) == 0) return;
        e.Handled = true;
        var pointer = e.GetPosition(DeckViewport);
        var old = Math.Max(.01, _fitScale * _userZoom);
        var logicalX = (DeckViewport.HorizontalOffset + pointer.X) / old;
        var logicalY = (DeckViewport.VerticalOffset + pointer.Y) / old;
        _userZoom = Math.Clamp(_userZoom + (e.Delta > 0 ? .12 : -.12), ZoomSlider.Minimum, ZoomSlider.Maximum);
        _updating = true; ZoomSlider.Value = _userZoom; _updating = false;
        if (_page is not null) _page.Zoom = _userZoom; SaveState(); UpdateZoom();
        Dispatcher.BeginInvoke(() =>
        {
            var next = _fitScale * _userZoom;
            DeckViewport.ScrollToHorizontalOffset(Math.Max(0, logicalX * next - pointer.X));
            DeckViewport.ScrollToVerticalOffset(Math.Max(0, logicalY * next - pointer.Y));
        }, DispatcherPriority.Background);
    }

    private void FocusTile(FrameworkElement element)
    {
        _userZoom = Math.Max(_userZoom, 1.5); _updating = true; ZoomSlider.Value = _userZoom; _updating = false;
        if (_page is not null) _page.Zoom = _userZoom; UpdateZoom();
        Dispatcher.BeginInvoke(() =>
        {
            try
            {
                var bounds = element.TransformToAncestor(DeckGrid).TransformBounds(new Rect(new Point(), element.RenderSize));
                var scale = _fitScale * _userZoom;
                DeckViewport.ScrollToHorizontalOffset(Math.Max(0, (bounds.Left + bounds.Width / 2) * scale - DeckViewport.ViewportWidth / 2));
                DeckViewport.ScrollToVerticalOffset(Math.Max(0, (bounds.Top + bounds.Height / 2) * scale - DeckViewport.ViewportHeight / 2));
            }
            catch { }
        }, DispatcherPriority.Background);
    }

    private string SelectedTransport()
        => TransportBox.SelectedItem is ComboBoxItem item && item.Tag?.ToString() == "Bluetooth" ? "Bluetooth" : "Wifi";

    private void ApplyTransport()
    {
        _updating = true;
        var wanted = _state.Transport == "Bluetooth" ? "Bluetooth" : "Wifi";
        foreach (var item in TransportBox.Items.OfType<ComboBoxItem>())
            if (item.Tag?.ToString() == wanted) { TransportBox.SelectedItem = item; break; }
        _updating = false;
        SyncConnectionUi();
    }

    private async void TransportBox_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (_updating) return;
        await StopAllTransportsAsync();
        _state.Transport = SelectedTransport();
        SaveState();
        await StartSelectedTransportAsync();
        SettingsPopup.IsOpen = false;
    }

    private async Task StartSelectedTransportAsync()
    {
        if (SelectedTransport() == "Bluetooth")
            await StartBleAsync();
        else
            await StartWifiAsync();
        SyncConnectionUi();
    }

    private async Task StopAllTransportsAsync()
    {
        await StopWifiAsync();
        if (!string.IsNullOrWhiteSpace(_bleClientId))
            MarkTrustedClient(_bleClientId, false, "Bluetooth");
        _bleClientId = "";
        await _ble.StopAsync();
        _bleAuthenticated = false;
    }

    private void SyncConnectionUi()
    {
        var wifi = SelectedTransport() == "Wifi";
        ConnectionModeText.Text = wifi ? "Wi‑Fi" : "Bluetooth LE";
        DeviceQrButton.IsEnabled = HeaderQrButton.IsEnabled = true;
        DeviceServerButton.Content = HeaderServerButton.Content = "Перезапустить связь";
        if (wifi)
        {
            ConnectionDetails.Text = _server is null
                ? "Wi‑Fi: запуск…"
                : $"{LocalIp()}:{WebSocketPort} • устройства в сети видят этот ПК автоматически";
        }
        else
        {
            ConnectionDetails.Text = _ble.IsRunning
                ? $"BLE GATT активен • Service {_bleServiceShort}"
                : "Bluetooth LE: запуск…";
        }
    }

    private string _bleServiceShort => BleGattServer.ServiceUuid.ToString()[..8];

    private async void ServerButton_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            await StopAllTransportsAsync();
            await StartSelectedTransportAsync();
        }
        catch (Exception ex)
        {
            MessageBox.Show(this, $"Не удалось перезапустить связь.\n\n{ex.Message}", "NEXO");
        }
    }

    private async Task StartWifiAsync()
    {
        if (_server is not null) return;
        RotatePairToken();
        var builder = WebApplication.CreateBuilder();
        builder.WebHost.UseUrls($"http://0.0.0.0:{WebSocketPort}");
        var app = builder.Build();
        app.UseWebSockets();
        app.Map("/ws", HandleWebSocketAsync);
        await app.StartAsync();
        _server = app;
        await _lanDiscovery.StartAsync();
        DeviceStatus.Text = "ПК виден в локальной сети • ожидается QR";
        HeaderStatus.Text = "Wi‑Fi активен • требуется QR";
        HeaderDot.Foreground = Brushes.Gold;
    }

    private async Task StopWifiAsync()
    {
        await _lanDiscovery.StopAsync();
        if (_server is not null)
        {
            try { await _server.StopAsync(); await _server.DisposeAsync(); } catch { }
            _server = null;
        }
        List<WebSocket> sockets;
        List<string> clientIds;
        lock (_clients)
        {
            sockets = _clients.ToList();
            clientIds = _clientIds.Values.Distinct().ToList();
            _clients.Clear();
            _clientIds.Clear();
        }
        foreach (var socket in sockets)
            try { await socket.CloseAsync(WebSocketCloseStatus.NormalClosure, "Server stopped", CancellationToken.None); } catch { }
        foreach (var id in clientIds) MarkTrustedClient(id, false, "Wi‑Fi");
        UpdateConnectionStatus();
    }

    private async Task HandleWebSocketAsync(HttpContext context)
    {
        if (!context.WebSockets.IsWebSocketRequest)
        {
            context.Response.StatusCode = 400;
            return;
        }

        var clientId = context.Request.Query["clientId"].ToString();
        var suppliedPairToken = context.Request.Query["token"].ToString();
        var suppliedDeviceToken = context.Request.Query["deviceToken"].ToString();
        if (string.IsNullOrWhiteSpace(clientId))
        {
            context.Response.StatusCode = 401;
            return;
        }

        string? newDeviceSecret = null;
        var trusted = TryAuthenticateTrusted(clientId, suppliedDeviceToken);
        if (!trusted)
        {
            if (!ConsumePairToken(suppliedPairToken))
            {
                context.Response.StatusCode = 401;
                return;
            }
            var paired = PairTrustedClient(clientId, "Wi‑Fi");
            newDeviceSecret = paired.Secret;
        }

        var socket = await context.WebSockets.AcceptWebSocketAsync();
        lock (_clients)
        {
            _clients.Add(socket);
            _clientIds[socket] = clientId;
        }
        MarkTrustedClient(clientId, true, "Wi‑Fi");
        Dispatcher.Invoke(UpdateConnectionStatus);

        if (!string.IsNullOrWhiteSpace(newDeviceSecret))
        {
            await SendJsonAsync(socket, new
            {
                type = "paired",
                serverId = _state.ServerId,
                serverName = Environment.MachineName,
                deviceToken = newDeviceSecret,
                transport = "wifi"
            });
        }
        await SendSnapshotAsync(socket);

        var buffer = new byte[64 * 1024];
        try
        {
            while (socket.State == WebSocketState.Open)
            {
                using var message = new MemoryStream();
                WebSocketReceiveResult result;
                do
                {
                    result = await socket.ReceiveAsync(buffer, CancellationToken.None);
                    if (result.MessageType == WebSocketMessageType.Close) break;
                    message.Write(buffer, 0, result.Count);
                }
                while (!result.EndOfMessage);

                if (result.MessageType == WebSocketMessageType.Close) break;
                var text = Encoding.UTF8.GetString(message.ToArray());
                await HandleRemoteMessageAsync(text, clientId);
            }
        }
        catch (Exception ex)
        {
            Dispatcher.Invoke(() => DeviceStatus.Text = $"Ошибка канала устройства: {ex.Message}");
        }
        finally
        {
            bool stillOnline;
            lock (_clients)
            {
                _clients.Remove(socket);
                _clientIds.Remove(socket);
                stillOnline = _clientIds.Values.Any(x => x == clientId);
            }
            if (!stillOnline)
            {
                Dispatcher.Invoke(() => ReleaseRemoteHolds(clientId));
                MarkTrustedClient(clientId, false, "Wi‑Fi");
            }
            Dispatcher.Invoke(UpdateConnectionStatus);
        }
    }

    private static async Task SendJsonAsync(WebSocket socket, object payload)
    {
        var bytes = Encoding.UTF8.GetBytes(JsonSerializer.Serialize(payload, new JsonSerializerOptions { PropertyNamingPolicy = JsonNamingPolicy.CamelCase }));
        await socket.SendAsync(bytes, WebSocketMessageType.Text, true, CancellationToken.None);
    }

    private async Task StartBleAsync()
    {
        RotatePairToken();
        _bleAuthenticated = false;
        await _ble.StartAsync();
        await _ble.SetSnapshotAsync(JsonSerializer.Serialize(Snapshot(), _json));
        DeviceStatus.Text = "Bluetooth LE активен • готов к подключению";
        HeaderStatus.Text = "Bluetooth LE активен";
        HeaderDot.Foreground = Brushes.Gold;
    }

    private async Task HandleBleMessageAsync(string message)
    {
        try
        {
            using var doc = JsonDocument.Parse(message);
            var root = doc.RootElement;
            var type = root.TryGetProperty("type", out var typeProp) ? typeProp.GetString() ?? "" : "";
            if (!_bleAuthenticated)
            {
                if (type != "auth") return;
                var clientId = root.TryGetProperty("clientId", out var clientProp) ? clientProp.GetString() ?? "" : "";
                var deviceToken = root.TryGetProperty("deviceToken", out var deviceTokenProp) ? deviceTokenProp.GetString() ?? "" : "";
                var pairToken = root.TryGetProperty("token", out var tokenProp) ? tokenProp.GetString() ?? "" : "";
                if (string.IsNullOrWhiteSpace(clientId)) return;

                string? newSecret = null;
                if (!TryAuthenticateTrusted(clientId, deviceToken))
                {
                    if (!ConsumePairToken(pairToken)) return;
                    newSecret = PairTrustedClient(clientId, "Bluetooth").Secret;
                }

                _bleAuthenticated = true;
                _bleClientId = clientId;
                MarkTrustedClient(clientId, true, "Bluetooth");
                await _ble.SetSnapshotAsync(JsonSerializer.Serialize(Snapshot(newSecret), _json));
                Dispatcher.Invoke(() =>
                {
                    HeaderStatus.Text = "Устройство подключено по Bluetooth";
                    HeaderDot.Foreground = (Brush)FindResource("Green");
                    RefreshTrustedDevices();
                });
                return;
            }
            await HandleRemoteMessageAsync(message, _bleClientId);
        }
        catch (Exception ex)
        {
            Dispatcher.Invoke(() => DeviceStatus.Text = $"Ошибка Bluetooth: {ex.Message}");
        }
    }

    private async Task HandleRemoteMessageAsync(string message, string clientId)
    {
        try
        {
            using var doc = JsonDocument.Parse(message);
            var root = doc.RootElement;
            var messageType = root.TryGetProperty("type", out var typeProp) ? typeProp.GetString() ?? "" : "";

            if (messageType == "clientInfo")
            {
                var formFactor = root.TryGetProperty("formFactor", out var formProp) ? formProp.GetString() ?? "phone" : "phone";
                var deviceName = root.TryGetProperty("deviceName", out var nameProp) ? nameProp.GetString() : null;
                var label = string.Equals(formFactor, "tablet", StringComparison.OrdinalIgnoreCase) ? "Планшет" : "Телефон";
                UpdateTrustedMetadata(clientId, formFactor, deviceName, SelectedTransport());
                Dispatcher.Invoke(() => DeviceStatus.Text = $"{label} подключен по {SelectedTransport()}");
                return;
            }

            if (messageType == "switchProfile" && root.TryGetProperty("profileId", out var profileIdProp))
            {
                var profileId = profileIdProp.GetString() ?? "";
                var forced = root.TryGetProperty("force", out var forceProp) && forceProp.ValueKind == JsonValueKind.True;
                var profile = _profiles.FirstOrDefault(p => p.Id == profileId);
                if (profile is not null)
                {
                    await Dispatcher.InvokeAsync(() =>
                    {
                        _state.ActiveProfileId = profile.Id;
                        SaveState();
                        RefreshProfiles();
                    });
                    if (forced) Dispatcher.Invoke(() => DeviceStatus.Text = $"Профиль выбран с телефона: {profile.Name}");
                    await BroadcastSnapshotAsync();
                }
                return;
            }

            if (messageType == "switchPage" && root.TryGetProperty("pageId", out var pageIdProp))
            {
                var pageId = pageIdProp.GetString() ?? "";
                if (_profile is not null && _profile.Pages.Any(p => p.Id == pageId))
                {
                    await Dispatcher.InvokeAsync(() =>
                    {
                        _profile.ActivePageId = pageId;
                        SaveState();
                        LoadProfile();
                    });
                    await BroadcastSnapshotAsync();
                }
                return;
            }

            if ((messageType == "press" || messageType == "longPressStart" || messageType == "longPressEnd") && root.TryGetProperty("tileId", out var tileIdProp))
            {
                var tileId = tileIdProp.GetString() ?? "";
                var tile = _state.Profiles.SelectMany(p => p.Pages).SelectMany(p => p.Tiles).FirstOrDefault(t => t.Id == tileId);
                if (tile is null)
                {
                    Dispatcher.Invoke(() => DeviceStatus.Text = $"Команда не найдена: {tileId}");
                    return;
                }

                if (messageType == "longPressStart")
                {
                    await Dispatcher.InvokeAsync(() => StartRemoteHold(clientId, tile));
                    return;
                }
                if (messageType == "longPressEnd")
                {
                    await Dispatcher.InvokeAsync(() => EndRemoteHold(clientId, tile.Id));
                    return;
                }

                Dispatcher.Invoke(() => DeviceStatus.Text = $"Команда получена: {tile.Title}");
                var executeTask = await Dispatcher.InvokeAsync(() => ExecuteTileAsync(tile));
                await executeTask;
                return;
            }

            // Backward compatibility with old APKs.
            if (root.TryGetProperty("hotkey", out var hotkeyProp))
            {
                var hotkey = hotkeyProp.GetString() ?? "";
                await Dispatcher.InvokeAsync(() => ExecuteHotkey(hotkey));
                Dispatcher.Invoke(() => DeviceStatus.Text = $"Выполнена команда: {hotkey}");
            }
        }
        catch (Exception ex)
        {
            Dispatcher.Invoke(() => DeviceStatus.Text = $"Ошибка команды телефона: {ex.Message}");
        }
    }

    private void RotatePairToken()
    {
        _pairToken = Convert.ToBase64String(RandomNumberGenerator.GetBytes(18)).TrimEnd('=').Replace('+', '-').Replace('/', '_');
    }

    private bool ConsumePairToken(string supplied)
    {
        if (string.IsNullOrWhiteSpace(supplied) || string.IsNullOrWhiteSpace(_pairToken)) return false;
        var a = Encoding.UTF8.GetBytes(supplied); var b = Encoding.UTF8.GetBytes(_pairToken);
        var valid = a.Length == b.Length && CryptographicOperations.FixedTimeEquals(a, b);
        if (valid) RotatePairToken();
        return valid;
    }

    private void UpdateConnectionStatus()
    {
        int count;
        lock (_clients) count = _clients.Count;
        if (count > 0)
        {
            HeaderStatus.Text = count == 1 ? "Подключено 1 устройство" : $"Подключено устройств: {count}";
            HeaderDot.Foreground = (Brush)FindResource("Green");
            DeviceStatus.Text = count == 1 ? "Устройство подключено по Wi‑Fi" : $"Активных Wi‑Fi устройств: {count}";
        }
        else if (_server is not null)
        {
            HeaderStatus.Text = "ПК виден в локальной сети";
            HeaderDot.Foreground = Brushes.Gold;
            DeviceStatus.Text = "Ожидание привязанного устройства или нового QR";
        }
        else if (!_ble.IsRunning)
        {
            HeaderStatus.Text = "Связь не запущена";
            HeaderDot.Foreground = (Brush)FindResource("Muted");
        }
        RefreshTrustedDevices();
    }

    private void ShowQr_Click(object sender, RoutedEventArgs e)
    {
        if (SelectedTransport() == "Wifi")
        {
            if (_server is null) { MessageBox.Show(this, "Wi‑Fi связь ещё не запущена.", "NEXO"); return; }
            ShowQr($"macropad://connect?transport=wifi&serverId={Uri.EscapeDataString(_state.ServerId)}&host={Uri.EscapeDataString(LocalIp())}&port={WebSocketPort}&token={Uri.EscapeDataString(_pairToken)}",
                "Wi‑Fi: приложение на телефоне сначала обнаруживает этот ПК в той же сети. QR только подтверждает найденный ПК и передаёт одноразовый токен.");
        }
        else
        {
            if (!_ble.IsRunning) { MessageBox.Show(this, "Bluetooth LE ещё не запущен.", "NEXO"); return; }
            ShowQr($"macropad://connect?transport=ble&serverId={Uri.EscapeDataString(_state.ServerId)}&service={BleGattServer.ServiceUuid:D}&token={Uri.EscapeDataString(_pairToken)}",
                "Bluetooth LE: QR передаёт одноразовый токен авторизации, после чего телефон подключается к GATT service.");
        }
    }

    private void ShowQr(string payload, string caption)
    {
        using var generator = new QRCodeGenerator();
        using var data = generator.CreateQrCode(payload, QRCodeGenerator.ECCLevel.Q);
        var png = new PngByteQRCode(data).GetGraphic(12);
        var bitmap = new BitmapImage();
        using (var stream = new MemoryStream(png))
        {
            bitmap.BeginInit(); bitmap.CacheOption = BitmapCacheOption.OnLoad; bitmap.StreamSource = stream; bitmap.EndInit(); bitmap.Freeze();
        }

        var window = new Window { Owner = this, Title = "Быстрое подключение", Width = 440, Height = 525, ResizeMode = ResizeMode.NoResize, WindowStartupLocation = WindowStartupLocation.CenterOwner, Background = (Brush)FindResource("Bg") };
        _qrWindow = window;
        window.Closed += (_, _) => { if (ReferenceEquals(_qrWindow, window)) _qrWindow = null; };
        var panel = new StackPanel { Margin = new Thickness(22) };
        panel.Children.Add(new TextBlock { Text = "Подключить телефон", FontSize = 22, FontWeight = FontWeights.SemiBold, HorizontalAlignment = HorizontalAlignment.Center });
        panel.Children.Add(new TextBlock { Text = caption, Foreground = (Brush)FindResource("Muted"), TextAlignment = TextAlignment.Center, TextWrapping = TextWrapping.Wrap, Margin = new Thickness(0, 8, 0, 14) });
        var qrBorder = new Border { Background = Brushes.White, Padding = new Thickness(12), HorizontalAlignment = HorizontalAlignment.Center };
        qrBorder.Child = new Image { Width = 290, Height = 290, Source = bitmap };
        panel.Children.Add(qrBorder);
        panel.Children.Add(new TextBlock { Text = "Отсканируйте QR в мобильном приложении NEXO", TextAlignment = TextAlignment.Center, Margin = new Thickness(0, 14, 0, 0) });
        window.Content = panel; window.ShowDialog();
    }

    private object Snapshot(string? deviceToken = null)
    {
        object? active = null;
        if (_profile is not null && _page is not null)
        {
            active = new
            {
                id = _profile.Id,
                name = _profile.Name,
                icon = _profile.Icon,
                activePageId = _page.Id,
                pageId = _page.Id,
                pageName = _page.Name,
                rows = _page.Rows,
                columns = _page.Columns,
                pages = _profile.Pages.Select(pg => new { id = pg.Id, name = pg.Name }).ToList(),
                tiles = _page.Tiles.Select(t => new
                {
                    id = t.Id,
                    title = t.Title,
                    actionType = t.ActionType,
                    actionValue = t.ActionValue,
                    hotkey = t.Hotkey,
                    iconKind = SnapshotIconKind(t),
                    iconValue = SnapshotIconValue(t),
                    showLabel = t.ShowLabel,
                    rowSpan = t.RowSpan,
                    columnSpan = t.ColumnSpan
                }).ToList()
            };
        }

        return new
        {
            type = "profile",
            serverId = _state.ServerId,
            serverName = Environment.MachineName,
            activeProfileId = _profile?.Id ?? "",
            deviceToken,
            profile = active,
            profiles = _profiles.Select(p => new
            {
                id = p.Id,
                name = p.Name,
                icon = p.Icon,
                activePageId = p.ActivePageId,
                pages = p.Pages.Select(pg => new { id = pg.Id, name = pg.Name }).ToList()
            }).ToList()
        };
    }

    private async Task SendSnapshotAsync(WebSocket socket)
    {
        var bytes = Encoding.UTF8.GetBytes(JsonSerializer.Serialize(Snapshot(), _json));
        await socket.SendAsync(bytes, WebSocketMessageType.Text, true, CancellationToken.None);
    }

    private async Task BroadcastSnapshotAsync()
    {
        List<WebSocket> sockets;
        lock (_clients) sockets = _clients.Where(x => x.State == WebSocketState.Open).ToList();
        foreach (var socket in sockets) try { await SendSnapshotAsync(socket); } catch { }
        if (_ble.IsRunning) await _ble.SetSnapshotAsync(JsonSerializer.Serialize(Snapshot(), _json));
    }

    private void SaveAndBroadcast()
    {
        if (_page is not null) EnsureCapacity(_page);
        SaveState(); RebuildGrid(); _ = BroadcastSnapshotAsync();
    }

    private static (int Row, int Column)? FindSpace(bool[,] used, Tile tile, int rows, int columns)
    {
        var rowSpan = Math.Max(1, tile.RowSpan); var columnSpan = Math.Max(1, tile.ColumnSpan);
        for (var row = 0; row < rows; row++)
            for (var column = 0; column < columns; column++)
            {
                if (row + rowSpan > rows || column + columnSpan > columns) continue;
                var free = true;
                for (var y = 0; y < rowSpan && free; y++) for (var x = 0; x < columnSpan; x++) if (used[row + y, column + x]) { free = false; break; }
                if (free) return (row, column);
            }
        return null;
    }

    private static void Mark(bool[,] used, int row, int column, int rowSpan, int columnSpan)
    { for (var y = 0; y < rowSpan; y++) for (var x = 0; x < columnSpan; x++) used[row + y, column + x] = true; }

    private static bool IsBlank(Tile tile) => string.IsNullOrWhiteSpace(tile.ActionType) && string.IsNullOrWhiteSpace(tile.Hotkey) && tile.Title.Equals("Добавить", StringComparison.OrdinalIgnoreCase);
    private static int UsedArea(DeckPage page) => page.Tiles.Sum(t => Math.Max(1, t.RowSpan) * Math.Max(1, t.ColumnSpan));
    private static int ConfiguredArea(DeckPage page) => page.Tiles.Where(t => !IsBlank(t)).Sum(t => Math.Max(1, t.RowSpan) * Math.Max(1, t.ColumnSpan));
    private static void EnsureCapacity(DeckPage page)
    {
        page.Rows = Math.Clamp(page.Rows, 1, 12); page.Columns = Math.Clamp(page.Columns, 1, 12);
        var target = page.Rows * page.Columns;
        while (UsedArea(page) < target) page.Tiles.Add(new Tile());
        while (UsedArea(page) > target)
        {
            var blank = page.Tiles.LastOrDefault(IsBlank); if (blank is null) break; page.Tiles.Remove(blank);
        }
    }

    private static string Glyph(Tile tile) => tile.ActionType switch
    {
        "hotkey" => "⌨", "text" => "T", "open" => "↗", "url" => "◎", "folder" => "□", "multi" => "≡", "profile" => "⇄", "media" => "▶", _ => IsBlank(tile) ? "+" : "⌨"
    };

    private string? Prompt(string title, string initial)
    {
        var window = new Window { Owner = this, Title = title, Width = 390, Height = 165, ResizeMode = ResizeMode.NoResize, WindowStartupLocation = WindowStartupLocation.CenterOwner, Background = (Brush)FindResource("Bg") };
        var grid = new Grid { Margin = new Thickness(16) }; grid.RowDefinitions.Add(new RowDefinition { Height = new GridLength(38) }); grid.RowDefinitions.Add(new RowDefinition());
        var box = new TextBox { Text = initial, Height = 34 }; grid.Children.Add(box);
        var panel = new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Right, VerticalAlignment = VerticalAlignment.Bottom };
        var cancel = new Button { Content = "Отмена", Width = 85, Margin = new Thickness(0, 0, 7, 0) }; cancel.Click += (_, _) => window.Close();
        var ok = new Button { Content = "OK", Width = 85 }; ok.Click += (_, _) => window.DialogResult = true;
        panel.Children.Add(cancel); panel.Children.Add(ok); Grid.SetRow(panel, 1); grid.Children.Add(panel); window.Content = grid; box.SelectAll(); box.Focus();
        return window.ShowDialog() == true ? box.Text.Trim() : null;
    }

    private static string LocalIp()
    {
        try
        {
            var candidates = NetworkInterface.GetAllNetworkInterfaces()
                .Where(n => n.OperationalStatus == OperationalStatus.Up)
                .Where(n => n.NetworkInterfaceType is not NetworkInterfaceType.Loopback and not NetworkInterfaceType.Tunnel)
                .SelectMany(n =>
                {
                    IPInterfaceProperties properties;
                    try { properties = n.GetIPProperties(); }
                    catch { return Array.Empty<(NetworkInterface Nic, IPAddress Address, bool HasGateway, int Score)>(); }

                    var hasGateway = properties.GatewayAddresses.Any(g =>
                        g.Address.AddressFamily == AddressFamily.InterNetwork &&
                        !g.Address.Equals(IPAddress.Any) && !g.Address.Equals(IPAddress.None));
                    var virtualName = $"{n.Name} {n.Description}".ToLowerInvariant();
                    var isVirtual = virtualName.Contains("virtual") || virtualName.Contains("hyper-v") ||
                                    virtualName.Contains("vmware") || virtualName.Contains("virtualbox") ||
                                    virtualName.Contains("wsl") || virtualName.Contains("docker") ||
                                    virtualName.Contains("tailscale") || virtualName.Contains("zerotier");
                    var isPhysicalPreferred = n.NetworkInterfaceType is NetworkInterfaceType.Wireless80211 or NetworkInterfaceType.Ethernet or NetworkInterfaceType.GigabitEthernet;

                    return properties.UnicastAddresses
                        .Where(a => a.Address.AddressFamily == AddressFamily.InterNetwork && !IPAddress.IsLoopback(a.Address))
                        .Select(a =>
                        {
                            var score = (hasGateway ? 100 : 0) + (isPhysicalPreferred ? 40 : 0) - (isVirtual ? 200 : 0) + (IsPrivateIpv4(a.Address) ? 20 : 0);
                            return (Nic: n, Address: a.Address, HasGateway: hasGateway, Score: score);
                        });
                })
                .OrderByDescending(x => x.Score)
                .ToList();

            return candidates.FirstOrDefault().Address?.ToString() ?? "127.0.0.1";
        }
        catch
        {
            return "127.0.0.1";
        }
    }

    private static bool IsPrivateIpv4(IPAddress address)
    {
        var b = address.GetAddressBytes();
        return b.Length == 4 &&
               (b[0] == 10 ||
                (b[0] == 172 && b[1] is >= 16 and <= 31) ||
                (b[0] == 192 && b[1] == 168));
    }

    protected override async void OnClosed(EventArgs e)
    {
        SaveState();
        await StopAllTransportsAsync();
        await _lanDiscovery.DisposeAsync();
        await _ble.DisposeAsync();
        base.OnClosed(e);
    }

    #region Windows input
    private const uint INPUT_MOUSE = 0;
    private const uint INPUT_KEYBOARD = 1;
    private const uint INPUT_HARDWARE = 2;
    private const uint KEYEVENTF_KEYUP = 0x0002;
    private const uint KEYEVENTF_UNICODE = 0x0004;

    [StructLayout(LayoutKind.Sequential)]
    private struct INPUT
    {
        public uint type;
        public InputUnion U;
    }

    // The native INPUT union must include its largest member. On x64 MOUSEINPUT
    // makes INPUT 40 bytes. A keyboard-only union becomes 32 bytes and causes
    // SendInput to fail with ERROR_INVALID_PARAMETER.
    [StructLayout(LayoutKind.Explicit)]
    private struct InputUnion
    {
        [FieldOffset(0)] public MOUSEINPUT mi;
        [FieldOffset(0)] public KEYBDINPUT ki;
        [FieldOffset(0)] public HARDWAREINPUT hi;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct MOUSEINPUT
    {
        public int dx;
        public int dy;
        public uint mouseData;
        public uint dwFlags;
        public uint time;
        public UIntPtr dwExtraInfo;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct KEYBDINPUT
    {
        public ushort wVk;
        public ushort wScan;
        public uint dwFlags;
        public uint time;
        public UIntPtr dwExtraInfo;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct HARDWAREINPUT
    {
        public uint uMsg;
        public ushort wParamL;
        public ushort wParamH;
    }

    [DllImport("user32.dll", SetLastError = true)]
    private static extern uint SendInput(uint nInputs, INPUT[] pInputs, int cbSize);

    private static void SendInputs(IReadOnlyCollection<INPUT> inputs)
    {
        if (inputs.Count == 0) return;
        var buffer = inputs.ToArray();
        var sent = SendInput((uint)buffer.Length, buffer, Marshal.SizeOf<INPUT>());
        if (sent != buffer.Length)
        {
            var error = Marshal.GetLastWin32Error();
            throw new Win32Exception(error, $"SendInput отправил {sent} из {buffer.Length} событий (INPUT={Marshal.SizeOf<INPUT>()} байт)");
        }
    }

    private static void ExecuteHotkey(string hotkey)
    {
        if (string.IsNullOrWhiteSpace(hotkey)) return;
        var tokens = hotkey.Split('+', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
        var keys = new List<ushort>();
        foreach (var token in tokens)
        {
            var vk = TokenToVk(token);
            if (vk != 0) keys.Add(vk);
        }
        if (keys.Count == 0)
            throw new InvalidOperationException($"Не удалось распознать сочетание «{hotkey}».");

        var inputs = new List<INPUT>();
        foreach (var vk in keys) inputs.Add(KeyInput(vk, false));
        for (var i = keys.Count - 1; i >= 0; i--) inputs.Add(KeyInput(keys[i], true));
        SendInputs(inputs);
    }

    private static INPUT KeyInput(ushort vk, bool up) => new()
    {
        type = INPUT_KEYBOARD,
        U = new InputUnion { ki = new KEYBDINPUT { wVk = vk, dwFlags = up ? KEYEVENTF_KEYUP : 0 } }
    };

    private static ushort TokenToVk(string token)
    {
        token = token.Trim().ToUpperInvariant();
        if (token.Length == 1)
        {
            var c = token[0];
            if (c is >= 'A' and <= 'Z') return c;
            if (c is >= '0' and <= '9') return c;
        }
        if (token.StartsWith('F') && int.TryParse(token[1..], out var f) && f is >= 1 and <= 24) return (ushort)(0x70 + f - 1);
        if (token.StartsWith("NUM") && int.TryParse(token[3..], out var n) && n is >= 0 and <= 9) return (ushort)(0x60 + n);
        return token switch
        {
            "CTRL" or "CONTROL" => 0x11, "ALT" => 0x12, "SHIFT" => 0x10, "WIN" or "WINDOWS" => 0x5B,
            "TAB" => 0x09, "ENTER" or "RETURN" => 0x0D, "ESC" or "ESCAPE" => 0x1B, "SPACE" => 0x20,
            "BACKSPACE" => 0x08, "DELETE" => 0x2E, "INSERT" => 0x2D, "HOME" => 0x24, "END" => 0x23,
            "LEFT" => 0x25, "UP" => 0x26, "RIGHT" => 0x27, "DOWN" => 0x28, "PAGEUP" => 0x21, "PAGEDOWN" => 0x22,
            "PLUS" or "+" => 0xBB, "MINUS" or "-" => 0xBD, "COMMA" => 0xBC, "PERIOD" or "DOT" => 0xBE,
            "MEDIA_PLAY" or "MEDIA_PLAY_PAUSE" => 0xB3, "MEDIA_NEXT" => 0xB0, "MEDIA_PREV" => 0xB1,
            "VOLUME_MUTE" => 0xAD, "VOLUME_DOWN" => 0xAE, "VOLUME_UP" => 0xAF,
            _ => 0
        };
    }

    private static void SendText(string text)
    {
        if (string.IsNullOrEmpty(text)) return;
        var inputs = new List<INPUT>();
        foreach (var ch in text)
        {
            inputs.Add(new INPUT { type = INPUT_KEYBOARD, U = new InputUnion { ki = new KEYBDINPUT { wScan = ch, dwFlags = KEYEVENTF_UNICODE } } });
            inputs.Add(new INPUT { type = INPUT_KEYBOARD, U = new InputUnion { ki = new KEYBDINPUT { wScan = ch, dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP } } });
        }
        SendInputs(inputs);
    }
    #endregion
}

public sealed class AppState
{
    public string ServerId { get; set; } = Guid.NewGuid().ToString("N");
    public string ActiveProfileId { get; set; } = "";
    public string Transport { get; set; } = "Wifi";
    public List<Profile> Profiles { get; set; } = new();
    public List<TrustedClient> TrustedDevices { get; set; } = new();
    public List<IconAsset> IconLibrary { get; set; } = new();
}

public sealed class Profile
{
    public string Id { get; set; } = Guid.NewGuid().ToString("N");
    public string Name { get; set; } = "Profile";
    public string Icon { get; set; } = "•";
    public string Description { get; set; } = "";
    public string ActivePageId { get; set; } = "";
    public List<DeckPage> Pages { get; set; } = new();
}

public sealed class DeckPage
{
    public string Id { get; set; } = Guid.NewGuid().ToString("N");
    public string Name { get; set; } = "Page";
    public int Rows { get; set; } = 3;
    public int Columns { get; set; } = 4;
    public double Zoom { get; set; } = 1;
    public List<Tile> Tiles { get; set; } = new();
}

public sealed class Tile
{
    public string Id { get; set; } = Guid.NewGuid().ToString("N");
    public string Title { get; set; } = "Добавить";
    public string ActionType { get; set; } = "";
    public string ActionValue { get; set; } = "";
    public string Hotkey { get; set; } = "";
    public string IconKind { get; set; } = "auto";
    public string IconValue { get; set; } = "";
    public bool ShowLabel { get; set; } = true;
    public int RowSpan { get; set; } = 1;
    public int ColumnSpan { get; set; } = 1;
    public List<ActionStep> Steps { get; set; } = new();
}

public sealed class ActionStep
{
    public string Type { get; set; } = "hotkey";
    public string Value { get; set; } = "";
    public int DelayMs { get; set; } = 100;
}

public sealed record ActionItem(string Category, string Icon, string Title, string Description, string Type, string Value);


public sealed class TrustedClient
{
    public string Id { get; set; } = "";
    public string Name { get; set; } = "Телефон";
    public string FormFactor { get; set; } = "phone";
    public string Secret { get; set; } = "";
    public string Transport { get; set; } = "Wi‑Fi";
    public DateTime LastSeenUtc { get; set; } = DateTime.UtcNow;

    [JsonIgnore] public bool IsOnline { get; set; }
    [JsonIgnore] public string DeviceGlyph => FormFactor == "tablet" ? "▭" : "▯";
    [JsonIgnore] public string Details
        => $"{(IsOnline ? "● Онлайн" : "○ Офлайн")} • {Transport} • {LastSeenUtc.ToLocalTime():dd.MM HH:mm}";
}
