using System;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Reflection;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.Windows.Media.Effects;
using Microsoft.Win32;
using IOPath = System.IO.Path;
using Rectangle = System.Windows.Shapes.Rectangle;

namespace NexoInstaller;

internal static class OfflineInstallerApp
{
    [STAThread]
    public static void Main()
    {
        var app = new Application { ShutdownMode = ShutdownMode.OnMainWindowClose };
        app.DispatcherUnhandledException += (_, e) =>
        {
            InstallerLog.Write("Unhandled UI exception: " + e.Exception);
            MessageBox.Show(e.Exception.Message, "NEXO Setup", MessageBoxButton.OK, MessageBoxImage.Error);
            e.Handled = true;
        };
        AppDomain.CurrentDomain.UnhandledException += (_, e) => InstallerLog.Write("Unhandled exception: " + e.ExceptionObject);
        app.Run(new OfflineSetupWindow());
    }
}

internal static class InstallerLog
{
    public static readonly string Path = IOPath.Combine(IOPath.GetTempPath(), "NEXO-Setup.log");

    public static void Write(string message)
    {
        try
        {
            File.AppendAllText(Path, $"[{DateTime.Now:yyyy-MM-dd HH:mm:ss}] {message}{Environment.NewLine}");
        }
        catch { }
    }
}

internal sealed class OfflineSetupWindow : Window
{
    private const string PayloadResource = "NEXO.Payload.zip";
    private const string UninstallKey = @"Software\Microsoft\Windows\CurrentVersion\Uninstall\NEXO";

    private static readonly SolidColorBrush Bg = B("#17191B");
    private static readonly SolidColorBrush Header = B("#1B1D1F");
    private static readonly SolidColorBrush Panel = B("#1D1F21");
    private static readonly SolidColorBrush Panel2 = B("#24272A");
    private static readonly SolidColorBrush Border = B("#353A3E");
    private static readonly SolidColorBrush Text = B("#F2F2F2");
    private static readonly SolidColorBrush Muted = B("#9DA3A8");
    private static readonly SolidColorBrush Blue = B("#1688FF");
    private static readonly SolidColorBrush Green = B("#62D16F");
    private static readonly SolidColorBrush Red = B("#FF6B6B");

    private readonly TextBox _path;
    private readonly CheckBox _desktopShortcut;
    private readonly CheckBox _launchAfterInstall;
    private readonly TextBlock _status;
    private readonly TextBlock _percent;
    private readonly Border _progressTrack;
    private readonly Border _progressFill;
    private readonly Button _install;
    private readonly Button _browse;
    private readonly Button _close;
    private readonly ScaleTransform _logoScale = new(1, 1);
    private CancellationTokenSource _cts = new();
    private bool _working;
    private bool _installed;
    private double _progress;

