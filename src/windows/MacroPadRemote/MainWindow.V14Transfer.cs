using System;
using System.Collections.Generic;
using System.Linq;
using System.Net.WebSockets;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

namespace MacroPadRemote;

public partial class MainWindow
{
    private TaskCompletionSource<JsonElement>? _v14TransferAwaiter;
    private bool _v14ApplyingTransfer;

    public UIElement V14BuildDevicesTab(Window owner)
    {
        var scroll = new ScrollViewer { VerticalScrollBarVisibility = ScrollBarVisibility.Auto };
        var root = new StackPanel { Margin = new Thickness(22) };
        scroll.Content = root;

        root.Children.Add(new TextBlock
        {
            Text = "Устройства",
            FontSize = 21,
            FontWeight = FontWeights.SemiBold
        });
        root.Children.Add(new TextBlock
        {
            Text = "Телефон или планшет используется как транспорт для выбранных профилей и настроек. В обычном режиме NEXO Mobile не сохраняет рабочие горячие клавиши.",
            Foreground = (Brush)FindResource("Muted"),
            TextWrapping = TextWrapping.Wrap,
            Margin = new Thickness(0, 7, 0, 18)
        });

        var transferBorder = new Border
        {
            Background = (Brush)FindResource("Panel"),
            BorderBrush = (Brush)FindResource("Border"),
            BorderThickness = new Thickness(1),
            Padding = new Thickness(16),
            Margin = new Thickness(0, 0, 0, 14)
        };
        var transfer = new StackPanel();
        transferBorder.Child = transfer;
        root.Children.Add(transferBorder);

        transfer.Children.Add(new TextBlock
        {
            Text = "Передача через устройство",
            FontSize = 17,
            FontWeight = FontWeights.SemiBold
        });
        transfer.Children.Add(new TextBlock
        {
            Text = "Выберите один или несколько профилей. Пакет будет сохранён на подключённом телефоне/планшете только для последующего импорта на другой ПК.",
            Foreground = (Brush)FindResource("Muted"),
            TextWrapping = TextWrapping.Wrap,
            Margin = new Thickness(0, 6, 0, 10)
        });

        var profiles = new ListBox
        {
            Height = 150,
            SelectionMode = SelectionMode.Extended,
            ItemsSource = _profiles,
            DisplayMemberPath = nameof(Profile.Name)
        };
        transfer.Children.Add(profiles);
        foreach (var item in _profiles)
            profiles.SelectedItems.Add(item);

        var createLink = new CheckBox
        {
            Content = "Создать связь между компьютерами при импорте этого пакета",
            IsChecked = true,
            Margin = new Thickness(0, 10, 0, 10)
        };
        transfer.Children.Add(createLink);

        var transferButtons = new WrapPanel();
        var sendSelected = new Button { Content = "Передать выбранные профили", MinWidth = 190, Height = 34, Margin = new Thickness(0, 0, 8, 8) };
        var sendAll = new Button { Content = "Передать настройки и все профили", MinWidth = 215, Height = 34, Margin = new Thickness(0, 0, 8, 8) };
        var importDevice = new Button { Content = "Импортировать с устройства", MinWidth = 190, Height = 34, Margin = new Thickness(0, 0, 8, 8) };
        transferButtons.Children.Add(sendSelected);
        transferButtons.Children.Add(sendAll);
        transferButtons.Children.Add(importDevice);
        transfer.Children.Add(transferButtons);

        sendSelected.Click += async (_, _) =>
        {
            var selected = profiles.SelectedItems.Cast<Profile>().ToList();
            if (selected.Count == 0)
            {
                MessageBox.Show(owner, "Выберите хотя бы один профиль.", "NEXO");
                return;
            }
            await V14SendTransferPackageAsync(selected, includeAllSettings: false, createLink: createLink.IsChecked == true, markPending: true);
        };

        sendAll.Click += async (_, _) =>
        {
            await V14SendTransferPackageAsync(_profiles.ToList(), includeAllSettings: true, createLink: createLink.IsChecked == true, markPending: true);
        };

        importDevice.Click += async (_, _) => await V14ImportFromDeviceAsync(owner, automatic: false);

        var linkBorder = new Border
        {
            Background = (Brush)FindResource("Panel"),
            BorderBrush = (Brush)FindResource("Border"),
            BorderThickness = new Thickness(1),
            Padding = new Thickness(16)
        };
        var link = new StackPanel();
        linkBorder.Child = link;
        root.Children.Add(linkBorder);

        link.Children.Add(new TextBlock
        {
            Text = "Связь между компьютерами",
            FontSize = 17,
            FontWeight = FontWeights.SemiBold
        });

        var linkStatus = new TextBlock
        {
            TextWrapping = TextWrapping.Wrap,
            Margin = new Thickness(0, 7, 0, 10),
            Foreground = (Brush)FindResource("Muted")
        };
        link.Children.Add(linkStatus);

        var auto = new CheckBox
        {
            Content = "Автоматически обновлять связь при каждом изменении",
            IsChecked = _state.DeviceLinkAutoUpdate,
            Margin = new Thickness(0, 0, 0, 10)
        };
        link.Children.Add(auto);

        var linkButtons = new WrapPanel();
        var update = new Button { Content = "Обновить связь", Width = 145, Height = 34, Margin = new Thickness(0, 0, 8, 8) };
        var toggle = new Button { Width = 145, Height = 34, Margin = new Thickness(0, 0, 8, 8) };
        var prepare = new Button { Content = "Создать связь", Width = 145, Height = 34, Margin = new Thickness(0, 0, 8, 8) };
        linkButtons.Children.Add(update);
        linkButtons.Children.Add(toggle);
        linkButtons.Children.Add(prepare);
        link.Children.Add(linkButtons);

        void refreshLinkUi()
        {
            var sourceKnown = !string.IsNullOrWhiteSpace(_state.DeviceLinkSourceServerId);
            var isSource = sourceKnown && string.Equals(_state.DeviceLinkSourceServerId, _state.ServerId, StringComparison.Ordinal);
            linkStatus.Text = !sourceKnown
                ? "Связь не настроена."
                : _state.DeviceLinkEnabled
                    ? isSource
                        ? $"Связь активна. Этот ПК — источник «{Environment.MachineName}»."
                        : $"Связь активна. Источник: {_state.DeviceLinkSourceServerName}."
                    : $"Связь приостановлена. Сохранённый источник: {_state.DeviceLinkSourceServerName}.";
            toggle.Content = _state.DeviceLinkEnabled ? "Разорвать связь" : "Восстановить связь";
            toggle.IsEnabled = sourceKnown;
            update.IsEnabled = sourceKnown && _state.DeviceLinkEnabled;
            auto.IsEnabled = sourceKnown && _state.DeviceLinkEnabled;
        }

        auto.Checked += (_, _) =>
        {
            _state.DeviceLinkAutoUpdate = true;
            SaveState();
            refreshLinkUi();
        };
        auto.Unchecked += (_, _) =>
        {
            _state.DeviceLinkAutoUpdate = false;
            SaveState();
            refreshLinkUi();
        };

        prepare.Click += async (_, _) =>
        {
            _state.DeviceLinkEnabled = true;
            _state.DeviceLinkAutoUpdate = auto.IsChecked == true;
            _state.DeviceLinkSourceServerId = _state.ServerId;
            _state.DeviceLinkSourceServerName = Environment.MachineName;
            SaveState();
            refreshLinkUi();
            await V14SendTransferPackageAsync(_profiles.ToList(), includeAllSettings: true, createLink: true, markPending: true);
        };

        toggle.Click += (_, _) =>
        {
            if (string.IsNullOrWhiteSpace(_state.DeviceLinkSourceServerId)) return;
            _state.DeviceLinkEnabled = !_state.DeviceLinkEnabled;
            SaveState();
            refreshLinkUi();
        };

        update.Click += async (_, _) =>
        {
            if (!_state.DeviceLinkEnabled) return;
            if (string.Equals(_state.DeviceLinkSourceServerId, _state.ServerId, StringComparison.Ordinal))
                await V14SendTransferPackageAsync(_profiles.ToList(), includeAllSettings: true, createLink: true, markPending: false, linkUpdate: true);
            else
                await V14ImportFromDeviceAsync(owner, automatic: false, requestedSourceId: _state.DeviceLinkSourceServerId);
            refreshLinkUi();
        };

        refreshLinkUi();
        return scroll;
    }

