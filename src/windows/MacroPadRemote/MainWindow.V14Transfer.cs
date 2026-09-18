using System;
using System.Collections.Generic;
using System.Linq;
using System.Net.WebSockets;
using System.Text.Json;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

namespace MacroPadRemote;

public sealed class V141TransferCatalogItem
{
    public string ServerId { get; init; } = "";
    public string ServerName { get; init; } = "NEXO PC";
    public DateTime UpdatedUtc { get; init; } = DateTime.MinValue;
    public int ProfileCount { get; init; }

    public string Display =>
        $"{ServerName}   •   {ProfileCount} проф.   •   {(UpdatedUtc == DateTime.MinValue ? "без даты" : UpdatedUtc.ToLocalTime().ToString("dd.MM.yyyy HH:mm"))}";
}

public partial class MainWindow
{
    private TaskCompletionSource<JsonElement>? _v14TransferAwaiter;
    private TaskCompletionSource<JsonElement>? _v141CatalogAwaiter;
    private bool _v14ApplyingTransfer;

    public UIElement V14BuildDevicesTab(Window owner)
    {
        _state.LinkedDevices ??= new List<V141LinkedDevice>();

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
            Text = "Телефон или планшет используется как транспорт для передачи профилей и синхронизации связанных компьютеров. Рабочие профили телефона от этого не изменяются.",
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
            Text = "Можно передать выбранные профили либо весь набор настроек. При импорте NEXO покажет компьютеры, пакеты которых сохранены на телефоне, и предложит выбрать, с каким ПК создать связь.",
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
            Content = "Предлагать создать двустороннюю связь при импорте",
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

            await V14SendTransferPackageAsync(
                selected,
                includeAllSettings: false,
                createLink: createLink.IsChecked == true,
                markPending: true);
        };

        sendAll.Click += async (_, _) =>
        {
            await V14SendTransferPackageAsync(
                _profiles.ToList(),
                includeAllSettings: true,
                createLink: createLink.IsChecked == true,
                markPending: true);
        };

        importDevice.Click += async (_, _) => await V141ChooseImportFromDeviceAsync(owner);

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
        link.Children.Add(new TextBlock
        {
            Text = "Связь двусторонняя: более свежие изменения профилей могут перейти с любого связанного ПК на другой при следующем подключении телефона/планшета.",
            Foreground = (Brush)FindResource("Muted"),
            TextWrapping = TextWrapping.Wrap,
            Margin = new Thickness(0, 6, 0, 10)
        });

        var auto = new CheckBox
        {
            Content = "Автоматически обновлять связи при каждом изменении",
            IsChecked = _state.DeviceLinkAutoUpdate,
            Margin = new Thickness(0, 0, 0, 10)
        };
        link.Children.Add(auto);

        link.Children.Add(new TextBlock
        {
            Text = "Связанные компьютеры",
            FontSize = 14,
            FontWeight = FontWeights.SemiBold,
            Margin = new Thickness(0, 4, 0, 6)
        });

        var linkedRows = new StackPanel();
        link.Children.Add(linkedRows);

        var linkButtons = new WrapPanel { Margin = new Thickness(0, 10, 0, 0) };
        var update = new Button { Content = "Обновить связи", MinWidth = 145, Height = 34, Margin = new Thickness(0, 0, 8, 8) };
        var discover = new Button { Content = "Обновить список связей", MinWidth = 175, Height = 34, Margin = new Thickness(0, 0, 8, 8) };
        linkButtons.Children.Add(update);
        linkButtons.Children.Add(discover);
        link.Children.Add(linkButtons);

