using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

namespace MacroPadRemote;

public partial class MainWindow
{
    private string V14ProfilesDirectory => Path.Combine(AppContext.BaseDirectory, "Profiles");

    private List<Profile> V14LoadProfilesFromProgramFolder(List<Profile>? legacyProfiles)
    {
        var legacy = legacyProfiles ?? new List<Profile>();

        try
        {
            Directory.CreateDirectory(V14ProfilesDirectory);
            var loaded = new List<Profile>();

            foreach (var file in Directory.EnumerateFiles(V14ProfilesDirectory, "*.nexo-profile", SearchOption.TopDirectoryOnly)
                         .OrderBy(x => x, StringComparer.OrdinalIgnoreCase))
            {
                try
                {
                    var profile = JsonSerializer.Deserialize<Profile>(File.ReadAllText(file), _json);
                    if (profile is null) continue;
                    V14NormalizeProfileBindings(profile);
                    loaded.Add(profile);
                }
                catch
                {
                    // A damaged profile file must not prevent NEXO from starting.
                }
            }

            if (loaded.Count > 0)
                return loaded;
        }
        catch
        {
            // If the program folder is temporarily unavailable, fall back to
            // the legacy in-memory profiles rather than losing the workspace.
        }

        return legacy;
    }

    private void V14PersistProfilesToProgramFolder()
    {
        Directory.CreateDirectory(V14ProfilesDirectory);

        var expected = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var profile in _profiles)
        {
            var safeName = V14SafeFileName(profile.Name);
            if (safeName.Length > 72) safeName = safeName[..72];
            var fileName = $"{safeName}__{profile.Id}.nexo-profile";
            var path = Path.Combine(V14ProfilesDirectory, fileName);
            var temp = path + ".tmp";

            File.WriteAllText(temp, JsonSerializer.Serialize(profile, _json));
            File.Move(temp, path, true);
            expected.Add(Path.GetFullPath(path));
        }