    private object V14TransferPackage(
        IReadOnlyCollection<Profile> profiles,
        bool includeAllSettings,
        bool createLink,
        bool markPending,
        bool linkUpdate)
    {
        return new
        {
            type = "transferPackage",
            format = 2,
            transferId = Guid.NewGuid().ToString("N"),
            sourceServerId = _state.ServerId,
            sourceServerName = Environment.MachineName,
            updatedUtc = _state.WorkspaceUpdatedUtc,
            includeAllSettings,
            createLink,
            markPending,
            linkUpdate,
            activeProfileId = _state.ActiveProfileId,
            defaultProfileId = _state.DefaultProfileId,
            profiles = profiles.ToList(),
            iconLibrary = includeAllSettings ? _state.IconLibrary : new List<IconAsset>()
        };
    }

    private async Task V14SendTransferPackageAsync(
        IReadOnlyCollection<Profile> profiles,
        bool includeAllSettings,
        bool createLink,
        bool markPending,
        bool linkUpdate = false)
    {
        List<WebSocket> sockets;
        lock (_clients)
            sockets = _clients.Where(x => x.State == WebSocketState.Open).ToList();

        if (sockets.Count == 0)
        {
            MessageBox.Show(this, "Подключите телефон или планшет к этому ПК по Wi‑Fi.", "NEXO");
            return;
        }

        if (createLink)
        {
            _state.DeviceLinkEnabled = true;
            _state.DeviceLinkSourceServerId = _state.ServerId;
            _state.DeviceLinkSourceServerName = Environment.MachineName;
            SaveState();
        }

        var package = V14TransferPackage(profiles, includeAllSettings, createLink, markPending, linkUpdate);
        foreach (var socket in sockets)
        {
            try { await SendJsonAsync(socket, package); } catch { }
        }

        DeviceStatus.Text = markPending
            ? $"Пакет переноса отправлен на устройство • профилей: {profiles.Count}"
            : "Связь обновлена на подключённом устройстве";
    }