        void RebuildLinkedRows()
        {
            linkedRows.Children.Clear();
            var items = (_state.LinkedDevices ?? new List<V141LinkedDevice>())
                .Where(x => !string.Equals(x.ServerId, _state.ServerId, StringComparison.Ordinal))
                .OrderBy(x => x.Name, StringComparer.OrdinalIgnoreCase)
                .ToList();

            if (items.Count == 0)
            {
                linkedRows.Children.Add(new TextBlock
                {
                    Text = "Связанных компьютеров пока нет.",
                    Foreground = (Brush)FindResource("Muted"),
                    Margin = new Thickness(0, 3, 0, 3)
                });
                return;
            }

            foreach (var item in items)
            {
                var row = new Grid { Height = 46, Margin = new Thickness(0, 0, 0, 4) };
                row.ColumnDefinitions.Add(new ColumnDefinition());
                row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(150) });

                var info = new StackPanel { VerticalAlignment = VerticalAlignment.Center };
                info.Children.Add(new TextBlock
                {
                    Text = item.Name,
                    FontWeight = FontWeights.SemiBold
                });
                info.Children.Add(new TextBlock
                {
                    Text = $"{(item.Enabled ? "Связь активна" : "Связь разорвана")} • {V141ShortServerId(item.ServerId)}"
                        + (item.LastSyncUtc == DateTime.MinValue ? "" : $" • {item.LastSyncUtc.ToLocalTime():dd.MM HH:mm}"),
                    Foreground = (Brush)FindResource("Muted"),
                    FontSize = 11
                });
                row.Children.Add(info);