    public OfflineSetupWindow()
    {
        InstallerLog.Write("NEXO offline setup started. Version 1.1.0-preview.");

        Title = "NEXO Setup";
        Width = MinWidth = MaxWidth = 720;
        Height = MinHeight = MaxHeight = 600;
        WindowStartupLocation = WindowStartupLocation.CenterScreen;
        WindowStyle = WindowStyle.None;
        ResizeMode = ResizeMode.NoResize;
        AllowsTransparency = true;
        Background = Brushes.Transparent;
        Foreground = Text;
        FontFamily = new FontFamily("Segoe UI");
        Opacity = 0;

        var shell = new Border
        {
            Background = Bg,
            BorderBrush = Border,
            BorderThickness = new Thickness(1),
            CornerRadius = new CornerRadius(18),
            Effect = new DropShadowEffect { BlurRadius = 30, ShadowDepth = 8, Opacity = .42, Color = Colors.Black },
            RenderTransformOrigin = new Point(.5, .5),
            RenderTransform = new ScaleTransform(.965, .965)
        };
        Content = shell;

        var grid = new Grid();
        grid.RowDefinitions.Add(new RowDefinition { Height = new GridLength(60) });
        grid.RowDefinitions.Add(new RowDefinition());
        shell.Child = grid;
        grid.Children.Add(BuildHeader());

        var body = new Grid { Margin = new Thickness(38, 30, 38, 30) };
        body.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        body.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        body.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        body.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        body.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        body.RowDefinitions.Add(new RowDefinition());
        body.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        Grid.SetRow(body, 1);
        grid.Children.Add(body);

        var hero = new StackPanel();
        hero.Children.Add(new TextBlock { Text = "Установка NEXO", FontSize = 30, FontWeight = FontWeights.SemiBold, Foreground = Text });
        hero.Children.Add(new TextBlock { Text = "Офлайн-установщик • все файлы уже внутри", FontSize = 13, Foreground = Muted, Margin = new Thickness(0, 7, 0, 0) });
        body.Children.Add(hero);

        var folderCard = Card(18, 15, 18, 16, 24);
        Grid.SetRow(folderCard, 1);
        body.Children.Add(folderCard);
        var folderStack = new StackPanel();
        folderCard.Child = folderStack;
        folderStack.Children.Add(new TextBlock { Text = "Папка установки", FontSize = 12, FontWeight = FontWeights.SemiBold, Foreground = Text, Margin = new Thickness(0, 0, 0, 9) });
        var folderGrid = new Grid();
        folderGrid.ColumnDefinitions.Add(new ColumnDefinition());
        folderGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(104) });
        folderStack.Children.Add(folderGrid);

        _path = new TextBox
        {
            Text = IOPath.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "NEXO"),
            Height = 38,
            Background = B("#111315"),
            Foreground = Text,
            CaretBrush = Brushes.White,
            BorderBrush = Border,
            BorderThickness = new Thickness(1),
            Padding = new Thickness(11, 7, 11, 7),
            FontSize = 12,
            VerticalContentAlignment = VerticalAlignment.Center
        };
        folderGrid.Children.Add(_path);
        _browse = Btn("Обзор", false, 94, 38);
        _browse.Margin = new Thickness(10, 0, 0, 0);
        _browse.Click += Browse_Click;
        Grid.SetColumn(_browse, 1);
        folderGrid.Children.Add(_browse);

        var optionsCard = Card(18, 14, 18, 14, 12);
        Grid.SetRow(optionsCard, 2);
        body.Children.Add(optionsCard);
        var options = new StackPanel();
        optionsCard.Child = options;
        _desktopShortcut = Check("Создать ярлык NEXO на рабочем столе", true);
        _launchAfterInstall = Check("Запустить NEXO после установки", true);
        _launchAfterInstall.Margin = new Thickness(0, 10, 0, 0);
        options.Children.Add(_desktopShortcut);
        options.Children.Add(_launchAfterInstall);

        var progress = new Grid { Margin = new Thickness(0, 24, 0, 0) };
        progress.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        progress.RowDefinitions.Add(new RowDefinition { Height = new GridLength(10) });
        progress.ColumnDefinitions.Add(new ColumnDefinition());
        progress.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        Grid.SetRow(progress, 3);
        body.Children.Add(progress);
        _status = new TextBlock { Text = "Готово к установке", Foreground = Muted, FontSize = 12 };
        progress.Children.Add(_status);
        _percent = new TextBlock { Text = "0%", Foreground = Muted, FontSize = 12, HorizontalAlignment = HorizontalAlignment.Right };
        Grid.SetColumn(_percent, 1);
        progress.Children.Add(_percent);
        _progressTrack = new Border { Height = 7, Background = Panel2, CornerRadius = new CornerRadius(4), Margin = new Thickness(0, 9, 0, 0), ClipToBounds = true };
        Grid.SetRow(_progressTrack, 1);
        Grid.SetColumnSpan(_progressTrack, 2);
        progress.Children.Add(_progressTrack);
        _progressFill = new Border { Width = 0, HorizontalAlignment = HorizontalAlignment.Left, Background = Blue, CornerRadius = new CornerRadius(4) };
        _progressTrack.Child = _progressFill;
        _progressTrack.SizeChanged += (_, _) => UpdateProgress(false);

        var meta = new TextBlock
        {
            Text = "NEXO v1.1 preview  •  Windows x64  •  интернет для установки не требуется",
            Foreground = B("#737A80"),
            FontSize = 10,
            Margin = new Thickness(0, 14, 0, 0)
        };
        Grid.SetRow(meta, 4);
        body.Children.Add(meta);

        var footer = new Grid { Margin = new Thickness(0, 28, 0, 0) };
        footer.ColumnDefinitions.Add(new ColumnDefinition());
        footer.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        Grid.SetRow(footer, 6);
        body.Children.Add(footer);
        _close = Btn("Закрыть", false, 108, 42);
        _close.Click += (_, _) => { if (_working) _cts.Cancel(); else Close(); };
        footer.Children.Add(_close);
        _install = Btn("Установить NEXO", true, 184, 42);
        _install.Click += Install_Click;
        Grid.SetColumn(_install, 1);
        footer.Children.Add(_install);

        Loaded += (_, _) => Intro(shell);
        Closing += (_, _) => _cts.Cancel();
    }

    private Border BuildHeader()
    {
        var header = new Border { Background = Header, BorderBrush = Border, BorderThickness = new Thickness(0, 0, 0, 1), CornerRadius = new CornerRadius(18, 18, 0, 0) };
        header.MouseLeftButtonDown += (_, e) => { if (e.ButtonState == MouseButtonState.Pressed) DragMove(); };
        var g = new Grid { Margin = new Thickness(18, 0, 12, 0) };
        g.ColumnDefinitions.Add(new ColumnDefinition());
        g.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        header.Child = g;
        var brand = new StackPanel { Orientation = Orientation.Horizontal, VerticalAlignment = VerticalAlignment.Center };
        g.Children.Add(brand);
        var logo = Logo(28);
        logo.Margin = new Thickness(0, 0, 11, 0);
        logo.RenderTransformOrigin = new Point(.5, .5);
        logo.RenderTransform = _logoScale;
        brand.Children.Add(logo);
        brand.Children.Add(new TextBlock { Text = "NEXO", FontSize = 18, FontWeight = FontWeights.SemiBold, Foreground = Text, VerticalAlignment = VerticalAlignment.Center });
        brand.Children.Add(new TextBlock { Text = "  Offline Setup v1.1", FontSize = 11, Foreground = Muted, VerticalAlignment = VerticalAlignment.Center });
        var x = Btn("×", false, 38, 32);
        x.FontSize = 20;
        x.Click += (_, _) => { if (_working) _cts.Cancel(); else Close(); };
        Grid.SetColumn(x, 1);
        g.Children.Add(x);
        return header;
    }

    private void Browse_Click(object? sender, RoutedEventArgs e)
    {
        var dlg = new OpenFolderDialog
        {
            Title = "Выберите папку установки NEXO",
            InitialDirectory = Directory.Exists(_path.Text) ? _path.Text : Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData)
        };
        if (dlg.ShowDialog(this) == true) _path.Text = dlg.FolderName;
    }

    private async void Install_Click(object? sender, RoutedEventArgs e)
    {
        if (_installed) { Launch(); return; }
        if (_working) return;
        await InstallAsync();
    }

    private async Task InstallAsync()
    {
        _working = true;
        Toggle(false);
        Pulse(true);
        _cts.Dispose();
        _cts = new CancellationTokenSource();
        string? zip = null;

        try
        {
            var installDir = IOPath.GetFullPath(Environment.ExpandEnvironmentVariables(_path.Text.Trim()));
            if (string.IsNullOrWhiteSpace(installDir)) throw new InvalidOperationException("Укажите папку установки.");
            if (Process.GetProcessesByName("NEXO").Any()) throw new InvalidOperationException("Закройте NEXO перед установкой или обновлением.");

            InstallerLog.Write("Install directory: " + installDir);
            SetStatus("Подготовка встроенного пакета…", 5);
            zip = IOPath.Combine(IOPath.GetTempPath(), $"NEXO-{Guid.NewGuid():N}.zip");
            await ExtractEmbeddedPayloadAsync(zip, _cts.Token);

            SetStatus("Распаковка файлов…", 48);
            await Task.Run(() =>
            {
                _cts.Token.ThrowIfCancellationRequested();
                if (Directory.Exists(installDir)) Directory.Delete(installDir, true);
                Directory.CreateDirectory(installDir);
                ZipFile.ExtractToDirectory(zip, installDir, true);
            }, _cts.Token);

            var exe = IOPath.Combine(installDir, "NEXO.exe");
            var uninstaller = IOPath.Combine(installDir, "NEXO-Uninstall.exe");
            if (!File.Exists(exe)) throw new InvalidDataException("В установочном пакете отсутствует NEXO.exe.");
            if (!File.Exists(uninstaller)) throw new InvalidDataException("В установочном пакете отсутствует NEXO-Uninstall.exe.");

            SetStatus("Регистрация в Windows…", 88);
            RegisterInstalledApp(installDir, exe, uninstaller);

            if (_desktopShortcut.IsChecked == true)
            {
                SetStatus("Создание ярлыка…", 95);
                CreateShortcut(exe, installDir);
            }

            SetStatus("NEXO установлен", 100, Green);
            InstallerLog.Write("Installation completed successfully.");
            _installed = true;
            _install.Content = "Открыть NEXO";
            _install.IsEnabled = true;
            if (_launchAfterInstall.IsChecked == true) Launch();
        }
        catch (OperationCanceledException)
        {
            InstallerLog.Write("Installation cancelled.");
            SetStatus("Установка отменена", 0, Muted);
        }
        catch (Exception ex)
        {
            InstallerLog.Write("Installation failed: " + ex);
            SetStatus("Не удалось установить NEXO", 0, Red);
            MessageBox.Show(this, ex.Message + $"\n\nЛог: {InstallerLog.Path}", "NEXO Setup", MessageBoxButton.OK, MessageBoxImage.Error);
        }
        finally
        {
            if (zip is not null) { try { if (File.Exists(zip)) File.Delete(zip); } catch { } }
            Pulse(false);
            _working = false;
            if (!_installed) Toggle(true);
        }
    }

    private async Task ExtractEmbeddedPayloadAsync(string outputPath, CancellationToken token)
    {
        var asm = Assembly.GetExecutingAssembly();
        await using var input = asm.GetManifestResourceStream(PayloadResource)
            ?? throw new InvalidDataException("В установщике отсутствует встроенный пакет NEXO.");
        await using var output = new FileStream(outputPath, FileMode.Create, FileAccess.Write, FileShare.None, 256 * 1024, true);

        var total = input.CanSeek ? input.Length : 0;
        var buffer = new byte[256 * 1024];
        long done = 0;
        int read;
        while ((read = await input.ReadAsync(buffer.AsMemory(0, buffer.Length), token)) > 0)
        {
            await output.WriteAsync(buffer.AsMemory(0, read), token);
            done += read;
            var p = total > 0 ? 7 + (done / (double)total) * 35 : 25;
            SetStatus(total > 0 ? $"Подготовка файлов… {Size(done)} / {Size(total)}" : "Подготовка файлов…", p);
        }
        await output.FlushAsync(token);
        InstallerLog.Write($"Embedded payload extracted: {done} bytes.");
    }

    private void RegisterInstalledApp(string installDir, string exe, string uninstaller)
    {
        using var key = Registry.CurrentUser.CreateSubKey(UninstallKey, true) ?? throw new InvalidOperationException("Не удалось зарегистрировать NEXO в Windows.");
        key.SetValue("DisplayName", "NEXO");
        key.SetValue("DisplayVersion", "1.1.0-preview");
        key.SetValue("Publisher", "NEXO");
        key.SetValue("InstallLocation", installDir);
        key.SetValue("DisplayIcon", $"{exe},0");
        key.SetValue("UninstallString", $"\"{uninstaller}\"");
        key.SetValue("QuietUninstallString", $"\"{uninstaller}\" /silent");
        key.SetValue("NoModify", 1, RegistryValueKind.DWord);
        key.SetValue("NoRepair", 1, RegistryValueKind.DWord);
        key.SetValue("EstimatedSize", Math.Max(1, DirectorySizeKb(installDir)), RegistryValueKind.DWord);
    }

    private static int DirectorySizeKb(string path)
    {
        long bytes = 0;
        try { bytes = new DirectoryInfo(path).EnumerateFiles("*", SearchOption.AllDirectories).Sum(f => f.Length); } catch { }
        return (int)Math.Min(int.MaxValue, Math.Max(1, bytes / 1024));
    }

    private static void CreateShortcut(string exe, string dir)
    {
        var shortcutPath = IOPath.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory), "NEXO.lnk");
        var shellType = Type.GetTypeFromProgID("WScript.Shell") ?? throw new InvalidOperationException("Windows Script Host недоступен.");
        dynamic shell = Activator.CreateInstance(shellType) ?? throw new InvalidOperationException("Не удалось создать ярлык.");
        dynamic shortcut = shell.CreateShortcut(shortcutPath);
        shortcut.TargetPath = exe;
        shortcut.WorkingDirectory = dir;
        shortcut.Description = "NEXO — удалённое управление компьютером";
        shortcut.IconLocation = exe + ",0";
        shortcut.Save();
    }

    private void Launch()
    {
        try
        {
            var dir = IOPath.GetFullPath(Environment.ExpandEnvironmentVariables(_path.Text.Trim()));
            var exe = IOPath.Combine(dir, "NEXO.exe");
            if (!File.Exists(exe)) throw new FileNotFoundException("NEXO.exe не найден.", exe);
            Process.Start(new ProcessStartInfo(exe) { UseShellExecute = true, WorkingDirectory = dir });
        }
        catch (Exception ex)
        {
            InstallerLog.Write("Launch failed: " + ex);
            MessageBox.Show(this, ex.Message, "NEXO Setup", MessageBoxButton.OK, MessageBoxImage.Warning);
        }
    }

    private void Toggle(bool enabled)
    {
        _path.IsEnabled = enabled;
        _browse.IsEnabled = enabled;
        _desktopShortcut.IsEnabled = enabled;
        _launchAfterInstall.IsEnabled = enabled;
        _install.IsEnabled = enabled;
        _install.Content = enabled ? "Установить NEXO" : "Установка…";
        _close.Content = enabled ? "Закрыть" : "Отменить";
    }

    private void SetStatus(string text, double value, Brush? brush = null)
    {
        Dispatcher.Invoke(() =>
        {
            _status.Text = text;
            _status.Foreground = brush ?? Muted;
            _progress = Math.Clamp(value, 0, 100);
            _percent.Text = $"{Math.Round(_progress):0}%";
            _percent.Foreground = brush ?? Muted;
            UpdateProgress(true);
        });
    }

    private void UpdateProgress(bool animate)
    {
        if (_progressTrack.ActualWidth <= 0) return;
        var target = _progressTrack.ActualWidth * _progress / 100d;
        if (!animate) { _progressFill.Width = target; return; }
        _progressFill.BeginAnimation(WidthProperty, new DoubleAnimation(target, TimeSpan.FromMilliseconds(220)) { EasingFunction = new CubicEase { EasingMode = EasingMode.EaseOut } });
    }

    private void Pulse(bool start)
    {
        if (!start)
        {
            _logoScale.BeginAnimation(ScaleTransform.ScaleXProperty, null);
            _logoScale.BeginAnimation(ScaleTransform.ScaleYProperty, null);
            _logoScale.ScaleX = _logoScale.ScaleY = 1;
            return;
        }
        var a = new DoubleAnimation(1, 1.08, TimeSpan.FromMilliseconds(620)) { AutoReverse = true, RepeatBehavior = RepeatBehavior.Forever, EasingFunction = new SineEase { EasingMode = EasingMode.EaseInOut } };
        _logoScale.BeginAnimation(ScaleTransform.ScaleXProperty, a);
        _logoScale.BeginAnimation(ScaleTransform.ScaleYProperty, a);
    }

    private void Intro(Border shell)
    {
        BeginAnimation(OpacityProperty, new DoubleAnimation(0, 1, TimeSpan.FromMilliseconds(260)) { EasingFunction = new CubicEase { EasingMode = EasingMode.EaseOut } });
        if (shell.RenderTransform is ScaleTransform s)
        {
            var ease = new BackEase { EasingMode = EasingMode.EaseOut, Amplitude = .18 };
            s.BeginAnimation(ScaleTransform.ScaleXProperty, new DoubleAnimation(.965, 1, TimeSpan.FromMilliseconds(430)) { EasingFunction = ease });
            s.BeginAnimation(ScaleTransform.ScaleYProperty, new DoubleAnimation(.965, 1, TimeSpan.FromMilliseconds(430)) { EasingFunction = ease });
        }
    }

    private static Border Card(double l, double t, double r, double b, double top) => new()
    {
        Background = Panel,
        BorderBrush = Border,
        BorderThickness = new Thickness(1),
        CornerRadius = new CornerRadius(12),
        Padding = new Thickness(l, t, r, b),
        Margin = new Thickness(0, top, 0, 0)
    };

    private static CheckBox Check(string text, bool value) => new() { Content = text, IsChecked = value, Foreground = Text, FontSize = 12, VerticalContentAlignment = VerticalAlignment.Center };

    private static Button Btn(string text, bool primary, double width, double height) => new()
    {
        Content = text,
        Width = width,
        Height = height,
        Background = primary ? Blue : Panel2,
        Foreground = Text,
        BorderBrush = primary ? Blue : Border,
        BorderThickness = new Thickness(1),
        FontWeight = primary ? FontWeights.SemiBold : FontWeights.Normal,
        FontSize = 12,
        Cursor = Cursors.Hand,
        Padding = new Thickness(12, 6, 12, 6)
    };

    private static Grid Logo(double size)
    {
        var g = new Grid { Width = size, Height = size };
        g.RowDefinitions.Add(new RowDefinition()); g.RowDefinitions.Add(new RowDefinition());
        g.ColumnDefinitions.Add(new ColumnDefinition()); g.ColumnDefinitions.Add(new ColumnDefinition());
        AddLogo(g, 0, 0, Blue, null); AddLogo(g, 0, 1, Text, null); AddLogo(g, 1, 0, Text, null); AddLogo(g, 1, 1, Panel2, Text);
        return g;
    }

    private static void AddLogo(Grid g, int row, int col, Brush fill, Brush? stroke)
    {
        var r = new Rectangle { Fill = fill, Stroke = stroke, StrokeThickness = stroke is null ? 0 : 1, Margin = new Thickness(col == 0 ? 0 : 2, row == 0 ? 0 : 2, col == 0 ? 2 : 0, row == 0 ? 2 : 0) };
        Grid.SetRow(r, row); Grid.SetColumn(r, col); g.Children.Add(r);
    }

    private static string Size(long n)
    {
        string[] u = { "Б", "КБ", "МБ", "ГБ" };
        double s = n; int i = 0;
        while (s >= 1024 && i < u.Length - 1) { s /= 1024; i++; }
        return $"{s:0.#} {u[i]}";
    }

    private static SolidColorBrush B(string hex)
    {
        var b = new SolidColorBrush((Color)ColorConverter.ConvertFromString(hex));
        b.Freeze();
        return b;
    }
}