    private async Task V14ImportFromDeviceAsync(Window owner, bool automatic, string? requestedSourceId = null)
    {
        List<WebSocket> sockets;
        lock (_clients)
            sockets = _clients.Where(x => x.State == WebSocketState.Open).ToList();

        if (sockets.Count == 0)
        {
            if (!automatic)
                MessageBox.Show(owner, "Подключите телефон или планшет к этому ПК по Wi‑Fi.", "NEXO");
            return;
        }

        _v14TransferAwaiter = new TaskCompletionSource<JsonElement>(TaskCreationOptions.RunContinuationsAsynchronously);
        var request = new
        {
            type = "transferPackageRequest",
            sourceServerId = requestedSourceId ?? "",
            automatic
        };

        foreach (var socket in sockets)
        {
            try { await SendJsonAsync(socket, request); } catch { }
        }

        var completed = await Task.WhenAny(_v14TransferAwaiter.Task, Task.Delay(5000));
        if (!ReferenceEquals(completed, _v14TransferAwaiter.Task))
        {
            _v14TransferAwaiter = null;
            if (!automatic)
                MessageBox.Show(owner, "На устройстве нет подходящего пакета переноса или устройство не ответило.", "NEXO");
            return;
        }

        var response = await _v14TransferAwaiter.Task;
        _v14TransferAwaiter = null;
        if (!response.TryGetProperty("workspace", out var workspace) || workspace.ValueKind != JsonValueKind.Object)
        {
            if (!automatic)
                MessageBox.Show(owner, "На устройстве нет подготовленного пакета переноса.", "NEXO");
            return;
        }

        V14ApplyTransferPackage(workspace, replaceExisting: false, automatic: automatic);
    }