                var toggle = new Button
                {
                    Content = item.Enabled ? "Разорвать связь" : "Восстановить",
                    Height = 30,
                    Margin = new Thickness(8, 6, 0, 6)
                };
                toggle.Click += async (_, _) =>
                {
                    item.Enabled = !item.Enabled;
                    _state.DeviceLinkEnabled = (_state.LinkedDevices ?? new List<V141LinkedDevice>()).Any(x => x.Enabled);
                    SaveState();
                    await V141PublishLinkRelationAsync(item, item.Enabled);
                    RebuildLinkedRows();
                };
                Grid.SetColumn(toggle, 1);
                row.Children.Add(toggle);
                linkedRows.Children.Add(row);
            }
        }

        auto.Checked += async (_, _) =>
        {
            _state.DeviceLinkAutoUpdate = true;
            _state.DeviceLinkEnabled = V141ActiveLinkedDevices().Count > 0;
            SaveState();
            if (_state.DeviceLinkEnabled)
                await V141PushOwnWorkspaceAsync(markPending: false);
        };
        auto.Unchecked += (_, _) =>
        {
            _state.DeviceLinkAutoUpdate = false;
            SaveState();
        };

        update.Click += async (_, _) =>
        {
            await V141RefreshLinksAsync(requestWorkspaces: true);
            RebuildLinkedRows();
        };

        discover.Click += async (_, _) =>
        {
            await V141RefreshLinksAsync(requestWorkspaces: false);
            RebuildLinkedRows();
        };

        RebuildLinkedRows();
        return scroll;
    }

    private static string V141ShortServerId(string value)
        => string.IsNullOrWhiteSpace(value) ? "—" : value[..Math.Min(8, value.Length)];

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
            format = 3,
            transferId = Guid.NewGuid().ToString("N"),
            sourceServerId = _state.ServerId,
            sourceServerName = Environment.MachineName,
            serverName = Environment.MachineName,
            updatedUtc = _state.ProfileWorkspaceUpdatedUtc == DateTime.MinValue
                ? _state.WorkspaceUpdatedUtc
                : _state.ProfileWorkspaceUpdatedUtc,
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

        var package = V14TransferPackage(profiles, includeAllSettings, createLink, markPending, linkUpdate);
        foreach (var socket in sockets)
        {
            try { await SendJsonAsync(socket, package); } catch { }
        }

        DeviceStatus.Text = markPending
            ? $"Пакет переноса отправлен на устройство • профилей: {profiles.Count}"
            : "Свежая версия рабочего пространства передана на устройство";
    }

    private async Task<List<V141TransferCatalogItem>> V141RequestTransferCatalogAsync()
    {
        List<WebSocket> sockets;
        lock (_clients)
            sockets = _clients.Where(x => x.State == WebSocketState.Open).ToList();

        if (sockets.Count == 0)
            return new List<V141TransferCatalogItem>();

        _v141CatalogAwaiter = new TaskCompletionSource<JsonElement>(TaskCreationOptions.RunContinuationsAsynchronously);
        foreach (var socket in sockets)
        {
            try
            {
                await SendJsonAsync(socket, new
                {
                    type = "transferCatalogRequest",
                    requestingServerId = _state.ServerId
                });
            }
            catch { }
        }

        var completed = await Task.WhenAny(_v141CatalogAwaiter.Task, Task.Delay(5000));
        if (!ReferenceEquals(completed, _v141CatalogAwaiter.Task))
        {
            _v141CatalogAwaiter = null;
            return new List<V141TransferCatalogItem>();
        }

        var response = await _v141CatalogAwaiter.Task;
        _v141CatalogAwaiter = null;

        var result = new List<V141TransferCatalogItem>();
        if (!response.TryGetProperty("devices", out var devices) || devices.ValueKind != JsonValueKind.Array)
            return result;

        foreach (var item in devices.EnumerateArray())
        {
            var id = item.TryGetProperty("serverId", out var idEl) ? idEl.GetString() ?? "" : "";
            if (string.IsNullOrWhiteSpace(id) || string.Equals(id, _state.ServerId, StringComparison.Ordinal))
                continue;

            var name = item.TryGetProperty("serverName", out var nameEl) ? nameEl.GetString() ?? "NEXO PC" : "NEXO PC";
            var updated = item.TryGetProperty("updatedUtc", out var updatedEl)
                && DateTime.TryParse(updatedEl.GetString(), out var parsed)
                    ? parsed.ToUniversalTime()
                    : DateTime.MinValue;
            var profileCount = item.TryGetProperty("profileCount", out var countEl) && countEl.TryGetInt32(out var count)
                ? count
                : 0;

            result.Add(new V141TransferCatalogItem
            {
                ServerId = id,
                ServerName = name,
                UpdatedUtc = updated,
                ProfileCount = profileCount
            });
        }

        return result.OrderByDescending(x => x.UpdatedUtc).ToList();
    }

    private async Task V141ChooseImportFromDeviceAsync(Window owner)
    {
        var catalog = await V141RequestTransferCatalogAsync();
        if (catalog.Count == 0)
        {
            MessageBox.Show(owner, "На подключённом устройстве нет пакетов от других компьютеров.", "NEXO");
            return;
        }

        var dialog = new Window
        {
            Owner = owner,
            Title = "Импортировать с устройства",
            Width = 610,
            Height = 460,
            MinWidth = 560,
            MinHeight = 400,
            WindowStartupLocation = WindowStartupLocation.CenterOwner,
            Background = (Brush)FindResource("Bg")
        };

        var root = new Grid { Margin = new Thickness(18) };
        root.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        root.RowDefinitions.Add(new RowDefinition());
        root.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        root.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });

        root.Children.Add(new TextBlock
        {
            Text = "Выберите компьютер, с которого нужно импортировать профили и настройки",
            FontSize = 17,
            FontWeight = FontWeights.SemiBold,
            TextWrapping = TextWrapping.Wrap,
            Margin = new Thickness(0, 0, 0, 12)
        });

        var list = new ListBox
        {
            ItemsSource = catalog,
            DisplayMemberPath = nameof(V141TransferCatalogItem.Display),
            Margin = new Thickness(0, 44, 0, 10)
        };
        Grid.SetRow(list, 1);
        root.Children.Add(list);

        var link = new CheckBox
        {
            Content = "Создать двустороннюю связь с выбранным компьютером",
            IsChecked = true,
            Margin = new Thickness(0, 8, 0, 10)
        };
        Grid.SetRow(link, 2);
        root.Children.Add(link);

        var buttons = new StackPanel
        {
            Orientation = Orientation.Horizontal,
            HorizontalAlignment = HorizontalAlignment.Right
        };
        var cancel = new Button { Content = "Отмена", Width = 100, Height = 34, Margin = new Thickness(0, 0, 8, 0) };
        var import = new Button { Content = "Импортировать", Width = 130, Height = 34, IsDefault = true };
        buttons.Children.Add(cancel);
        buttons.Children.Add(import);
        Grid.SetRow(buttons, 3);
        root.Children.Add(buttons);

        cancel.Click += (_, _) => dialog.Close();
        import.Click += async (_, _) =>
        {
            if (list.SelectedItem is not V141TransferCatalogItem selected)
            {
                MessageBox.Show(dialog, "Выберите компьютер.", "NEXO");
                return;
            }

            dialog.IsEnabled = false;
            await V14ImportFromDeviceAsync(
                owner,
                automatic: false,
                requestedSourceId: selected.ServerId,
                createBidirectionalLink: link.IsChecked == true);
            dialog.Close();
        };

        list.SelectedIndex = 0;
        dialog.Content = root;
        dialog.ShowDialog();
    }

    private async Task V14ImportFromDeviceAsync(
        Window owner,
        bool automatic,
        string? requestedSourceId = null,
        bool createBidirectionalLink = false)
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

        V14ApplyTransferPackage(
            workspace,
            replaceExisting: automatic,
            automatic: automatic,
            createBidirectionalLink: createBidirectionalLink);
    }

    private async Task<bool> V14HandleTransferMessageAsync(JsonElement root, string messageType, string clientId)
    {
        if (messageType == "transferStored")
        {
            await Dispatcher.InvokeAsync(() => DeviceStatus.Text = "Устройство сохранило пакет переноса");
            return true;
        }

        if (messageType == "transferCatalogResponse")
        {
            _v141CatalogAwaiter?.TrySetResult(root.Clone());
            return true;
        }

        if (messageType == "linkPeersResponse")
        {
            var pending = await Dispatcher.InvokeAsync(() => V141ApplyLinkPeersResponseAsync(root));
            await pending;
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
                await Dispatcher.InvokeAsync(() =>
                    V14ApplyTransferPackage(autoWorkspace, replaceExisting: true, automatic: true, createBidirectionalLink: true));
                return true;
            }

            return true;
        }

        if (messageType == "applyTransferPackage" && root.TryGetProperty("workspace", out var workspace))
        {
            var firstRun = root.TryGetProperty("firstRun", out var firstRunElement) && firstRunElement.ValueKind == JsonValueKind.True;
            var createLink = workspace.TryGetProperty("createLink", out var createLinkEl) && createLinkEl.ValueKind == JsonValueKind.True;
            await Dispatcher.InvokeAsync(() =>
                V14ApplyTransferPackage(workspace, replaceExisting: firstRun, automatic: false, createBidirectionalLink: createLink));
            return true;
        }

        return false;
    }

    private void V14ApplyTransferPackage(
        JsonElement workspace,
        bool replaceExisting,
        bool automatic,
        bool createBidirectionalLink = false)
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
            var packageWantsLink = workspace.TryGetProperty("createLink", out var linkEl) && linkEl.ValueKind == JsonValueKind.True;
            var includeAllSettings = workspace.TryGetProperty("includeAllSettings", out var settingsEl) && settingsEl.ValueKind == JsonValueKind.True;
            var remoteUpdatedUtc = workspace.TryGetProperty("updatedUtc", out var updatedEl)
                && DateTime.TryParse(updatedEl.GetString(), out var parsedUpdated)
                    ? parsedUpdated.ToUniversalTime()
                    : DateTime.UtcNow;

            V141LinkedDevice? peer = null;
            if (!string.IsNullOrWhiteSpace(sourceId) && !string.Equals(sourceId, _state.ServerId, StringComparison.Ordinal))
            {
                peer = (_state.LinkedDevices ?? new List<V141LinkedDevice>())
                    .FirstOrDefault(x => string.Equals(x.ServerId, sourceId, StringComparison.Ordinal));

                if (peer is null && (createBidirectionalLink || packageWantsLink))
                    peer = V141UpsertLinkedDevice(sourceId, sourceName);
                else if (peer is not null && !string.IsNullOrWhiteSpace(sourceName))
                    peer.Name = sourceName;
            }

            if (automatic)
            {
                if (peer is null || !peer.Enabled) return;
                if (remoteUpdatedUtc <= peer.LastRemoteUpdateUtc) return;
                var localProfileRevision = _state.ProfileWorkspaceUpdatedUtc == DateTime.MinValue
                    ? _state.WorkspaceUpdatedUtc
                    : _state.ProfileWorkspaceUpdatedUtc;
                if (remoteUpdatedUtc <= localProfileRevision) return;
            }

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
                var existing = _profiles.FirstOrDefault(x => string.Equals(x.Id, incoming.Id, StringComparison.Ordinal));
                if (existing is not null && !automatic && !replaceExisting)
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

            if (peer is not null)
            {
                peer.LastRemoteUpdateUtc = remoteUpdatedUtc;
                peer.LastSyncUtc = DateTime.UtcNow;
                if (createBidirectionalLink || packageWantsLink)
                {
                    peer.Enabled = true;
                    _state.DeviceLinkEnabled = true;
                }
            }

            if (replaceExisting)
                _state.SetupCompleted = true;

            SaveState();
            RefreshProfiles();
            _ = BroadcastSnapshotAsync();

            if (peer is not null && (createBidirectionalLink || packageWantsLink))
                _ = V141PublishLinkRelationAsync(peer, enabled: true);

            if (replaceExisting && _v13FirstRunWindow is not null)
            {
                _v13AllowWizardClose = true;
                _v13FirstRunWindow.Close();
            }

            DeviceStatus.Text = automatic
                ? $"Связь обновлена • {sourceName}"
                : $"Импортировано профилей: {imported.Count}";
        }
        finally
        {
            _v14ApplyingTransfer = false;
        }
    }

    private async Task V141PublishLinkRelationAsync(V141LinkedDevice peer, bool enabled)
    {
        List<WebSocket> sockets;
        lock (_clients)
            sockets = _clients.Where(x => x.State == WebSocketState.Open).ToList();

        foreach (var socket in sockets)
        {
            try
            {
                await SendJsonAsync(socket, new
                {
                    type = "linkRelationUpdate",
                    aServerId = _state.ServerId,
                    aServerName = Environment.MachineName,
                    bServerId = peer.ServerId,
                    bServerName = peer.Name,
                    enabled
                });
            }
            catch { }
        }

        if (enabled)
            await V141PushOwnWorkspaceAsync(markPending: false);
    }

    private async Task V141PushOwnWorkspaceAsync(bool markPending)
    {
        List<WebSocket> sockets;
        lock (_clients)
            sockets = _clients.Where(x => x.State == WebSocketState.Open).ToList();
        if (sockets.Count == 0) return;

        var package = V14TransferPackage(
            _profiles.ToList(),
            includeAllSettings: true,
            createLink: false,
            markPending: markPending,
            linkUpdate: true);

        foreach (var socket in sockets)
        {
            try { await SendJsonAsync(socket, package); } catch { }
        }
    }

    private async Task V141RefreshLinksAsync(bool requestWorkspaces)
    {
        List<WebSocket> sockets;
        lock (_clients)
            sockets = _clients.Where(x => x.State == WebSocketState.Open).ToList();

        if (sockets.Count == 0)
        {
            MessageBox.Show(this, "Подключите телефон или планшет к этому ПК по Wi‑Fi.", "NEXO");
            return;
        }

        foreach (var socket in sockets)
        {
            try
            {
                await SendJsonAsync(socket, new
                {
                    type = "linkPeersRequest",
                    serverId = _state.ServerId,
                    requestWorkspaces
                });
            }
            catch { }
        }

        if (_state.DeviceLinkAutoUpdate || requestWorkspaces)
            await V141PushOwnWorkspaceAsync(markPending: false);
    }

    private async Task V141ApplyLinkPeersResponseAsync(JsonElement root)
    {
        if (!root.TryGetProperty("peers", out var peers) || peers.ValueKind != JsonValueKind.Array)
            return;

        _state.LinkedDevices ??= new List<V141LinkedDevice>();
        var receivedIds = new HashSet<string>(StringComparer.Ordinal);

        foreach (var peerElement in peers.EnumerateArray())
        {
            var id = peerElement.TryGetProperty("serverId", out var idEl) ? idEl.GetString() ?? "" : "";
            if (string.IsNullOrWhiteSpace(id) || string.Equals(id, _state.ServerId, StringComparison.Ordinal))
                continue;

            var name = peerElement.TryGetProperty("serverName", out var nameEl) ? nameEl.GetString() ?? "NEXO PC" : "NEXO PC";
            receivedIds.Add(id);
            var peer = V141UpsertLinkedDevice(id, name);
            peer.Enabled = true;
        }

        foreach (var known in _state.LinkedDevices.Where(x => !string.Equals(x.ServerId, _state.ServerId, StringComparison.Ordinal)))
        {
            if (!receivedIds.Contains(known.ServerId))
                known.Enabled = false;
        }

        _state.DeviceLinkEnabled = _state.LinkedDevices.Any(x => x.Enabled);
        var oldApplying = _v14ApplyingTransfer;
        _v14ApplyingTransfer = true;
        try { SaveState(); }
        finally { _v14ApplyingTransfer = oldApplying; }

        var manualWorkspaceRefresh = root.TryGetProperty("requestWorkspaces", out var requestEl)
            && requestEl.ValueKind == JsonValueKind.True;

        if (_state.DeviceLinkAutoUpdate || manualWorkspaceRefresh)
        {
            List<WebSocket> sockets;
            lock (_clients)
                sockets = _clients.Where(x => x.State == WebSocketState.Open).ToList();

            foreach (var peer in V141ActiveLinkedDevices())
            {
                foreach (var socket in sockets)
                {
                    try
                    {
                        await SendJsonAsync(socket, new
                        {
                            type = "transferPackageRequest",
                            sourceServerId = peer.ServerId,
                            automatic = true
                        });
                    }
                    catch { }
                }
            }
        }
    }

    private async Task V14OnWorkspaceChangedAsync()
    {
        if (_v14ApplyingTransfer) return;
        if (!_state.DeviceLinkEnabled || !_state.DeviceLinkAutoUpdate) return;
        if (V141ActiveLinkedDevices().Count == 0) return;

        try
        {
            await V141PushOwnWorkspaceAsync(markPending: false);
        }
        catch { }
    }

    private async Task V14SyncLinkOnClientConnectedAsync(WebSocket socket)
    {
        try
        {
            await SendJsonAsync(socket, new
            {
                type = "linkPeersRequest",
                serverId = _state.ServerId,
                requestWorkspaces = _state.DeviceLinkAutoUpdate
            });

            if (!_state.DeviceLinkEnabled || !_state.DeviceLinkAutoUpdate)
                return;

            await SendJsonAsync(socket, V14TransferPackage(
                _profiles.ToList(),
                includeAllSettings: true,
                createLink: false,
                markPending: false,
                linkUpdate: true));

            foreach (var peer in V141ActiveLinkedDevices())
            {
                await SendJsonAsync(socket, new
                {
                    type = "transferPackageRequest",
                    sourceServerId = peer.ServerId,
                    automatic = true
                });
            }
        }
        catch { }
    }
}