        foreach (var file in Directory.EnumerateFiles(V14ProfilesDirectory, "*.nexo-profile", SearchOption.TopDirectoryOnly))
        {
            var full = Path.GetFullPath(file);
            if (expected.Contains(full)) continue;
            try { File.Delete(file); } catch { }
        }
    }

    private string V14SerializeStateWithoutProfiles()
    {
        var json = JsonSerializer.Serialize(_state, _json);
        using var document = JsonDocument.Parse(json);
        using var stream = new MemoryStream();
        using (var writer = new Utf8JsonWriter(stream, new JsonWriterOptions { Indented = true }))
        {
            writer.WriteStartObject();
            foreach (var property in document.RootElement.EnumerateObject())
            {
                if (string.Equals(property.Name, "profiles", StringComparison.OrdinalIgnoreCase))
                    continue;
                property.WriteTo(writer);
            }
            writer.WriteEndObject();
        }

        return System.Text.Encoding.UTF8.GetString(stream.ToArray());
    }

    public void V14OpenSettingsWindow()
    {
        foreach (var profile in _profiles)
            V14NormalizeProfileBindings(profile);

        var win = new Window
        {
            Owner = this,
            Title = "Настройка",
            Width = 920,
            Height = 650,
            MinWidth = 800,
            MinHeight = 560,
            WindowStartupLocation = WindowStartupLocation.CenterOwner,
            Background = (Brush)FindResource("Bg")
        };

        var tabs = new TabControl { Margin = new Thickness(0) };
        tabs.Items.Add(new TabItem { Header = "Общее", Content = V14BuildGeneralTab(win) });
        tabs.Items.Add(new TabItem { Header = "Оборудование", Content = V14BuildHardwareTab(win) });
        tabs.Items.Add(new TabItem { Header = "Профили", Content = V14BuildProfilesTab(win) });
        tabs.Items.Add(new TabItem { Header = "Устройства", Content = V14BuildDevicesTab(win) });
        tabs.SelectedIndex = 2;
        win.Content = tabs;
        win.ShowDialog();
    }

    private UIElement V14BuildGeneralTab(Window owner)
    {
        var root = new StackPanel { Margin = new Thickness(22) };
        root.Children.Add(new TextBlock
        {
            Text = "Общие настройки NEXO",
            FontSize = 21,
            FontWeight = FontWeights.SemiBold
        });
        root.Children.Add(new TextBlock
        {
            Text = "Настройки профилей перенесены в отдельную вкладку «Профили». Основное окно теперь используется только для редактирования рабочего поля и действий.",
            Foreground = (Brush)FindResource("Muted"),
            TextWrapping = TextWrapping.Wrap,
            Margin = new Thickness(0, 9, 0, 0)
        });
        return root;
    }

    private UIElement V14BuildHardwareTab(Window owner)
    {
        var root = new StackPanel { Margin = new Thickness(22) };
        root.Children.Add(new TextBlock
        {
            Text = "Подключение и оборудование",
            FontSize = 21,
            FontWeight = FontWeights.SemiBold
        });

        var combo = new ComboBox
        {
            Height = 34,
            Margin = new Thickness(0, 14, 0, 8),
            ItemsSource = new[] { "Wi‑Fi", "Bluetooth LE" },
            SelectedIndex = SelectedTransport() == "Bluetooth" ? 1 : 0
        };
        root.Children.Add(combo);

        var qr = new Button
        {
            Content = "Показать QR-код",
            Width = 180,
            Height = 34,
            HorizontalAlignment = HorizontalAlignment.Left,
            Margin = new Thickness(0, 0, 0, 14)
        };
        qr.Click += ShowQr_Click;
        root.Children.Add(qr);

        var visibleToggle = new CheckBox
        {
            Content = "Показывать этот ПК в локальной сети",
            IsChecked = _state.Discoverable,
            Margin = new Thickness(0, 3, 0, 5)
        };
        var onlineToggle = new CheckBox
        {
            Content = "Разрешить подключения к этому ПК",
            IsChecked = _state.AcceptConnections,
            Margin = new Thickness(0, 3, 0, 14)
        };
        visibleToggle.Checked += async (_, _) => await SetLanDiscoverableAsync(true);
        visibleToggle.Unchecked += async (_, _) => await SetLanDiscoverableAsync(false);
        onlineToggle.Checked += async (_, _) => await SetConnectionsEnabledAsync(true);
        onlineToggle.Unchecked += async (_, _) => await SetConnectionsEnabledAsync(false);
        root.Children.Add(visibleToggle);
        root.Children.Add(onlineToggle);

        root.Children.Add(new TextBlock
        {
            Text = "Привязанные устройства",
            FontSize = 16,
            FontWeight = FontWeights.SemiBold,
            Margin = new Thickness(0, 6, 0, 7)
        });

        foreach (var d in _state.TrustedDevices.OrderByDescending(x => x.LastSeenUtc))
        {
            var row = new Grid { Height = 42, Margin = new Thickness(0, 0, 0, 3) };
            row.ColumnDefinitions.Add(new ColumnDefinition());
            row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(44) });
            row.Children.Add(new TextBlock
            {
                Text = $"{d.Name}   •   {d.Transport}",
                VerticalAlignment = VerticalAlignment.Center
            });
            var more = new Button { Content = "⋮", Tag = d };
            more.Click += TrustedDeviceMenu_Click;
            Grid.SetColumn(more, 1);
            row.Children.Add(more);
            root.Children.Add(row);
        }

        combo.SelectionChanged += async (_, _) =>
        {
            await StopAllTransportsAsync();
            _state.Transport = combo.SelectedIndex == 1 ? "Bluetooth" : "Wifi";
            ApplyTransport();
            SaveState();
            await StartSelectedTransportAsync();
        };

        return new ScrollViewer { Content = root, VerticalScrollBarVisibility = ScrollBarVisibility.Auto };
    }

    private UIElement V14BuildProfilesTab(Window owner)
    {
        var root = new Grid { Margin = new Thickness(18) };
        root.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(290) });
        root.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(18) });
        root.ColumnDefinitions.Add(new ColumnDefinition());

        var left = new Grid();
        left.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        left.RowDefinitions.Add(new RowDefinition());
        left.RowDefinitions.Add(new RowDefinition { Height = new GridLength(46) });

        left.Children.Add(new TextBlock
        {
            Text = "Профили",
            FontSize = 18,
            FontWeight = FontWeights.SemiBold,
            Margin = new Thickness(8, 4, 8, 12)
        });

        var list = new ListBox
        {
            Margin = new Thickness(0, 42, 0, 0),
            ItemsSource = _profiles,
            DisplayMemberPath = nameof(Profile.Name)
        };
        Grid.SetRow(list, 1);
        left.Children.Add(list);

        var actions = new Grid { Margin = new Thickness(0, 7, 0, 0) };
        actions.ColumnDefinitions.Add(new ColumnDefinition());
        actions.ColumnDefinitions.Add(new ColumnDefinition());
        actions.ColumnDefinitions.Add(new ColumnDefinition());

        var rename = new Button { Content = "Переименовать", Margin = new Thickness(0, 0, 4, 0) };
        var import = new Button { Content = "Импортировать", Margin = new Thickness(2, 0, 2, 0) };
        var export = new Button { Content = "Экспортировать", Margin = new Thickness(4, 0, 0, 0) };
        actions.Children.Add(rename);
        Grid.SetColumn(import, 1);
        actions.Children.Add(import);
        Grid.SetColumn(export, 2);
        actions.Children.Add(export);
        Grid.SetRow(actions, 2);
        left.Children.Add(actions);

        var right = new Grid
        {
            Background = (Brush)FindResource("Panel"),
            Margin = new Thickness(0),
        };
        right.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        right.RowDefinitions.Add(new RowDefinition());

        var rightHeader = new TextBlock
        {
            Text = "Настройки профиля",
            FontSize = 18,
            FontWeight = FontWeights.SemiBold,
            Margin = new Thickness(18, 17, 18, 10)
        };
        right.Children.Add(rightHeader);

        var form = new StackPanel { Margin = new Thickness(18, 60, 18, 18) };
        var hint = new TextBlock
        {
            Text = "Когда окно указанного приложения находится на переднем плане, NEXO автоматически переключается на этот профиль. Можно назначить до трёх приложений.",
            Foreground = (Brush)FindResource("Muted"),
            TextWrapping = TextWrapping.Wrap,
            Margin = new Thickness(0, 0, 0, 18)
        };
        form.Children.Add(hint);

        var apps = V141RunningApplications();
        ComboBox AppCombo(string label)
        {
            var row = new Grid { Margin = new Thickness(0, 0, 0, 8) };
            row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(110) });
            row.ColumnDefinitions.Add(new ColumnDefinition());
            row.Children.Add(new TextBlock
            {
                Text = label,
                VerticalAlignment = VerticalAlignment.Center,
                Foreground = (Brush)FindResource("Muted")
            });
            var combo = V141ApplicationCombo(apps);
            Grid.SetColumn(combo, 1);
            row.Children.Add(combo);
            form.Children.Add(row);
            return combo;
        }

        var app1 = AppCombo("Приложение 1:");
        var app2 = AppCombo("Приложение 2:");
        var app3 = AppCombo("Приложение 3:");

        var defaultCheck = new CheckBox
        {
            Content = "Установить этот профиль как профиль по умолчанию",
            Margin = new Thickness(0, 18, 0, 8)
        };
        form.Children.Add(defaultCheck);

        var defaultHint = new TextBlock
        {
            Text = "Этот профиль будет отображаться, если для активного приложения не назначен другой профиль.",
            Foreground = (Brush)FindResource("Muted"),
            TextWrapping = TextWrapping.Wrap,
            Margin = new Thickness(0, 4, 0, 16)
        };
        form.Children.Add(defaultHint);

        var descriptionLabel = new TextBlock
        {
            Text = "Описание",
            Foreground = (Brush)FindResource("Muted"),
            Margin = new Thickness(0, 5, 0, 4)
        };
        form.Children.Add(descriptionLabel);
        var description = new TextBox { Height = 66, AcceptsReturn = true, TextWrapping = TextWrapping.Wrap };
        form.Children.Add(description);

        var iconButton = new Button
        {
            Content = "Изменить иконку профиля…",
            Width = 190,
            Height = 32,
            HorizontalAlignment = HorizontalAlignment.Left,
            Margin = new Thickness(0, 12, 0, 0)
        };
        form.Children.Add(iconButton);

        Grid.SetRow(form, 1);
        right.Children.Add(form);

        Grid.SetColumn(right, 2);
        root.Children.Add(left);
        root.Children.Add(right);

        Profile? current = null;
        bool loading = false;

        void LoadSelected(Profile? profile)
        {
            current = profile;
            loading = true;
            var bindings = profile is null ? new List<string>() : V14Bindings(profile);
            app1.Text = bindings.ElementAtOrDefault(0) ?? "";
            app2.Text = bindings.ElementAtOrDefault(1) ?? "";
            app3.Text = bindings.ElementAtOrDefault(2) ?? "";
            defaultCheck.IsChecked = profile is not null && string.Equals(_state.DefaultProfileId, profile.Id, StringComparison.Ordinal);
            description.Text = profile?.Description ?? "";
            rightHeader.Text = profile is null ? "Настройки профиля" : profile.Name;
            loading = false;
        }

        void SaveSelected()
        {
            if (loading || current is null) return;
            current.BoundApplications = new[] { app1.Text, app2.Text, app3.Text }
                .Select(V14NormalizeExeName)
                .Where(x => !string.IsNullOrWhiteSpace(x))
                .Distinct(StringComparer.OrdinalIgnoreCase)
                .Take(3)
                .ToList();
            current.BoundApplication = current.BoundApplications.FirstOrDefault() ?? "";
            current.Description = description.Text;
            _state.DefaultProfileId = defaultCheck.IsChecked == true ? current.Id
                : string.Equals(_state.DefaultProfileId, current.Id, StringComparison.Ordinal) ? "" : _state.DefaultProfileId;
            SaveState();
            RefreshProfiles();
            _ = BroadcastSnapshotAsync();
        }

        app1.LostKeyboardFocus += (_, _) => SaveSelected();
        app2.LostKeyboardFocus += (_, _) => SaveSelected();
        app3.LostKeyboardFocus += (_, _) => SaveSelected();
        description.LostKeyboardFocus += (_, _) => SaveSelected();
        defaultCheck.Checked += (_, _) =>
        {
            if (loading || current is null) return;
            _state.DefaultProfileId = current.Id;
            SaveState();
            _ = BroadcastSnapshotAsync();
        };
        defaultCheck.Unchecked += (_, _) =>
        {
            if (loading || current is null) return;
            if (string.Equals(_state.DefaultProfileId, current.Id, StringComparison.Ordinal))
            {
                _state.DefaultProfileId = "";
                SaveState();
            }
        };

        list.SelectionChanged += (_, _) => LoadSelected(list.SelectedItem as Profile);

        rename.Click += (_, _) =>
        {
            if (list.SelectedItem is not Profile p) return;
            var value = Prompt("Переименовать профиль", p.Name);
            if (string.IsNullOrWhiteSpace(value)) return;
            p.Name = value.Trim();
            SaveState();
            RefreshProfiles();
            list.Items.Refresh();
            rightHeader.Text = p.Name;
            _ = BroadcastSnapshotAsync();
        };

        iconButton.Click += (_, _) =>
        {
            if (current is null) return;
            ShowProfileIconPicker(current);
            list.Items.Refresh();
        };

        import.Click += (_, _) => V14ShowImportMenu(import, list);
        export.Click += (_, _) => V14ShowExportMenu(export, list.SelectedItem as Profile);

        var context = new ContextMenu();
        var create = new MenuItem { Header = "Создать новый профиль" };
        create.Click += (_, _) =>
        {
            var name = V141PromptNewProfileName(owner);
            if (name is null) return;
            var p = EmptyProfile(name, name[..1].ToUpperInvariant());
            _profiles.Add(p);
            _state.ActiveProfileId = p.Id;
            SaveState();
            RefreshProfiles();
            list.Items.Refresh();
            list.SelectedItem = p;
            _ = BroadcastSnapshotAsync();
        };
        var duplicate = new MenuItem { Header = "Дублировать профиль" };
        duplicate.Click += (_, _) =>
        {
            if (list.SelectedItem is not Profile p) return;
            var clone = V14CloneImportedProfile(p);
            clone.Name = p.Name + " copy";
            _profiles.Add(clone);
            SaveState();
            RefreshProfiles();
            list.Items.Refresh();
            list.SelectedItem = clone;
            _ = BroadcastSnapshotAsync();
        };
        var delete = new MenuItem { Header = "Удалить профиль" };
        delete.Click += (_, _) =>
        {
            if (list.SelectedItem is not Profile p || _profiles.Count <= 1) return;
            if (MessageBox.Show(owner, $"Удалить профиль «{p.Name}»?", "NEXO", MessageBoxButton.YesNo, MessageBoxImage.Question) != MessageBoxResult.Yes) return;
            _profiles.Remove(p);
            if (string.Equals(_state.DefaultProfileId, p.Id, StringComparison.Ordinal)) _state.DefaultProfileId = "";
            if (string.Equals(_state.ActiveProfileId, p.Id, StringComparison.Ordinal)) _state.ActiveProfileId = _profiles[0].Id;
            SaveState();
            RefreshProfiles();
            list.Items.Refresh();
            list.SelectedItem = _profile;
            _ = BroadcastSnapshotAsync();
        };
        context.Items.Add(create);
        context.Items.Add(duplicate);
        context.Items.Add(new Separator());
        context.Items.Add(delete);
        list.ContextMenu = context;

        list.SelectedItem = _profiles.FirstOrDefault(x => x.Id == _state.ActiveProfileId) ?? _profiles.FirstOrDefault();
        LoadSelected(list.SelectedItem as Profile);
        return root;
    }

    private static List<string> V14RunningApplications()
    {
        try
        {
            return Process.GetProcesses()
                .Select(p =>
                {
                    try { return V14NormalizeExeName(p.ProcessName); }
                    catch { return ""; }
                })
                .Where(x => !string.IsNullOrWhiteSpace(x))
                .Distinct(StringComparer.OrdinalIgnoreCase)
                .OrderBy(x => x, StringComparer.OrdinalIgnoreCase)
                .Prepend("Нет")
                .ToList();
        }
        catch
        {
            return new List<string> { "Нет" };
        }
    }

    private static string V14NormalizeExeName(string? value)
    {
        var text = (value ?? "").Trim();
        if (string.Equals(text, "Нет", StringComparison.OrdinalIgnoreCase)) return "";
        if (text.Length == 0) return "";
        text = Path.GetFileName(text);
        return text.EndsWith(".exe", StringComparison.OrdinalIgnoreCase) ? text : text + ".exe";
    }

    private static void V14NormalizeProfileBindings(Profile profile)
    {
        profile.BoundApplications ??= new List<string>();
        if (profile.BoundApplications.Count == 0 && !string.IsNullOrWhiteSpace(profile.BoundApplication))
            profile.BoundApplications.Add(V14NormalizeExeName(profile.BoundApplication));
        profile.BoundApplications = profile.BoundApplications
            .Select(V14NormalizeExeName)
            .Where(x => !string.IsNullOrWhiteSpace(x))
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .Take(3)
            .ToList();
        profile.BoundApplication = profile.BoundApplications.FirstOrDefault() ?? "";
    }

    private static List<string> V14Bindings(Profile profile)
    {
        V14NormalizeProfileBindings(profile);
        return profile.BoundApplications.ToList();
    }

    private void V14ShowImportMenu(Button target, ListBox list)
    {
        var menu = new ContextMenu();
        var folder = new MenuItem { Header = "Импортировать папку" };
        folder.Click += (_, _) =>
        {
            using var dialog = new System.Windows.Forms.FolderBrowserDialog
            {
                Description = "Выберите папку с профилями NEXO"
            };
            if (dialog.ShowDialog() != System.Windows.Forms.DialogResult.OK) return;
            var files = Directory.EnumerateFiles(dialog.SelectedPath, "*.nexo-profile", SearchOption.TopDirectoryOnly).ToArray();
            V14ImportProfileFiles(files, list);
        };

        var filesItem = new MenuItem { Header = "Импортировать один или несколько профилей" };
        filesItem.Click += (_, _) =>
        {
            var dialog = new Microsoft.Win32.OpenFileDialog
            {
                Title = "Импорт профилей NEXO",
                Filter = "Профиль NEXO (*.nexo-profile)|*.nexo-profile|JSON (*.json)|*.json",
                Multiselect = true
            };
            if (dialog.ShowDialog(this) != true) return;
            V14ImportProfileFiles(dialog.FileNames, list);
        };
        menu.Items.Add(folder);
        menu.Items.Add(filesItem);
        target.ContextMenu = menu;
        menu.PlacementTarget = target;
        menu.IsOpen = true;
    }

    private void V14ShowExportMenu(Button target, Profile? selected)
    {
        var menu = new ContextMenu();
        var all = new MenuItem { Header = "Экспортировать все профили" };
        all.Click += (_, _) =>
        {
            using var dialog = new System.Windows.Forms.FolderBrowserDialog
            {
                Description = "Папка для экспорта профилей NEXO"
            };
            if (dialog.ShowDialog() != System.Windows.Forms.DialogResult.OK) return;
            foreach (var profile in _profiles)
            {
                var file = Path.Combine(dialog.SelectedPath, V14SafeFileName(profile.Name) + ".nexo-profile");
                V14WriteProfile(file, profile);
            }
            DeviceStatus.Text = $"Экспортировано профилей: {_profiles.Count}";
        };

        var one = new MenuItem { Header = "Экспортировать выбранный профиль", IsEnabled = selected is not null };
        one.Click += (_, _) =>
        {
            if (selected is null) return;
            var dialog = new Microsoft.Win32.SaveFileDialog
            {
                Title = "Экспорт профиля NEXO",
                Filter = "Профиль NEXO (*.nexo-profile)|*.nexo-profile",
                FileName = V14SafeFileName(selected.Name) + ".nexo-profile"
            };
            if (dialog.ShowDialog(this) != true) return;
            V14WriteProfile(dialog.FileName, selected);
            DeviceStatus.Text = $"Профиль «{selected.Name}» экспортирован";
        };

        menu.Items.Add(all);
        menu.Items.Add(one);
        target.ContextMenu = menu;
        menu.PlacementTarget = target;
        menu.IsOpen = true;
    }

    private void V14ImportProfileFiles(IEnumerable<string> files, ListBox list)
    {
        var imported = new List<Profile>();
        foreach (var file in files)
        {
            try
            {
                var raw = File.ReadAllText(file);
                var profile = JsonSerializer.Deserialize<Profile>(raw, _json);
                if (profile is null) continue;
                profile = V14CloneImportedProfile(profile);
                _profiles.Add(profile);
                imported.Add(profile);
            }
            catch
            {
                // Invalid files are skipped so one broken profile does not cancel a batch.
            }
        }

        if (imported.Count == 0)
        {
            MessageBox.Show(this, "Не найдено корректных профилей NEXO.", "NEXO");
            return;
        }

        _state.ActiveProfileId = imported[0].Id;
        SaveState();
        RefreshProfiles();
        list.Items.Refresh();
        list.SelectedItem = imported[0];
        _ = BroadcastSnapshotAsync();
        DeviceStatus.Text = $"Импортировано профилей: {imported.Count}";
    }

    private void V14WriteProfile(string path, Profile profile)
    {
        var json = JsonSerializer.Serialize(profile, _json);
        File.WriteAllText(path, json);
    }

    private Profile V14CloneImportedProfile(Profile source)
    {
        var raw = JsonSerializer.Serialize(source, _json);
        var clone = JsonSerializer.Deserialize<Profile>(raw, _json) ?? EmptyProfile("Profile", "P");

        clone.Pages ??= new List<DeckPage>();
        if (clone.Pages.Count == 0) clone.Pages.Add(DefaultPage("Страница 1"));

        var pageMap = new Dictionary<string, string>(StringComparer.Ordinal);
        clone.Id = Guid.NewGuid().ToString("N");
        foreach (var page in clone.Pages)
        {
            var oldId = page.Id;
            page.Id = Guid.NewGuid().ToString("N");
            pageMap[oldId] = page.Id;
            page.Tiles ??= new List<Tile>();
            foreach (var tile in page.Tiles)
                tile.Id = Guid.NewGuid().ToString("N");
            EnsureCapacity(page);
        }

        foreach (var page in clone.Pages)
            foreach (var tile in page.Tiles)
                if (tile.ActionType == "folder" && pageMap.TryGetValue(tile.ActionValue, out var mapped))
                    tile.ActionValue = mapped;

        clone.ActivePageId = pageMap.TryGetValue(clone.ActivePageId, out var active)
            ? active
            : clone.Pages[0].Id;
        V14NormalizeProfileBindings(clone);
        return clone;
    }

    private static string V14SafeFileName(string value)
    {
        var invalid = Path.GetInvalidFileNameChars();
        var cleaned = new string((value ?? "Profile").Select(ch => invalid.Contains(ch) ? '_' : ch).ToArray()).Trim();
        return string.IsNullOrWhiteSpace(cleaned) ? "Profile" : cleaned;
    }
}