    private async Task<bool> V14HandleTransferMessageAsync(JsonElement root, string messageType, string clientId)
    {
        if (messageType == "transferStored")
        {
            await Dispatcher.InvokeAsync(() => DeviceStatus.Text = "Устройство сохранило пакет переноса");
            return true;
        }

        if (messageType == "transferPackageResponse")
        {
            if (_v14TransferAwaiter is not null)
            {
                _v14TransferAwaiter.TrySetResult(root.Clone());
                return true;
            }

            if (_state.DeviceLinkEnabled && _state.DeviceLinkAutoUpdate
                && root.TryGetProperty("workspace", out var autoWorkspace)
                && autoWorkspace.ValueKind == JsonValueKind.Object)
            {
                await Dispatcher.InvokeAsync(() => V14ApplyTransferPackage(autoWorkspace, replaceExisting: false, automatic: true));
                return true;
            }

            return true;
        }

        if (messageType == "applyTransferPackage" && root.TryGetProperty("workspace", out var workspace))
        {
            var firstRun = root.TryGetProperty("firstRun", out var firstRunElement) && firstRunElement.ValueKind == JsonValueKind.True;
            await Dispatcher.InvokeAsync(() => V14ApplyTransferPackage(workspace, replaceExisting: firstRun, automatic: false));
            return true;
        }

        return false;
    }

