using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net.WebSockets;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using QRCoder;

namespace MacroPadRemote;

public partial class MainWindow
{
    private bool _v13FreshInstall;
    private bool _v13AllowWizardClose;
    private Window? _v13FirstRunWindow;
    private TaskCompletionSource<JsonElement>? _v13CatalogAwaiter;
    private TaskCompletionSource<JsonElement>? _v13WorkspaceAwaiter;
    private string? _v13CopiedProfileJson;
    private string? _v13CopiedTileJson;

    private void V13BeforeLoadState()
        => _v13FreshInstall = !File.Exists(_statePath);

    private void V13AfterLoadState()
    {
        // Existing installations must not suddenly receive the first-run wizard
        // after upgrading to v1.3.
        if (!_v13FreshInstall && !_state.SetupCompleted)
        {
            _state.SetupCompleted = true;
            SaveState();
        }
    }

    private async Task V13RunFirstLaunchWizardAsync()
    {
        if (_state.SetupCompleted) return;

        var window = new Window
        {
            Owner = this,
            Title = "NEXO — первый запуск",
            Width = 720,
            Height = 520,
            ResizeMode = ResizeMode.NoResize,
            WindowStartupLocation = WindowStartupLocation.CenterOwner,
            Background = (Brush)FindResource("Bg")
        };
        _v13FirstRunWindow = window;
        _v13AllowWizardClose = false;

        var root = new Grid { Margin = new Thickness(28) };
        root.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        root.RowDefinitions.Add(new RowDefinition());
        root.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });

        var title = new StackPanel();
        title.Children.Add(new TextBlock
        {
            Text = "Настройка NEXO",
            FontSize = 25,
            FontWeight = FontWeights.SemiBold
        });
        title.Children.Add(new TextBlock
        {
            Text = "Как настроить этот компьютер?",
            Foreground = (Brush)FindResource("Muted"),
            Margin = new Thickness(0, 7, 0, 18)
        });
        root.Children.Add(title);

        var choices = new Grid { Margin = new Thickness(0, 82, 0, 70) };
        choices.ColumnDefinitions.Add(new ColumnDefinition());
        choices.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(16) });
        choices.ColumnDefinitions.Add(new ColumnDefinition());

        Button Choice(string heading, string description)
        {
            var panel = new StackPanel { Margin = new Thickness(18) };
            panel.Children.Add(new TextBlock { Text = heading, FontSize = 18, FontWeight = FontWeights.SemiBold, TextWrapping = TextWrapping.Wrap });
            panel.Children.Add(new TextBlock { Text = description, Foreground = (Brush)FindResource("Muted"), TextWrapping = TextWrapping.Wrap, Margin = new Thickness(0, 8, 0, 0) });
            return new Button { Content = panel, HorizontalContentAlignment = HorizontalAlignment.Stretch, VerticalContentAlignment = VerticalAlignment.Stretch };
        }

        var fresh = Choice("Настроить как новое устройство", "Создать самостоятельное рабочее пространство на этом ПК. Текущая логика NEXO остаётся без изменений.");
        var restore = Choice("Перенести профили с другого ПК", "Отсканировать QR телефоном или планшетом и выбрать сохранённое рабочее пространство другого компьютера.");

        choices.Children.Add(fresh);
        Grid.SetColumn(restore, 2);
        choices.Children.Add(restore);
        Grid.SetRow(choices, 1);
        root.Children.Add(choices);

        var note = new TextBlock
        {
            Text = "Копии рабочих пространств хранятся только во внутреннем защищённом хранилище мобильного устройства.",
            Foreground = (Brush)FindResource("Muted"),
            FontSize = 11,
            TextWrapping = TextWrapping.Wrap
        };
        Grid.SetRow(note, 2);
        root.Children.Add(note);

        fresh.Click += (_, _) =>
        {
            _state.SetupCompleted = true;
            SaveState();
            _v13AllowWizardClose = true;
            window.Close();
        };

        restore.Click += async (_, _) =>
        {
            try
            {
                if (_server is null)
                {
                    await StopAllTransportsAsync();
                    _state.Transport = "Wifi";
                    ApplyTransport();
                    SaveState();
                    await StartWifiAsync();
                }

                RotatePairToken();
                var payload = $"macropad://connect?transport=wifi&mode=restore&serverId={Uri.EscapeDataString(_state.ServerId)}&host={Uri.EscapeDataString(LocalIp())}&port={WebSocketPort}&token={Uri.EscapeDataString(_pairToken)}";

                var transfer = new Grid { Margin = new Thickness(0, 70, 0, 40) };
                transfer.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(330) });
                transfer.ColumnDefinitions.Add(new ColumnDefinition());
                var qr = new Border
                {
                    Background = Brushes.White,
                    Padding = new Thickness(12),
                    Width = 300,
                    Height = 300,
                    HorizontalAlignment = HorizontalAlignment.Left,
                    Child = new Image { Source = V13QrImage(payload), Stretch = Stretch.Uniform }
                };
                transfer.Children.Add(qr);

                var copy = new StackPanel { Margin = new Thickness(24, 16, 0, 0) };
                copy.Children.Add(new TextBlock { Text = "Перенос профилей", FontSize = 20, FontWeight = FontWeights.SemiBold });
                copy.Children.Add(new TextBlock
                {
                    Text = "1. На телефоне откройте NEXO и выберите «Перенос / библиотека».\n\n2. Отсканируйте этот QR.\n\n3. Подтвердите биометрию или PIN устройства.\n\n4. Выберите компьютер, данные которого нужно перенести.",
                    Foreground = (Brush)FindResource("Muted"),
                    TextWrapping = TextWrapping.Wrap,
                    Margin = new Thickness(0, 12, 0, 0)
                });
                copy.Children.Add(new TextBlock
                {
                    Text = "Ожидание выбора на мобильном устройстве…",
                    Foreground = (Brush)FindResource("Blue"),
                    FontWeight = FontWeights.SemiBold,
                    Margin = new Thickness(0, 18, 0, 0)
                });
                Grid.SetColumn(copy, 1);
                transfer.Children.Add(copy);

                root.Children.Remove(choices);
                Grid.SetRow(transfer, 1);
                root.Children.Add(transfer);
            }
            catch (Exception ex)
            {
                MessageBox.Show(window, $"Не удалось запустить перенос.\n\n{ex.Message}", "NEXO");
            }
        };

        window.Closing += (_, e) =>
        {
            if (!_v13AllowWizardClose && !_state.SetupCompleted)
                e.Cancel = true;
        };
        window.Closed += (_, _) =>
        {
            if (ReferenceEquals(_v13FirstRunWindow, window)) _v13FirstRunWindow = null;
        };

        window.Content = root;
        window.ShowDialog();
    }

    private static ImageSource V13QrImage(string payload)
    {
        using var generator = new QRCodeGenerator();
        using var data = generator.CreateQrCode(payload, QRCodeGenerator.ECCLevel.Q);
        var png = new PngByteQRCode(data).GetGraphic(10);
        var bitmap = new BitmapImage();
        using var stream = new MemoryStream(png);
        bitmap.BeginInit();
        bitmap.CacheOption = BitmapCacheOption.OnLoad;
        bitmap.StreamSource = stream;
        bitmap.EndInit();
        bitmap.Freeze();
        return bitmap;
    }

    private object V13WorkspaceBackupMessage() => new
    {
        type = "workspaceBackup",
        format = 1,
        serverId = _state.ServerId,
        serverName = Environment.MachineName,
        updatedUtc = _state.WorkspaceUpdatedUtc,
        activeProfileId = _state.ActiveProfileId,
        profiles = _profiles.ToList(),
        iconLibrary = _state.IconLibrary
    };

    private Task V13SendWorkspaceBackupAsync(WebSocket socket)
        => SendJsonAsync(socket, V13WorkspaceBackupMessage());

    private async Task V13BroadcastWorkspaceBackupOnlyAsync()
    {
        List<WebSocket> sockets;
        lock (_clients)
            sockets = _clients.Where(x => x.State == WebSocketState.Open).ToList();

        foreach (var socket in sockets)
            try { await V13SendWorkspaceBackupAsync(socket); } catch { }

        if (_ble.IsRunning && _bleAuthenticated && !string.IsNullOrWhiteSpace(_bleClientId))
        {
            try
            {
                await _ble.SetSnapshotAsync(JsonSerializer.Serialize(V13WorkspaceBackupMessage(), _json));
                await Task.Delay(180);
                await _ble.SetSnapshotAsync(JsonSerializer.Serialize(Snapshot(), _json));
            }
            catch { }
        }
    }

    private async Task V13SendWorkspaceBackupToClientAsync(string clientId)
    {
        List<WebSocket> sockets;
        lock (_clients)
            sockets = _clientIds.Where(x => x.Value == clientId && x.Key.State == WebSocketState.Open).Select(x => x.Key).ToList();

        foreach (var socket in sockets)
            try { await V13SendWorkspaceBackupAsync(socket); } catch { }

        if (_ble.IsRunning && string.Equals(_bleClientId, clientId, StringComparison.Ordinal))
        {
            try
            {
                await _ble.SetSnapshotAsync(JsonSerializer.Serialize(V13WorkspaceBackupMessage(), _json));
                await Task.Delay(220);
                await _ble.SetSnapshotAsync(JsonSerializer.Serialize(Snapshot(), _json));
            }
            catch { }
        }
    }

    private async Task<bool> V13HandleRemoteMessageAsync(JsonElement root, string messageType, string clientId)
    {
        if (messageType == "workspaceBackupRequest")
        {
            await V13SendWorkspaceBackupToClientAsync(clientId);
            return true;
        }

        if (messageType == "restoreWorkspace" && root.TryGetProperty("workspace", out var restore))
        {
            await Dispatcher.InvokeAsync(() => V13ImportWorkspace(restore, completeSetup: true));
            await BroadcastSnapshotAsync();
            return true;
        }

        if (messageType == "backupCatalogResponse")
        {
            _v13CatalogAwaiter?.TrySetResult(root.Clone());
            return true;
        }

        if (messageType == "backupWorkspaceResponse")
        {
            _v13WorkspaceAwaiter?.TrySetResult(root.Clone());
            return true;
        }

        return false;
    }

    private void V13ImportWorkspace(JsonElement workspace, bool completeSetup)
    {
        if (!workspace.TryGetProperty("profiles", out var profilesElement)) return;
        var imported = JsonSerializer.Deserialize<List<Profile>>(profilesElement.GetRawText(), _json) ?? new List<Profile>();
        if (imported.Count == 0) return;

        _profiles.Clear();
        foreach (var profile in imported)
        {
            profile.Pages ??= new List<DeckPage>();
            if (profile.Pages.Count == 0) profile.Pages.Add(DefaultPage("Страница 1"));
            foreach (var page in profile.Pages)
            {
                page.Tiles ??= new List<Tile>();
                EnsureCapacity(page);
            }
            if (string.IsNullOrWhiteSpace(profile.ActivePageId) || profile.Pages.All(x => x.Id != profile.ActivePageId))
                profile.ActivePageId = profile.Pages[0].Id;
            _profiles.Add(profile);
        }

        if (workspace.TryGetProperty("iconLibrary", out var icons) && icons.ValueKind == JsonValueKind.Array)
            _state.IconLibrary = JsonSerializer.Deserialize<List<IconAsset>>(icons.GetRawText(), _json) ?? new List<IconAsset>();

        var requestedActive = workspace.TryGetProperty("activeProfileId", out var active) ? active.GetString() ?? "" : "";
        _state.ActiveProfileId = _profiles.Any(x => x.Id == requestedActive) ? requestedActive : _profiles[0].Id;
        if (completeSetup) _state.SetupCompleted = true;
        SaveState();
        RefreshProfiles();

        if (completeSetup && _v13FirstRunWindow is not null)
        {
            _v13AllowWizardClose = true;
            _v13FirstRunWindow.Close();
        }

        DeviceStatus.Text = completeSetup ? "Профили перенесены с мобильного устройства" : "Рабочее пространство обновлено";
    }

    private async Task V13SendControlAsync(object payload)
    {
        List<WebSocket> sockets;
        lock (_clients) sockets = _clients.Where(x => x.State == WebSocketState.Open).ToList();
        foreach (var socket in sockets)
            try { await SendJsonAsync(socket, payload); } catch { }

        if (_ble.IsRunning && !string.IsNullOrWhiteSpace(_bleClientId))
        {
            // Library transfer is intentionally Wi-Fi first: large workspace payloads
            // are sent over WebSocket. BLE remains available for normal controls and
            // automatic small-state operation.
        }
    }

    private static async Task<JsonElement?> V13WaitAsync(Task<JsonElement> task, int timeoutMs = 30000)
    {
        var completed = await Task.WhenAny(task, Task.Delay(timeoutMs));
        return ReferenceEquals(completed, task) ? await task : null;
    }

    public async Task V13OpenRemoteLibraryAsync()
    {
        List<WebSocket> sockets;
        lock (_clients) sockets = _clients.Where(x => x.State == WebSocketState.Open).ToList();
        if (sockets.Count == 0)
        {
            MessageBox.Show(this, "Подключите телефон или планшет к NEXO по Wi‑Fi.\nНа мобильном устройстве появится системный запрос биометрии/PIN.", "NEXO");
            return;
        }

        _v13CatalogAwaiter = new TaskCompletionSource<JsonElement>(TaskCreationOptions.RunContinuationsAsynchronously);
        await V13SendControlAsync(new { type = "backupCatalogRequest" });
        var catalogResponse = await V13WaitAsync(_v13CatalogAwaiter.Task);
        _v13CatalogAwaiter = null;
        if (catalogResponse is null)
        {
            MessageBox.Show(this, "Мобильное устройство не подтвердило доступ к библиотеке.", "NEXO");
            return;
        }

        if (!catalogResponse.Value.TryGetProperty("devices", out var devicesElement) || devicesElement.ValueKind != JsonValueKind.Array)
        {
            MessageBox.Show(this, "На мобильном устройстве пока нет сохранённых рабочих пространств.", "NEXO");
            return;
        }

        var devices = devicesElement.EnumerateArray()
            .Select(x => new V13RemoteDevice(
                x.TryGetProperty("serverId", out var sid) ? sid.GetString() ?? "" : "",
                x.TryGetProperty("serverName", out var sn) ? sn.GetString() ?? "NEXO PC" : "NEXO PC",
                x.TryGetProperty("updatedUtc", out var upd) && DateTime.TryParse(upd.GetString(), out var dt) ? dt : DateTime.MinValue,
                x.TryGetProperty("profileCount", out var pc) ? pc.GetInt32() : 0))
            .Where(x => !string.IsNullOrWhiteSpace(x.ServerId))
            .ToList();

        if (devices.Count == 0)
        {
            MessageBox.Show(this, "На мобильном устройстве пока нет сохранённых рабочих пространств.", "NEXO");
            return;
        }

        var win = new Window
        {
            Owner = this,
            Title = "NEXO — библиотека устройств",
            Width = 1120,
            Height = 720,
            MinWidth = 900,
            MinHeight = 600,
            WindowStartupLocation = WindowStartupLocation.CenterOwner,
            Background = (Brush)FindResource("Bg")
        };

        var root = new Grid();
        root.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(280) });
        root.ColumnDefinitions.Add(new ColumnDefinition());

        var left = new DockPanel { Background = (Brush)FindResource("Panel") };
        var heading = new TextBlock { Text = "Сохранённые устройства", FontSize = 18, FontWeight = FontWeights.SemiBold, Margin = new Thickness(16) };
        DockPanel.SetDock(heading, Dock.Top);
        left.Children.Add(heading);
        var deviceList = new ListBox { Margin = new Thickness(8) };
        deviceList.ItemsSource = devices;
        deviceList.DisplayMemberPath = nameof(V13RemoteDevice.Display);
        left.Children.Add(deviceList);
        root.Children.Add(left);

        var right = new Grid { Margin = new Thickness(18) };
        right.RowDefinitions.Add(new RowDefinition { Height = new GridLength(52) });
        right.RowDefinitions.Add(new RowDefinition());
        right.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(260) });
        right.ColumnDefinitions.Add(new ColumnDefinition());

        var status = new TextBlock
        {
            Text = "Выберите устройство слева. Доступ к данным уже подтверждён на мобильном устройстве.",
            Foreground = (Brush)FindResource("Muted"),
            VerticalAlignment = VerticalAlignment.Center
        };
        Grid.SetColumnSpan(status, 2);
        right.Children.Add(status);

        var profileList = new ListBox { Margin = new Thickness(0, 8, 12, 0) };
        Grid.SetRow(profileList, 1);
        right.Children.Add(profileList);

        var profileCopyMenu = new ContextMenu();
        var profileCopy = new MenuItem { Header = "Копировать профиль" };
        profileCopy.Click += (_, _) =>
        {
            if (profileList.SelectedItem is Profile p)
            {
                V13CopyProfile(p);
                status.Text = $"Профиль «{p.Name}» скопирован. В основном окне используйте правую кнопку мыши → «Вставить профиль».";
            }
        };
        profileCopyMenu.Items.Add(profileCopy);
        profileList.ContextMenu = profileCopyMenu;

        var workspaceScroll = new ScrollViewer { Margin = new Thickness(8, 8, 0, 0), VerticalScrollBarVisibility = ScrollBarVisibility.Auto };
        var tilePanel = new WrapPanel { Orientation = Orientation.Horizontal };
        workspaceScroll.Content = tilePanel;
        Grid.SetRow(workspaceScroll, 1);
        Grid.SetColumn(workspaceScroll, 1);
        right.Children.Add(workspaceScroll);

        List<Profile> remoteProfiles = new();

        void RenderProfile(Profile? profile)
        {
            tilePanel.Children.Clear();
            if (profile is null) return;
            var page = profile.Pages.FirstOrDefault(p => p.Id == profile.ActivePageId) ?? profile.Pages.FirstOrDefault();
            if (page is null) return;
            foreach (var tile in page.Tiles)
            {
                var b = new Button
                {
                    Width = 142,
                    Height = 88,
                    Margin = new Thickness(5),
                    Tag = tile,
                    Content = new TextBlock
                    {
                        Text = string.IsNullOrWhiteSpace(tile.Title) ? "Функция" : tile.Title,
                        TextWrapping = TextWrapping.Wrap,
                        TextAlignment = TextAlignment.Center
                    }
                };
                var menu = new ContextMenu();
                var copy = new MenuItem { Header = "Копировать функцию" };
                copy.Click += (_, _) =>
                {
                    V13CopyTile(tile);
                    status.Text = $"Функция «{tile.Title}» скопирована. В основном рабочем поле нажмите правой кнопкой по ячейке → «Вставить функцию».";
                };
                menu.Items.Add(copy);
                b.ContextMenu = menu;
                tilePanel.Children.Add(b);
            }
        }

        profileList.SelectionChanged += (_, _) => RenderProfile(profileList.SelectedItem as Profile);

        deviceList.SelectionChanged += async (_, _) =>
        {
            if (deviceList.SelectedItem is not V13RemoteDevice device) return;
            status.Text = $"Загрузка «{device.Name}»…";
            _v13WorkspaceAwaiter = new TaskCompletionSource<JsonElement>(TaskCreationOptions.RunContinuationsAsynchronously);
            await V13SendControlAsync(new { type = "backupWorkspaceRequest", serverId = device.ServerId });
            var response = await V13WaitAsync(_v13WorkspaceAwaiter.Task);
            _v13WorkspaceAwaiter = null;
            if (response is null || !response.Value.TryGetProperty("workspace", out var workspace))
            {
                status.Text = "Не удалось получить рабочее пространство.";
                return;
            }

            remoteProfiles = workspace.TryGetProperty("profiles", out var p)
                ? JsonSerializer.Deserialize<List<Profile>>(p.GetRawText(), _json) ?? new List<Profile>()
                : new List<Profile>();
            profileList.ItemsSource = remoteProfiles;
            profileList.DisplayMemberPath = nameof(Profile.Name);
            profileList.SelectedIndex = remoteProfiles.Count > 0 ? 0 : -1;
            status.Text = $"{device.Name} • профилей: {remoteProfiles.Count} • сохранено {device.UpdatedUtc.ToLocalTime():dd.MM.yyyy HH:mm}";
        };

        Grid.SetColumn(right, 1);
        root.Children.Add(right);
        win.Content = root;
        deviceList.SelectedIndex = 0;
        win.ShowDialog();
    }

    private void V13CopyProfile(Profile profile)
    {
        _v13CopiedProfileJson = JsonSerializer.Serialize(profile, _json);
    }

    private bool V13HasCopiedProfile => !string.IsNullOrWhiteSpace(_v13CopiedProfileJson);

    private void V13PasteProfile()
    {
        if (!V13HasCopiedProfile) return;
        var clone = JsonSerializer.Deserialize<Profile>(_v13CopiedProfileJson!, _json);
        if (clone is null) return;

        var pageIdMap = new Dictionary<string, string>(StringComparer.Ordinal);
        clone.Id = Guid.NewGuid().ToString("N");
        clone.Name = $"{clone.Name} copy";
        foreach (var page in clone.Pages)
        {
            var oldPageId = page.Id;
            var newPageId = Guid.NewGuid().ToString("N");
            pageIdMap[oldPageId] = newPageId;
            page.Id = newPageId;
            foreach (var tile in page.Tiles)
                tile.Id = Guid.NewGuid().ToString("N");
        }

        foreach (var page in clone.Pages)
            foreach (var tile in page.Tiles)
                if (tile.ActionType == "folder" && pageIdMap.TryGetValue(tile.ActionValue, out var mapped))
                    tile.ActionValue = mapped;

        clone.ActivePageId = pageIdMap.TryGetValue(clone.ActivePageId, out var active) ? active : clone.Pages.FirstOrDefault()?.Id ?? "";
        _profiles.Add(clone);
        _state.ActiveProfileId = clone.Id;
        SaveState();
        RefreshProfiles();
        _ = BroadcastSnapshotAsync();
    }

    private void V13CopyTile(Tile tile)
    {
        _v13CopiedTileJson = JsonSerializer.Serialize(tile, _json);
    }

    private bool V13HasCopiedTile => !string.IsNullOrWhiteSpace(_v13CopiedTileJson);

    private void V13PasteTile(Tile target)
    {
        if (!V13HasCopiedTile) return;
        var source = JsonSerializer.Deserialize<Tile>(_v13CopiedTileJson!, _json);
        if (source is null) return;

        if (!IsBlank(target) && MessageBox.Show(this, $"Заменить функцию «{target.Title}»?", "NEXO", MessageBoxButton.YesNo) != MessageBoxResult.Yes)
            return;

        target.Title = source.Title;
        target.ActionType = source.ActionType;
        target.ActionValue = source.ActionValue;
        target.Hotkey = source.Hotkey;
        target.IconKind = source.IconKind;
        target.IconValue = source.IconValue;
        target.ShowLabel = source.ShowLabel;
        target.Steps = JsonSerializer.Deserialize<List<ActionStep>>(JsonSerializer.Serialize(source.Steps, _json), _json) ?? new List<ActionStep>();
        target.MacroIntervalMs = source.MacroIntervalMs;
        target.MacroRepeatCount = source.MacroRepeatCount;
        target.MacroStartDelayMs = source.MacroStartDelayMs;

        SaveAndBroadcast();
        RefreshInspector();
    }
}

public sealed record V13RemoteDevice(string ServerId, string Name, DateTime UpdatedUtc, int ProfileCount)
{
    public string Display => $"{Name}\n{ProfileCount} проф. • {UpdatedUtc.ToLocalTime():dd.MM HH:mm}";
}
