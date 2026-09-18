from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)


def replace_between(text: str, start: str, end: str, replacement: str, label: str) -> str:
    a = text.find(start)
    if a < 0:
        raise RuntimeError(f"{label}: start marker not found")
    b = text.find(end, a)
    if b < 0:
        raise RuntimeError(f"{label}: end marker not found")
    return text[:a] + replacement + text[b:]


def main() -> None:
    path = ROOT / "src/windows/MacroPadRemote/MainWindow.xaml.cs"
    text = path.read_text(encoding="utf-8")

    text = replace_between(
        text,
        "    private async void HeaderSettingsButton_Click(object sender, RoutedEventArgs e)\n    {",
        "\n    private static Profile DefaultProfile",
        """    private void HeaderSettingsButton_Click(object sender, RoutedEventArgs e)
    {
        ProfileSettingsPopup.IsOpen = false;
        V14OpenSettingsWindow();
    }

""",
        "v1.4 settings window",
    )

    text = replace_once(
        text,
        '    public string BoundApplicationPath { get; set; } = "";\n    public string ActivePageId { get; set; } = "";',
        '    public string BoundApplicationPath { get; set; } = "";\n    public List<string> BoundApplications { get; set; } = new();\n    public string ActivePageId { get; set; } = "";',
        "multi app profile bindings",
    )
    text = replace_once(
        text,
        '    public DateTime WorkspaceUpdatedUtc { get; set; } = DateTime.UtcNow;',
        '    public DateTime WorkspaceUpdatedUtc { get; set; } = DateTime.UtcNow;\n    public string DefaultProfileId { get; set; } = "";',
        "default profile state",
    )
    text = replace_once(
        text,
        '    public string DefaultProfileId { get; set; } = "";\n    public string SourceServerId { get; set; } = "";',
        '    public string DefaultProfileId { get; set; } = "";\n    public bool DeviceLinkEnabled { get; set; } = false;\n    public bool DeviceLinkAutoUpdate { get; set; } = false;\n    public string DeviceLinkSourceServerId { get; set; } = "";\n    public string DeviceLinkSourceServerName { get; set; } = "";\n    public DateTime DeviceLinkUpdatedUtc { get; set; } = DateTime.MinValue;\n    public string SourceServerId { get; set; } = "";',
        "device link state",
    )

    text = replace_once(
        text,
        '''        _state.Profiles ??= new List<Profile>();
        _state.TrustedDevices ??= new List<TrustedClient>();''',
        '''        _state.Profiles ??= new List<Profile>();
        var legacyProfiles = _state.Profiles.ToList();
        _state.Profiles = V14LoadProfilesFromProgramFolder(legacyProfiles);
        _state.TrustedDevices ??= new List<TrustedClient>();''',
        "load profiles from program Profiles folder with legacy migration",
    )

    text = replace_once(
        text,
        '''        _state.WorkspaceUpdatedUtc = DateTime.UtcNow;
        try { File.WriteAllText(_statePath, JsonSerializer.Serialize(_state, _json)); } catch { }
        _ = V13BroadcastWorkspaceBackupOnlyAsync();''',
        '''        _state.WorkspaceUpdatedUtc = DateTime.UtcNow;
        try
        {
            V14PersistProfilesToProgramFolder();
            File.WriteAllText(_statePath, V14SerializeStateWithoutProfiles());
        }
        catch (Exception ex)
        {
            DeviceStatus.Text = $"Ошибка сохранения профилей: {ex.Message}";
        }
        _ = V14OnWorkspaceChangedAsync();''',
        "persist profiles beside executable and keep state profile-free",
    )

    text = replace_once(
        text,
        '''        var bytes = Encoding.UTF8.GetBytes(JsonSerializer.Serialize(Snapshot(), _json));
        await socket.SendAsync(bytes, WebSocketMessageType.Text, true, CancellationToken.None);
        await V13SendWorkspaceBackupAsync(socket);''',
        '''        var bytes = Encoding.UTF8.GetBytes(JsonSerializer.Serialize(Snapshot(), _json));
        await socket.SendAsync(bytes, WebSocketMessageType.Text, true, CancellationToken.None);
        await V14SyncLinkOnClientConnectedAsync(socket);''',
        "sync links only when enabled",
    )
    text = replace_once(
        text,
        "    private bool _capturingHotkey;\n",
        "    private bool _capturingHotkey;\n    private readonly List<string> _v14CombinationTokens = new();\n",
        "combination recorder state",
    )

    text = replace_between(
        text,
        "    private void RecordHotkey_Click(object sender, RoutedEventArgs e)\n    {",
        "\n    private static string KeyToToken(Key key)",
        r'''    private void RecordHotkey_Click(object sender, RoutedEventArgs e)
    {
        if (_selected is null) return;

        if (_capturingHotkey)
        {
            _capturingHotkey = false;
            RecordHotkeyButton.Content = "Записать";
            if (_selected.ActionType == "superhotkey")
            {
                _selected.ActionValue = string.Join(' ', _v14CombinationTokens);
                InspectorHotkeyBox.Text = _selected.ActionValue;
            }
            SaveAndBroadcast();
            return;
        }

        _capturingHotkey = true;
        _v14CombinationTokens.Clear();
        if (_selected.ActionType == "superhotkey")
        {
            _selected.ActionValue = "";
            InspectorHotkeyBox.Text = "";
            RecordHotkeyButton.Content = "Завершить запись";
        }
        else
        {
            RecordHotkeyButton.Content = "Нажмите сочетание…";
        }
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
        var keyToken = KeyToToken(key);
        if (!string.IsNullOrWhiteSpace(keyToken)) tokens.Add(keyToken);
        var chord = string.Join('+', tokens);

        if (_selected.ActionType == "superhotkey")
        {
            if (!string.IsNullOrWhiteSpace(chord))
            {
                _v14CombinationTokens.Add(chord);
                _selected.ActionValue = string.Join(' ', _v14CombinationTokens);
                InspectorHotkeyBox.Text = _selected.ActionValue;
            }
            RecordHotkeyButton.Content = "Завершить запись";
            e.Handled = true;
            return;
        }

        _selected.ActionType = "hotkey";
        _selected.Hotkey = chord;
        _selected.ActionValue = "";
        InspectorHotkeyBox.Text = chord;
        InspectorTypeBox.Text = ActionTypeName("hotkey");
        _capturingHotkey = false;
        RecordHotkeyButton.Content = "Записать";
        e.Handled = true;
        SaveAndBroadcast();
    }

''',
        "combination key recorder",
    )

    text = replace_between(
        text,
        "    private void RefreshInspector()\n    {",
        "\n    private void ActionLibrary_PreviewMouseLeftButtonDown",
        r'''    private void RefreshInspector()
    {
        _updating = true;
        var enabled = _selected is not null;
        var combination = _selected?.ActionType == "superhotkey";
        var normalHotkey = _selected?.ActionType == "hotkey";

        InspectorTitleBox.IsEnabled = enabled;
        InspectorTypeBox.IsEnabled = enabled;
        InspectorValueBox.IsEnabled = enabled && !combination;
        InspectorHotkeyBox.IsEnabled = enabled;
        InspectorHotkeyBox.IsReadOnly = combination;
        RecordHotkeyButton.IsEnabled = enabled && (normalHotkey || combination);
        InspectorShowLabel.IsEnabled = enabled;

        InspectorValueLabel.Visibility = combination ? Visibility.Collapsed : Visibility.Visible;
        InspectorValueBox.Visibility = combination ? Visibility.Collapsed : Visibility.Visible;
        SuperHotkeySettingsPanel.Visibility = combination ? Visibility.Visible : Visibility.Collapsed;

        if (_selected is null)
        {
            InspectorHint.Text = "Выберите плитку или перетащите действие из каталога на рабочее поле.";
            InspectorTitleBox.Text = "";
            InspectorTypeBox.Text = "";
            InspectorValueBox.Text = "";
            InspectorHotkeyBox.Text = "";
            InspectorValueLabel.Text = "Параметр";
            SuperIntervalBox.Text = "50";
            SuperRepeatBox.Text = "1";
            SuperTimerBox.Text = "0";
            InspectorShowLabel.IsChecked = true;
        }
        else
        {
            InspectorHint.Text = combination
                ? "Нажмите «Записать», наберите нужные клавиши и нажмите «Завершить запись». Можно записывать A A, A W, CTRL+S и другие сочетания."
                : "Настройка выполняется на ПК. Изменения сразу синхронизируются с подключенным телефоном.";
            InspectorTitleBox.Text = _selected.Title;
            InspectorTypeBox.Text = ActionTypeName(_selected.ActionType);
            InspectorValueBox.Text = _selected.ActionValue;
            InspectorHotkeyBox.Text = combination ? _selected.ActionValue : _selected.Hotkey;
            InspectorShowLabel.IsChecked = _selected.ShowLabel;
            SuperIntervalBox.Text = _selected.MacroIntervalMs.ToString();
            SuperRepeatBox.Text = _selected.MacroRepeatCount.ToString();
            SuperTimerBox.Text = _selected.MacroStartDelayMs.ToString();
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
        "superhotkey" => "Сочетание клавиш",
        "text" => "Текст",
        "open" => "Открыть",
        "url" => "Веб-сайт",
        "folder" => "Папка",
        "multi" => "Multi Action",
        "profile" => "Переключить профиль",
        "media" => "Мультимедиа",
        _ => "Не назначено"
    };

''',
        "v1.4 inspector",
    )

    text = replace_between(
        text,
        "    private void ApplyInspector_Click(object sender, RoutedEventArgs e)\n    {",
        "\n    private void ClearTile_Click",
        r'''    private void ApplyInspector_Click(object sender, RoutedEventArgs e)
    {
        if (_selected is null) return;
        _selected.Title = string.IsNullOrWhiteSpace(InspectorTitleBox.Text) ? "Кнопка" : InspectorTitleBox.Text.Trim();
        _selected.ShowLabel = InspectorShowLabel.IsChecked != false;

        if (_selected.ActionType == "hotkey")
        {
            _selected.Hotkey = InspectorHotkeyBox.Text.Trim().ToUpperInvariant();
            _selected.ActionValue = "";
        }
        else if (_selected.ActionType == "superhotkey")
        {
            _selected.ActionValue = InspectorHotkeyBox.Text.Trim().ToUpperInvariant();
            _selected.MacroIntervalMs = int.TryParse(SuperIntervalBox.Text, out var interval) ? Math.Clamp(interval, 0, 60000) : 50;
            _selected.MacroRepeatCount = int.TryParse(SuperRepeatBox.Text, out var repeat) ? Math.Clamp(repeat, 1, 999) : 1;
            _selected.MacroStartDelayMs = int.TryParse(SuperTimerBox.Text, out var timer) ? Math.Clamp(timer, 0, 3600000) : 0;
        }
        else
        {
            _selected.ActionValue = InspectorValueBox.Text.Trim();
        }

        SaveAndBroadcast();
        RefreshInspector();
    }

''',
        "v1.4 inspector apply",
    )

    text = text.replace("Супер горячая клавиша", "Сочетание клавиш")
    text = text.replace(
        "Последовательности AA / AW или сочетания A+W с интервалом, повторами и таймером",
        "Записываемые сочетания и последовательности клавиш с интервалом, повторами и таймером",
    )
    text = text.replace(
        '"superhotkey", "AW")',
        '"superhotkey", "")',
    )

    path.write_text(text, encoding="utf-8")

    xaml_path = ROOT / "src/windows/MacroPadRemote/MainWindow.xaml"
    xaml = xaml_path.read_text(encoding="utf-8")
    xaml = replace_once(xaml, '<ColumnDefinition Width="285"/>', '<ColumnDefinition Width="0"/>', "hide left profile sidebar")
    xaml = xaml.replace('ToolTip="Настройки подключения"', 'ToolTip="Настройки"')
    xaml = xaml.replace('x:Name="InspectorIconPreview" Width="38" Height="38"', 'x:Name="InspectorIconPreview" Width="34" Height="34"')
    xaml = xaml.replace('x:Name="InspectorIconStatus" Text="AUTO" Width="70"', 'x:Name="InspectorIconStatus" Text="AUTO" Width="48"')
    xaml = xaml.replace('x:Name="IconLibraryButton" Content="Библиотека" Width="66"', 'x:Name="IconLibraryButton" Content="Библиотека" Width="52"')
    xaml = xaml.replace('x:Name="IconImportButton" Content="Файл" Width="62"', 'x:Name="IconImportButton" Content="Файл" Width="50"')
    xaml = xaml.replace('x:Name="IconSnapshotButton" Content="Снимок" Width="62"', 'x:Name="IconSnapshotButton" Content="Снимок" Width="50"')
    xaml = xaml.replace('x:Name="IconAutoButton" Content="AUTO" Width="52"', 'x:Name="IconAutoButton" Content="AUTO" Width="44"')
    xaml = xaml.replace('Text="AW = A→W; AA = A→A; A+W = одновременное сочетание"', 'Text="Запись: A A, A W, CTRL+S и другие сочетания"')
    xaml = xaml.replace('Text="  v1.3.0 preview"', 'Text="  v1.4.0 preview"')
    xaml_path.write_text(xaml, encoding="utf-8")

    print(f"Applied v1.4 Windows fixes: {path}")


if __name__ == "__main__":
    main()