    private void V14ApplyTransferPackage(JsonElement workspace, bool replaceExisting, bool automatic)
    {
        if (_v14ApplyingTransfer) return;
        _v14ApplyingTransfer = true;
        try
        {
            if (!workspace.TryGetProperty("profiles", out var profilesElement) || profilesElement.ValueKind != JsonValueKind.Array)
                return;

            var imported = JsonSerializer.Deserialize<List<Profile>>(profilesElement.GetRawText(), _json) ?? new List<Profile>();
            if (imported.Count == 0) return;

            var sourceId = workspace.TryGetProperty("sourceServerId", out var sourceIdEl) ? sourceIdEl.GetString() ?? "" : "";
            var sourceName = workspace.TryGetProperty("sourceServerName", out var sourceNameEl) ? sourceNameEl.GetString() ?? "NEXO PC" : "NEXO PC";
            var createLink = workspace.TryGetProperty("createLink", out var linkEl) && linkEl.ValueKind == JsonValueKind.True;
            var includeAllSettings = workspace.TryGetProperty("includeAllSettings", out var settingsEl) && settingsEl.ValueKind == JsonValueKind.True;
            var remoteUpdatedUtc = workspace.TryGetProperty("updatedUtc", out var updatedEl)
                && DateTime.TryParse(updatedEl.GetString(), out var parsedUpdated)
                    ? parsedUpdated.ToUniversalTime()
                    : DateTime.UtcNow;

            if (automatic && remoteUpdatedUtc <= _state.DeviceLinkUpdatedUtc)
                return;

            if (replaceExisting)
                _profiles.Clear();

            var idMap = new Dictionary<string, string>(StringComparer.Ordinal);
            foreach (var incoming in imported)
            {
                incoming.Pages ??= new List<DeckPage>();
                if (incoming.Pages.Count == 0) incoming.Pages.Add(DefaultPage("Страница 1"));
                foreach (var page in incoming.Pages)
                {
                    page.Tiles ??= new List<Tile>();
                    EnsureCapacity(page);
                }

                var oldId = incoming.Id;
                var collision = _profiles.Any(x => string.Equals(x.Id, incoming.Id, StringComparison.Ordinal));
                if (collision && !replaceExisting)
                    incoming.Id = Guid.NewGuid().ToString("N");
                idMap[oldId] = incoming.Id;
            }

            foreach (var incoming in imported)
            {
                foreach (var page in incoming.Pages)
                {
                    foreach (var tile in page.Tiles)
                    {
                        if (tile.ActionType == "profile" && idMap.TryGetValue(tile.ActionValue, out var mapped))
                            tile.ActionValue = mapped;
                    }
                }

                var same = _profiles.FirstOrDefault(x => string.Equals(x.Id, incoming.Id, StringComparison.Ordinal));
                if (same is not null)
                    _profiles.Remove(same);
                V14NormalizeProfileBindings(incoming);
                _profiles.Add(incoming);
            }

            if (includeAllSettings
                && workspace.TryGetProperty("iconLibrary", out var icons)
                && icons.ValueKind == JsonValueKind.Array)
            {
                _state.IconLibrary = JsonSerializer.Deserialize<List<IconAsset>>(icons.GetRawText(), _json) ?? new List<IconAsset>();
            }

            var requestedActive = workspace.TryGetProperty("activeProfileId", out var activeEl) ? activeEl.GetString() ?? "" : "";
            if (idMap.TryGetValue(requestedActive, out var mappedActive))
                requestedActive = mappedActive;
            if (_profiles.Any(x => x.Id == requestedActive))
                _state.ActiveProfileId = requestedActive;
            else if (_profiles.Count > 0 && (replaceExisting || string.IsNullOrWhiteSpace(_state.ActiveProfileId)))
                _state.ActiveProfileId = _profiles[0].Id;

            var incomingDefault = workspace.TryGetProperty("defaultProfileId", out var defaultEl) ? defaultEl.GetString() ?? "" : "";
            if (idMap.TryGetValue(incomingDefault, out var mappedDefault))
                incomingDefault = mappedDefault;
            if (includeAllSettings && _profiles.Any(x => x.Id == incomingDefault))
                _state.DefaultProfileId = incomingDefault;

            if (createLink && !string.IsNullOrWhiteSpace(sourceId))
            {
                _state.DeviceLinkEnabled = true;
                _state.DeviceLinkSourceServerId = sourceId;
                _state.DeviceLinkSourceServerName = sourceName;
                _state.DeviceLinkUpdatedUtc = remoteUpdatedUtc;
            }

            if (replaceExisting)
                _state.SetupCompleted = true;

            SaveState();
            RefreshProfiles();
            _ = BroadcastSnapshotAsync();

            if (replaceExisting && _v13FirstRunWindow is not null)
            {
                _v13AllowWizardClose = true;
                _v13FirstRunWindow.Close();
            }

            DeviceStatus.Text = automatic
                ? $"Связь автоматически обновлена • {sourceName}"
                : $"Импортировано профилей: {imported.Count}";
        }
        finally
        {
            _v14ApplyingTransfer = false;
        }
    }

    private async Task V14OnWorkspaceChangedAsync()
    {
        if (_v14ApplyingTransfer) return;
        if (!_state.DeviceLinkEnabled || !_state.DeviceLinkAutoUpdate) return;
        if (!string.Equals(_state.DeviceLinkSourceServerId, _state.ServerId, StringComparison.Ordinal)) return;

        try
        {
            await V14SendTransferPackageAsync(
                _profiles.ToList(),
                includeAllSettings: true,
                createLink: true,
                markPending: false,
                linkUpdate: true);
        }
        catch { }
    }

    private async Task V14SyncLinkOnClientConnectedAsync(WebSocket socket)
    {
        if (!_state.DeviceLinkEnabled || !_state.DeviceLinkAutoUpdate) return;

        try
        {
            if (string.Equals(_state.DeviceLinkSourceServerId, _state.ServerId, StringComparison.Ordinal))
            {
                await SendJsonAsync(socket, V14TransferPackage(
                    _profiles.ToList(),
                    includeAllSettings: true,
                    createLink: true,
                    markPending: false,
                    linkUpdate: true));
            }
            else if (!string.IsNullOrWhiteSpace(_state.DeviceLinkSourceServerId))
            {
                await SendJsonAsync(socket, new
                {
                    type = "transferPackageRequest",
                    sourceServerId = _state.DeviceLinkSourceServerId,
                    automatic = true
                });
            }
        }
        catch { }
    }
}
