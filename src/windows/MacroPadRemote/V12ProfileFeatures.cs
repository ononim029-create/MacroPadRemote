using System.Drawing.Imaging;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;

namespace MacroPadRemote;

public partial class MainWindow
{
    private DispatcherTimer? _v12ContextTimer;
    private string _v12LastKeyboardLayout = "";
    private bool _v12ContextBusy;

    private void StartV12ContextMonitor()
    {
        if (_v12ContextTimer is not null) return;
        _v12LastKeyboardLayout = KeyboardLayoutService.GetActiveId();
        _v12ContextTimer = new DispatcherTimer(DispatcherPriority.Background)
        {
            Interval = TimeSpan.FromMilliseconds(700)
        };
        _v12ContextTimer.Tick += async (_, _) => await V12ContextTickAsync();
        _v12ContextTimer.Start();
    }

    private void StopV12ContextMonitor()
    {
        if (_v12ContextTimer is null) return;
        _v12ContextTimer.Stop();
        _v12ContextTimer = null;
    }

    private async Task V12ContextTickAsync()
    {
        if (_v12ContextBusy) return;
        _v12ContextBusy = true;
        try
        {
            var layout = KeyboardLayoutService.GetActiveId();
            var layoutChanged = !string.IsNullOrWhiteSpace(layout) && !string.Equals(layout, _v12LastKeyboardLayout, StringComparison.OrdinalIgnoreCase);
            if (layoutChanged) _v12LastKeyboardLayout = layout;

            var exe = ForegroundAppService.GetExecutableName();
            var automatic = string.IsNullOrWhiteSpace(exe)
                ? null
                : _profiles.FirstOrDefault(p =>
                {
                    V14NormalizeProfileBindings(p);
                    return p.BoundApplications.Any(app => string.Equals(app, exe, StringComparison.OrdinalIgnoreCase));
                });

            if (automatic is null && !string.IsNullOrWhiteSpace(_state.DefaultProfileId))
                automatic = _profiles.FirstOrDefault(p => string.Equals(p.Id, _state.DefaultProfileId, StringComparison.Ordinal));

            var profileChanged = automatic is not null && !string.Equals(_state.ActiveProfileId, automatic.Id, StringComparison.Ordinal);
            if (profileChanged)
            {
                _state.ActiveProfileId = automatic!.Id;
                SaveState();
                RefreshProfiles();
                DeviceStatus.Text = $"Автопрофиль: {automatic.Name} • {exe}";
            }

            if (layoutChanged || profileChanged)
                await BroadcastSnapshotAsync();
        }
        catch
        {
            // Context monitoring must never interrupt the remote server.
        }
        finally
        {
            _v12ContextBusy = false;
        }
    }

    private void AddV12ProfileMenuItems(ContextMenu menu, Profile profile)
    {
        var icon = new MenuItem { Header = "Иконка профиля…" };
        icon.Click += (_, _) => ShowProfileIconPicker(profile);

        V14NormalizeProfileBindings(profile);
        var bind = new MenuItem
        {
            Header = profile.BoundApplications.Count == 0
                ? "Приложения профиля…"
                : $"Приложения: {string.Join(", ", profile.BoundApplications)}"
        };
        bind.Click += (_, _) => V14OpenSettingsWindow();

        var unbind = new MenuItem
        {
            Header = "Убрать привязки приложений",
            IsEnabled = profile.BoundApplications.Count > 0
        };
        unbind.Click += (_, _) =>
        {
            profile.BoundApplications.Clear();
            profile.BoundApplication = "";
            profile.BoundApplicationPath = "";
            SaveState();
            RefreshProfiles();
            _ = BroadcastSnapshotAsync();
        };

        menu.Items.Insert(0, new Separator());
        menu.Items.Insert(0, unbind);
        menu.Items.Insert(0, bind);
        menu.Items.Insert(0, icon);
    }

    private void BindProfileApplication(Profile profile)
    {
        var dialog = new Microsoft.Win32.OpenFileDialog
        {
            Title = "Привязать приложение к профилю",
            Filter = "Программы (*.exe)|*.exe|Все файлы|*.*",
            Multiselect = false
        };
        if (dialog.ShowDialog(this) != true) return;
        profile.BoundApplicationPath = dialog.FileName;
        profile.BoundApplication = Path.GetFileName(dialog.FileName);
        SaveState();
        RefreshProfiles();
        _ = BroadcastSnapshotAsync();
    }

