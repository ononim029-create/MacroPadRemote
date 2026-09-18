from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)


def insert_before_once(text: str, marker: str, insertion: str, label: str) -> str:
    count = text.count(marker)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one marker, got {count}")
    return text.replace(marker, insertion + marker, 1)


def patch_windows() -> None:
    path = ROOT / "src/windows/MacroPadRemote/MainWindow.xaml.cs"
    text = path.read_text(encoding="utf-8")

    text = replace_once(
        text,
        '''        _statePath = Path.Combine(dir, "presets.json");

        LoadState();
        ProfileBox.ItemsSource = _profiles;''',
        '''        _statePath = Path.Combine(dir, "presets.json");
        V13BeforeLoadState();

        LoadState();
        V13AfterLoadState();
        ProfileBox.ItemsSource = _profiles;''',
        "v1.3 first-run state hooks",
    )

    text = replace_once(
        text,
        '''            await StartSelectedTransportAsync();
            StartV12ContextMonitor();
            StartupStatus.Text = "Готово";''',
        '''            await StartSelectedTransportAsync();
            StartV12ContextMonitor();
            await V13RunFirstLaunchWizardAsync();
            StartupStatus.Text = "Готово";''',
        "v1.3 first-run wizard",
    )

    text = replace_once(
        text,
        '''    private void SaveState()
    {
        _state.Profiles = _profiles.ToList();
        if (_profile is not null) _state.ActiveProfileId = _profile.Id;
        try { File.WriteAllText(_statePath, JsonSerializer.Serialize(_state, _json)); } catch { }
    }''',
        '''    private void SaveState()
    {
        _state.Profiles = _profiles.ToList();
        if (_profile is not null) _state.ActiveProfileId = _profile.Id;
        _state.WorkspaceUpdatedUtc = DateTime.UtcNow;
        try { File.WriteAllText(_statePath, JsonSerializer.Serialize(_state, _json)); } catch { }
        _ = V13BroadcastWorkspaceBackupOnlyAsync();
    }''',
        "v1.3 workspace revision and backup push",
    )

    text = replace_once(
        text,
        '''            var messageType = root.TryGetProperty("type", out var typeProp) ? typeProp.GetString() ?? "" : "";

            if (messageType == "clientInfo")''',
        '''            var messageType = root.TryGetProperty("type", out var typeProp) ? typeProp.GetString() ?? "" : "";

            if (await V13HandleRemoteMessageAsync(root, messageType, clientId))
                return;

            if (messageType == "clientInfo")''',
        "v1.3 remote protocol hook",
    )

    text = replace_once(
        text,
        '''    private async Task SendSnapshotAsync(WebSocket socket)
    {
        var bytes = Encoding.UTF8.GetBytes(JsonSerializer.Serialize(Snapshot(), _json));
        await socket.SendAsync(bytes, WebSocketMessageType.Text, true, CancellationToken.None);
    }''',
        '''    private async Task SendSnapshotAsync(WebSocket socket)
    {
        var bytes = Encoding.UTF8.GetBytes(JsonSerializer.Serialize(Snapshot(), _json));
        await socket.SendAsync(bytes, WebSocketMessageType.Text, true, CancellationToken.None);
        await V13SendWorkspaceBackupAsync(socket);
    }''',
        "v1.3 full workspace snapshot",
    )

    text = replace_once(
        text,
        '''        root.Children.Add(deviceRows);

        void RebuildDeviceRows()''',
        '''        root.Children.Add(deviceRows);

        var libraryButton = new Button
        {
            Content = "Библиотека устройств / синхронизация",
            Height = 36,
            Margin = new Thickness(0, 12, 0, 4)
        };
        libraryButton.Click += async (_, _) =>
        {
            win.Hide();
            await V13OpenRemoteLibraryAsync();
            if (!win.IsVisible) win.Show();
        };
        root.Children.Add(libraryButton);

        void RebuildDeviceRows()''',
        "v1.3 library button",
    )

    text = replace_once(
        text,
        '''        var delete = new MenuItem { Header = "Удалить" }; delete.Click += DeleteProfile_Click;
        menu.Items.Add(rename); menu.Items.Add(copy); menu.Items.Add(new Separator()); menu.Items.Add(delete);''',
        '''        var clipboardCopy = new MenuItem { Header = "Копировать профиль" };
        clipboardCopy.Click += (_, _) => V13CopyProfile(profile);
        var clipboardPaste = new MenuItem { Header = "Вставить профиль", IsEnabled = V13HasCopiedProfile };
        clipboardPaste.Click += (_, _) => V13PasteProfile();
        var delete = new MenuItem { Header = "Удалить" }; delete.Click += DeleteProfile_Click;
        menu.Items.Add(rename);
        menu.Items.Add(copy);
        menu.Items.Add(new Separator());
        menu.Items.Add(clipboardCopy);
        menu.Items.Add(clipboardPaste);
        menu.Items.Add(new Separator());
        menu.Items.Add(delete);''',
        "v1.3 profile clipboard menu",
    )

    text = replace_once(
        text,
        '''        menu.Items.Add(properties);

        var test = new MenuItem { Header = "Выполнить тест" };''',
        '''        menu.Items.Add(properties);

        var clipboardCopy = new MenuItem { Header = "Копировать функцию" };
        clipboardCopy.Click += (_, _) => V13CopyTile(tile);
        var clipboardPaste = new MenuItem { Header = "Вставить функцию", IsEnabled = V13HasCopiedTile };
        clipboardPaste.Click += (_, _) => V13PasteTile(tile);
        menu.Items.Add(clipboardCopy);
        menu.Items.Add(clipboardPaste);
        menu.Items.Add(new Separator());

        var test = new MenuItem { Header = "Выполнить тест" };''',
        "v1.3 action clipboard menu",
    )

    text = replace_once(
        text,
        '''public sealed class AppState
{
    public string ServerId { get; set; } = Guid.NewGuid().ToString("N");
    public string ActiveProfileId { get; set; } = "";
    public string Transport { get; set; } = "Wifi";''',
        '''public sealed class AppState
{
    public string ServerId { get; set; } = Guid.NewGuid().ToString("N");
    public string ActiveProfileId { get; set; } = "";
    public string Transport { get; set; } = "Wifi";
    public bool SetupCompleted { get; set; } = false;
    public DateTime WorkspaceUpdatedUtc { get; set; } = DateTime.UtcNow;''',
        "v1.3 app state fields",
    )

    path.write_text(text, encoding="utf-8")

    xaml_path = ROOT / "src/windows/MacroPadRemote/MainWindow.xaml"
    xaml = xaml_path.read_text(encoding="utf-8")
    xaml = xaml.replace('Text="  v1.2.5 preview"', 'Text="  v1.3.0 preview"', 1)
    xaml_path.write_text(xaml, encoding="utf-8")
    print(f"Applied v1.3 Windows fixes: {path}")



if __name__ == "__main__":
    patch_windows()