    private void ShowProfileIconPicker(Profile profile)
    {
        var window = new Window
        {
            Owner = this,
            Title = $"NEXO — иконка профиля «{profile.Name}»",
            Width = 650,
            Height = 540,
            MinWidth = 560,
            MinHeight = 430,
            WindowStartupLocation = WindowStartupLocation.CenterOwner,
            Background = (Brush)FindResource("Bg")
        };

        var root = new Grid { Margin = new Thickness(16) };
        root.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        root.RowDefinitions.Add(new RowDefinition());
        root.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        root.Children.Add(new TextBlock
        {
            Text = "Иконка профиля",
            FontSize = 21,
            FontWeight = FontWeights.SemiBold,
            Margin = new Thickness(0, 0, 0, 12)
        });

        var scroll = new ScrollViewer { VerticalScrollBarVisibility = ScrollBarVisibility.Auto };
        var content = new StackPanel();
        scroll.Content = content;
        Grid.SetRow(scroll, 1);
        root.Children.Add(scroll);

        void setIcon(string value)
        {
            profile.Icon = string.IsNullOrWhiteSpace(value)
                ? (string.IsNullOrWhiteSpace(profile.Name) ? "•" : profile.Name[..1].ToUpperInvariant())
                : value;
            SaveState();
            RefreshProfiles();
            _ = BroadcastSnapshotAsync();
            window.Close();
        }

        var actions = new WrapPanel();
        var reset = IconChoiceButton("По умолчанию", new TextBlock { Text = "A", FontSize = 24, FontWeight = FontWeights.Bold, Foreground = Brushes.White, HorizontalAlignment = HorizontalAlignment.Center });
        reset.Click += (_, _) => setIcon("");
        actions.Children.Add(reset);

        var app = IconChoiceButton("Иконка приложения", new TextBlock { Text = "↗", FontSize = 25, Foreground = Brushes.White, HorizontalAlignment = HorizontalAlignment.Center });
        app.Click += (_, _) =>
        {
            var path = profile.BoundApplicationPath;
            if (string.IsNullOrWhiteSpace(path) || !File.Exists(path))
            {
                var dialog = new Microsoft.Win32.OpenFileDialog { Title = "Выберите приложение", Filter = "Программы (*.exe)|*.exe|Все файлы|*.*" };
                if (dialog.ShowDialog(window) != true) return;
                path = dialog.FileName;
            }
            var data = ProfileIconFromExecutable(path);
            if (!string.IsNullOrWhiteSpace(data)) setIcon(data);
        };
        actions.Children.Add(app);

        var import = IconChoiceButton("Из файла", new TextBlock { Text = "+", FontSize = 26, Foreground = Brushes.White, HorizontalAlignment = HorizontalAlignment.Center });
        import.Click += (_, _) =>
        {
            var dialog = new Microsoft.Win32.OpenFileDialog { Title = "Иконка профиля", Filter = "Изображения|*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.gif|Все файлы|*.*" };
            if (dialog.ShowDialog(window) != true) return;
            try
            {
                using var stream = File.OpenRead(dialog.FileName);
                var data = NormalizeImage(stream);
                if (!string.IsNullOrWhiteSpace(data)) setIcon(data);
            }
            catch { }
        };
        actions.Children.Add(import);

        var screenshot = IconChoiceButton("Снимок экрана", new TextBlock { Text = "⌗", FontSize = 25, Foreground = Brushes.White, HorizontalAlignment = HorizontalAlignment.Center });
        screenshot.Click += async (_, _) =>
        {
            window.Hide();
            var wasVisible = IsVisible;
            if (wasVisible) Hide();
            await Task.Delay(180);
            BitmapSource? captured = null;
            try
            {
                var region = ScreenRegionSelector.SelectRegion();
                if (region is not null)
                {
                    await Task.Delay(80);
                    captured = ScreenRegionSelector.Capture(region.Value);
                }
            }
            finally
            {
                if (wasVisible)
                {
                    Show();
                    Activate();
                }
                if (window.IsLoaded) window.Show();
            }
            if (captured is null) return;
            var data = NormalizeBitmap(captured);
            if (!string.IsNullOrWhiteSpace(data)) setIcon(data);
        };
        actions.Children.Add(screenshot);
        content.Children.Add(actions);

        content.Children.Add(new TextBlock
        {
            Text = "Локальная библиотека",
            FontWeight = FontWeights.SemiBold,
            Foreground = (Brush)FindResource("Muted"),
            Margin = new Thickness(0, 14, 0, 6)
        });
        var library = new WrapPanel();
        foreach (var asset in _state.IconLibrary)
        {
            var bitmap = BitmapFromDataUri(asset.DataUri);
            var visual = bitmap is null
                ? (UIElement)new TextBlock { Text = "?", FontSize = 24, Foreground = Brushes.White, HorizontalAlignment = HorizontalAlignment.Center }
                : new Image { Source = bitmap, Width = 44, Height = 44, Stretch = Stretch.Uniform };
            var button = IconChoiceButton(asset.Name, visual);
            button.Click += (_, _) => setIcon(asset.DataUri);
            library.Children.Add(button);
        }
        if (_state.IconLibrary.Count == 0)
            library.Children.Add(new TextBlock { Text = "Библиотека пока пустая.", Foreground = (Brush)FindResource("Muted"), Margin = new Thickness(4, 8, 0, 8) });
        content.Children.Add(library);

        var close = new Button { Content = "Закрыть", Width = 100, Height = 32, HorizontalAlignment = HorizontalAlignment.Right, Margin = new Thickness(0, 12, 0, 0) };
        close.Click += (_, _) => window.Close();
        Grid.SetRow(close, 2);
        root.Children.Add(close);
        window.Content = root;
        window.ShowDialog();
    }

    private static string ProfileIconFromExecutable(string path)
    {
        try
        {
            using var icon = System.Drawing.Icon.ExtractAssociatedIcon(path);
            if (icon is null) return "";
            using var bitmap = icon.ToBitmap();
            using var stream = new MemoryStream();
            bitmap.Save(stream, ImageFormat.Png);
            return "data:image/png;base64," + Convert.ToBase64String(stream.ToArray());
        }
        catch
        {
            return "";
        }
    }
}
