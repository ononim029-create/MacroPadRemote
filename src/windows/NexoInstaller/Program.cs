using System;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.Windows.Media.Effects;
using System.Windows.Shapes;
using Microsoft.Win32;

namespace NexoInstaller;

internal static class Program
{
    [STAThread]
    public static void Main()
    {
        var app = new Application
        {
            ShutdownMode = ShutdownMode.OnMainWindowClose
        };
        app.Run(new InstallerWindow());
    }
}

internal sealed class InstallerWindow : Window
{
    private const string PackageUrl = "https://github.com/ononim029-create/MacroPadRemote/releases/download/preview/NEXO-win-x64.zip";

    private static readonly SolidColorBrush Bg = Brush("#17191B");
    private static readonly SolidColorBrush Panel = Brush("#1D1F21");
    private static readonly SolidColorBrush Panel2 = Brush("#24272A");
    private static readonly SolidColorBrush Hover = Brush("#2C3034");
    private static readonly SolidColorBrush BorderBrush = Brush("#353A3E");
    private static readonly SolidColorBrush TextBrush = Brush("#F2F2F2");
    private static readonly SolidColorBrush Muted = Brush("#9DA3A8");
    private static readonly SolidColorBrush Blue = Brush("#1688FF");
    private static readonly SolidColorBrush Green = Brush("#62D16F");

    private readonly Border _root;
    private readonly TextBox _pathBox;
    private readonly CheckBox _desktopShortcut;
    private readonly CheckBox _launchAfterInstall;
    private readonly TextBlock _status;
    private readonly TextBlock _progressText;
    private readonly Border _progressTrack;
    private readonly Border _progressFill;
    private readonly Button _installButton;
    private readonly Button _browseButton;
    private readonly ScaleTransform _logoScale = new(1, 1);
    private readonly CancellationTokenSource _cts = new();

    private bool _installing;
    private bool _installed;
    private double _progress;

    public InstallerWindow()
    {
        Title = "NEXO Setup";
        Width = 720;
        Height = 600;
        MinWidth = 720;
        MinHeight = 600;
        MaxWidth = 720;
        MaxHeight = 600;
        WindowStartupLocation = WindowStartupLocation.CenterScreen;
        WindowStyle = WindowStyle.None;
        ResizeMode = ResizeMode.NoResize;
        AllowsTransparency = true;
        Background = Brushes.Transparent;
        Foreground = TextBrush;
        FontFamily = new FontFamily("Segoe UI");
        Opacity = 0;

        _root = new Border
        {
            CornerRadius = new CornerRadius(18),
            Background = Bg,
            BorderBrush = BorderBrush,
            BorderThickness = new Thickness(1),
            Effect = new DropShadowEffect
            {
                BlurRadius = 28,
                ShadowDepth = 8,
                Opacity = 0.42,
                Color = Colors.Black
            },
            RenderTransformOrigin = new Point(0.5, 0.5),
            RenderTransform = new ScaleTransform(0.965, 0.965)
        };
        Content = _root;

        var layout = new Grid();
        layout.RowDefinitions.Add(new RowDefinition { Height = new GridLength(60) });
        layout.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
        _root.Child = layout;

        layout.Children.Add(BuildHeader());

        var content = new Grid { Margin = new Thickness(38, 30, 38, 30) };
        Grid.SetRow(content, 1);
        content.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        content.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        content.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        content.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        content.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        content.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
        content.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        layout.Children.Add(content);

        var hero = new StackPanel();
        hero.Children.Add(new TextBlock
        {
            Text = "Установка NEXO",
            FontSize = 30,
            FontWeight = FontWeights.SemiBold,
            Foreground = TextBrush
        });
        hero.Children.Add(new TextBlock
        {
            Text = "Удалённое управление компьютером с телефона и планшета",
            FontSize = 13,
            Foreground = Muted,
            Margin = new Thickness(0, 7, 0, 0)
        });
        content.Children.Add(hero);

        var folderCard = new Border
        {
            Background = Panel,
            BorderBrush = BorderBrush,
            BorderThickness = new Thickness(1),
            CornerRadius = new CornerRadius(12),
            Padding = new Thickness(18, 15, 18, 16),
            Margin = new Thickness(0, 24, 0, 0)
        };
        Grid.SetRow(folderCard, 1);
        content.Children.Add(folderCard);

        var folderStack = new StackPanel();
        folderCard.Child = folderStack;
        folderStack.Children.Add(new TextBlock
        {
            Text = "Папка установки",
            FontSize = 12,
            FontWeight = FontWeights.SemiBold,
            Foreground = TextBrush,
            Margin = new Thickness(0, 0, 0, 9)
        });

        var folderGrid = new Grid();
        folderGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        folderGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(104) });
        folderStack.Children.Add(folderGrid);

        _pathBox = new TextBox
        {
            Text = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "NEXO"),
            Height = 38,
            Background = Brush("#111315"),
            Foreground = TextBrush,
            CaretBrush = Brushes.White,
            BorderBrush = BorderBrush,
            BorderThickness = new Thickness(1),
            Padding = new Thickness(11, 7, 11, 7),
            FontSize = 12,
            VerticalContentAlignment = VerticalAlignment.Center
        };
        folderGrid.Children.Add(_pathBox);

        _browseButton = MakeButton("Обзор", false, 94, 38);
        _browseButton.Margin = new Thickness(10, 0, 0, 0);
        _browseButton.Click += Browse_Click;
        Grid.SetColumn(_browseButton, 1);
        folderGrid.Children.Add(_browseButton);

        var optionsCard = new Border
        {
            Background = Panel,
            BorderBrush = BorderBrush,
            BorderThickness = new Thickness(1),
            CornerRadius = new CornerRadius(12),
            Padding = new Thickness(18, 14, 18, 14),
            Margin = new Thickness(0, 12, 0, 0)
        };
        Grid.SetRow(optionsCard, 2);
        content.Children.Add(optionsCard);

        var options = new StackPanel();
        optionsCard.Child = options;
        _desktopShortcut = MakeCheckBox("Создать ярлык NEXO на рабочем столе", true);
        _launchAfterInstall = MakeCheckBox("Запустить NEXO после установки", true);
        _launchAfterInstall.Margin = new Thickness(0, 10, 0, 0);
        options.Children.Add(_desktopShortcut);
        options.Children.Add(_launchAfterInstall);

        var progressBlock = new Grid { Margin = new Thickness(0, 24, 0, 0) };
        progressBlock.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        progressBlock.RowDefinitions.Add(new RowDefinition { Height = new GridLength(10) });
        progressBlock.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        progressBlock.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        Grid.SetRow(progressBlock, 3);
        content.Children.Add(progressBlock);

        _status = new TextBlock
        {
            Text = "Готово к установке",
            Foreground = Muted,
            FontSize = 12
        };
        progressBlock.Children.Add(_status);

        _progressText = new TextBlock
        {
            Text = "0%",
            Foreground = Muted,
            FontSize = 12,
            HorizontalAlignment = HorizontalAlignment.Right
        };
        Grid.SetColumn(_progressText, 1);
        progressBlock.Children.Add(_progressText);

        _progressTrack = new Border
        {
            Height = 7,
            Background = Panel2,
            CornerRadius = new CornerRadius(4),
            Margin = new Thickness(0, 9, 0, 0),
            ClipToBounds = true
        };
        Grid.SetRow(_progressTrack, 1);
        Grid.SetColumnSpan(_progressTrack, 2);
        progressBlock.Children.Add(_progressTrack);

        _progressFill = new Border
        {
            Width = 0,
            HorizontalAlignment = HorizontalAlignment.Left,
            Background = Blue,
            CornerRadius = new CornerRadius(4)
        };
        _progressTrack.Child = _progressFill;
        _progressTrack.SizeChanged += (_, _) => UpdateProgressVisual(false);

        var details = new TextBlock
        {
            Text = "Версия 1.1 preview  •  Windows x64  •  установка без прав администратора",
            Foreground = Brush("#737A80"),
            FontSize = 10,
            Margin = new Thickness(0, 14, 0, 0)
        };
        Grid.SetRow(details, 4);
        content.Children.Add(details);

        var footer = new Grid { Margin = new Thickness(0, 28, 0, 0) };
        footer.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        footer.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        Grid.SetRow(footer, 6);
        content.Children.Add(footer);

        var cancel = MakeButton("Закрыть", false, 108, 42);
        cancel.Click += (_, _) =>
        {
            if (_installing)
            {
                _cts.Cancel();
                return;
            }
            Close();
        };
        footer.Children.Add(cancel);

        _installButton = MakeButton("Установить NEXO", true, 184, 42);
        _installButton.Click += InstallButton_Click;
        Grid.SetColumn(_installButton, 1);
        footer.Children.Add(_installButton);

        Loaded += OnLoaded;
        Closing += (_, _) => _cts.Cancel();
    }

    private UIElement BuildHeader()
    {
        var header = new Border
        {
            Background = Brush("#1B1D1F"),
            BorderBrush = BorderBrush,
            BorderThickness = new Thickness(0, 0, 0, 1),
            CornerRadius = new CornerRadius(18, 18, 0, 0)
        };
        header.MouseLeftButtonDown += (_, e) =>
        {
            if (e.ButtonState == MouseButtonState.Pressed)
                DragMove();
        };

        var grid = new Grid { Margin = new Thickness(18, 0, 12, 0) };
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        header.Child = grid;

        var brand = new StackPanel
        {
            Orientation = Orientation.Horizontal,
            VerticalAlignment = VerticalAlignment.Center
        };
        grid.Children.Add(brand);

        var mark = BuildLogo(28);
        mark.Margin = new Thickness(0, 0, 11, 0);
        mark.RenderTransformOrigin = new Point(0.5, 0.5);
        mark.RenderTransform = _logoScale;
        brand.Children.Add(mark);

        brand.Children.Add(new TextBlock
        {
            Text = "NEXO",
            FontSize = 18,
            FontWeight = FontWeights.SemiBold,
            Foreground = TextBrush,
            VerticalAlignment = VerticalAlignment.Center
        });
        brand.Children.Add(new TextBlock
        {
            Text = "  Setup v1.1",
            FontSize = 11,
            Foreground = Muted,
            VerticalAlignment = VerticalAlignment.Center
        });

        var close = MakeButton("×", false, 38, 32);
        close.FontSize = 20;
        close.Padding = new Thickness(0);
        close.Click += (_, _) =>
        {
            if (_installing)
                _cts.Cancel();
            else
                Close();
        };
        Grid.SetColumn(close, 1);
        grid.Children.Add(close);
        return header;
    }

    private static Grid BuildLogo(double size)
    {
        var grid = new Grid { Width = size, Height = size };
        grid.RowDefinitions.Add(new RowDefinition());
        grid.RowDefinitions.Add(new RowDefinition());
        grid.ColumnDefinitions.Add(new ColumnDefinition());
        grid.ColumnDefinitions.Add(new ColumnDefinition());

        AddLogoCell(grid, 0, 0, Blue, null);
        AddLogoCell(grid, 0, 1, TextBrush, null);
        AddLogoCell(grid, 1, 0, TextBrush, null);
        AddLogoCell(grid, 1, 1, Panel2, TextBrush);
        return grid;
    }

    private static void AddLogoCell(Grid grid, int row, int column, Brush fill, Brush? stroke)
    {
        var rect = new Rectangle
        {
            Fill = fill,
            Stroke = stroke,
            StrokeThickness = stroke is null ? 0 : 1,
            Margin = new Thickness(column == 0 ? 0 : 2, row == 0 ? 0 : 2, column == 0 ? 2 : 0, row == 0 ? 2 : 0)
        };
        Grid.SetRow(rect, row);
        Grid.SetColumn(rect, column);
        grid.Children.Add(rect);
    }

    private static CheckBox MakeCheckBox(string text, bool value)
    {
        return new CheckBox
        {
            Content = text,
            IsChecked = value,
            Foreground = TextBrush,
            FontSize = 12,
            VerticalContentAlignment = VerticalAlignment.Center
        };
    }

    private static Button MakeButton(string text, bool primary, double width, double height)
    {
        var button = new Button
        {
            Content = text,
            Width = width,
            Height = height,
            Background = primary ? Blue : Panel2,
            Foreground = TextBrush,
            BorderBrush = primary ? Blue : BorderBrush,
            BorderThickness = new Thickness(1),
            FontWeight = primary ? FontWeights.SemiBold : FontWeights.Normal,
            FontSize = 12,
            Cursor = Cursors.Hand,
            Padding = new Thickness(12, 6, 12, 6),
            HorizontalContentAlignment = HorizontalAlignment.Center,
            VerticalContentAlignment = VerticalAlignment.Center
        };

        var template = new ControlTemplate(typeof(Button));
        var border = new FrameworkElementFactory(typeof(Border));
        border.Name = "Root";
        border.SetBinding(Border.BackgroundProperty, new System.Windows.Data.Binding("Background") { RelativeSource = new System.Windows.Data.RelativeSource(System.Windows.Data.RelativeSourceMode.TemplatedParent) });
        border.SetBinding(Border.BorderBrushProperty, new System.Windows.Data.Binding("BorderBrush") { RelativeSource = new System.Windows.Data.RelativeSource(System.Windows.Data.RelativeSourceMode.TemplatedParent) });
        border.SetBinding(Border.BorderThicknessProperty, new System.Windows.Data.Binding("BorderThickness") { RelativeSource = new System.Windows.Data.RelativeSource(System.Windows.Data.RelativeSourceMode.TemplatedParent) });
        border.SetValue(Border.CornerRadiusProperty, new CornerRadius(8));

        var presenter = new FrameworkElementFactory(typeof(ContentPresenter));
        presenter.SetValue(HorizontalAlignmentProperty, HorizontalAlignment.Center);
        presenter.SetValue(VerticalAlignmentProperty, VerticalAlignment.Center);
        border.AppendChild(presenter);
        template.VisualTree = border;

        var hover = new Trigger { Property = Button.IsMouseOverProperty, Value = true };
        hover.Setters.Add(new Setter(Border.BackgroundProperty, primary ? Brush("#2B96FF") : Hover, "Root"));
        hover.Setters.Add(new Setter(Border.BorderBrushProperty, primary ? Brush("#2B96FF") : Brush("#5B6166"), "Root"));
        template.Triggers.Add(hover);

        var pressed = new Trigger { Property = Button.IsPressedProperty, Value = true };
        pressed.Setters.Add(new Setter(UIElement.OpacityProperty, 0.76, "Root"));
        template.Triggers.Add(pressed);

        var disabled = new Trigger { Property = Button.IsEnabledProperty, Value = false };
        disabled.Setters.Add(new Setter(UIElement.OpacityProperty, 0.42, "Root"));
        template.Triggers.Add(disabled);

        button.Template = template;
        return button;
    }

    private void OnLoaded(object sender, RoutedEventArgs e)
    {
        var fade = new DoubleAnimation(0, 1, TimeSpan.FromMilliseconds(260))
        {
            EasingFunction = new CubicEase { EasingMode = EasingMode.EaseOut }
        };
        BeginAnimation(OpacityProperty, fade);

        if (_root.RenderTransform is ScaleTransform scale)
        {
            var ease = new BackEase { EasingMode = EasingMode.EaseOut, Amplitude = 0.18 };
            scale.BeginAnimation(ScaleTransform.ScaleXProperty, new DoubleAnimation(0.965, 1, TimeSpan.FromMilliseconds(430)) { EasingFunction = ease });
            scale.BeginAnimation(ScaleTransform.ScaleYProperty, new DoubleAnimation(0.965, 1, TimeSpan.FromMilliseconds(430)) { EasingFunction = ease });
        }
    }

    private void Browse_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new OpenFolderDialog
        {
            Title = "Выберите папку установки NEXO",
            InitialDirectory = Directory.Exists(_pathBox.Text)
                ? _pathBox.Text
                : Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData)
        };
        if (dialog.ShowDialog(this) == true)
            _pathBox.Text = dialog.FolderName;
    }

    private async void InstallButton_Click(object sender, RoutedEventArgs e)
    {
        if (_installed)
        {
            LaunchInstalledApp();
            return;
        }

        if (_installing)
            return;

        await InstallAsync();
    }

    private async Task InstallAsync()
    {
        _installing = true;
        ToggleInputs(false);
        StartLogoPulse();
        string? tempZip = null;

        try
        {
            var installDir = Path.GetFullPath(Environment.ExpandEnvironmentVariables(_pathBox.Text.Trim()));
            if (string.IsNullOrWhiteSpace(installDir))
                throw new InvalidOperationException("Укажите папку установки.");

            if (Process.GetProcessesByName("NEXO").Any(p => p.Id != Environment.ProcessId))
                throw new InvalidOperationException("Закройте запущенный NEXO перед обновлением или установкой.");

            SetStatus("Подготовка установки…", 4);
            tempZip = Path.Combine(Path.GetTempPath(), $"NEXO-{Guid.NewGuid():N}.zip");

            using (var client = new HttpClient { Timeout = TimeSpan.FromMinutes(20) })
            using (var response = await client.GetAsync(PackageUrl, HttpCompletionOption.ResponseHeadersRead, _cts.Token))
            {
                response.EnsureSuccessStatusCode();
                var total = response.Content.Headers.ContentLength;
                await using var input = await response.Content.ReadAsStreamAsync(_cts.Token);
                await using var output = new FileStream(tempZip, FileMode.Create, FileAccess.Write, FileShare.None, 128 * 1024, true);
                var buffer = new byte[128 * 1024];
                long readTotal = 0;
                int read;
                while ((read = await input.ReadAsync(buffer.AsMemory(0, buffer.Length), _cts.Token)) > 0)
                {
                    await output.WriteAsync(buffer.AsMemory(0, read), _cts.Token);
                    readTotal += read;
                    if (total is > 0)
                    {
                        var pct = 8 + (readTotal / (double)total.Value) * 64;
                        SetStatus($"Загрузка NEXO…  {FormatBytes(readTotal)} / {FormatBytes(total.Value)}", pct);
                    }
                }
            }

            SetStatus("Распаковка файлов…", 78);
            await Task.Run(() =>
            {
                _cts.Token.ThrowIfCancellationRequested();
                if (Directory.Exists(installDir))
                    Directory.Delete(installDir, true);
                Directory.CreateDirectory(installDir);
                ZipFile.ExtractToDirectory(tempZip, installDir, true);
            }, _cts.Token);

            var exePath = Path.Combine(installDir, "NEXO.exe");
            if (!File.Exists(exePath))
                throw new InvalidDataException("В пакете установки не найден NEXO.exe.");

            SetStatus("Создание ярлыков…", 91);
            if (_desktopShortcut.IsChecked == true)
                await Task.Run(() => CreateDesktopShortcut(exePath, installDir), _cts.Token);

            SetStatus("NEXO установлен", 100, Green);
            _installed = true;
            _installButton.Content = "Открыть NEXO";
            _installButton.IsEnabled = true;

            if (_launchAfterInstall.IsChecked == true)
                LaunchInstalledApp();
        }
        catch (OperationCanceledException)
        {
            SetStatus("Установка отменена", 0, Muted);
        }
        catch (Exception ex)
        {
            SetStatus("Не удалось установить NEXO", 0, Brush("#FF6B6B"));
            MessageBox.Show(this, ex.Message, "NEXO Setup", MessageBoxButton.OK, MessageBoxImage.Error);
        }
        finally
        {
            if (tempZip is not null)
            {
                try { if (File.Exists(tempZip)) File.Delete(tempZip); }
                catch { }
            }

            StopLogoPulse();
            _installing = false;
            if (!_installed)
                ToggleInputs(true);
        }
    }

    private void ToggleInputs(bool enabled)
    {
        _pathBox.IsEnabled = enabled;
        _browseButton.IsEnabled = enabled;
        _desktopShortcut.IsEnabled = enabled;
        _launchAfterInstall.IsEnabled = enabled;
        _installButton.IsEnabled = enabled;
        if (!enabled)
            _installButton.Content = "Установка…";
        else if (!_installed)
            _installButton.Content = "Установить NEXO";
    }

    private void SetStatus(string text, double progress, Brush? statusBrush = null)
    {
        Dispatcher.Invoke(() =>
        {
            _status.Text = text;
            _status.Foreground = statusBrush ?? Muted;
            _progress = Math.Clamp(progress, 0, 100);
            _progressText.Text = $"{Math.Round(_progress):0}%";
            _progressText.Foreground = statusBrush ?? Muted;
            UpdateProgressVisual(true);
        });
    }

    private void UpdateProgressVisual(bool animate)
    {
        if (_progressTrack.ActualWidth <= 0)
            return;

        var target = _progressTrack.ActualWidth * (_progress / 100d);
        if (!animate)
        {
            _progressFill.Width = target;
            return;
        }

        var animation = new DoubleAnimation(target, TimeSpan.FromMilliseconds(220))
        {
            EasingFunction = new CubicEase { EasingMode = EasingMode.EaseOut }
        };
        _progressFill.BeginAnimation(WidthProperty, animation, HandoffBehavior.SnapshotAndReplace);
    }

    private void StartLogoPulse()
    {
        var pulse = new DoubleAnimation(1, 1.08, TimeSpan.FromMilliseconds(620))
        {
            AutoReverse = true,
            RepeatBehavior = RepeatBehavior.Forever,
            EasingFunction = new SineEase { EasingMode = EasingMode.EaseInOut }
        };
        _logoScale.BeginAnimation(ScaleTransform.ScaleXProperty, pulse);
        _logoScale.BeginAnimation(ScaleTransform.ScaleYProperty, pulse);
    }

    private void StopLogoPulse()
    {
        _logoScale.BeginAnimation(ScaleTransform.ScaleXProperty, null);
        _logoScale.BeginAnimation(ScaleTransform.ScaleYProperty, null);
        _logoScale.ScaleX = 1;
        _logoScale.ScaleY = 1;
    }

    private void LaunchInstalledApp()
    {
        try
        {
            var installDir = Path.GetFullPath(Environment.ExpandEnvironmentVariables(_pathBox.Text.Trim()));
            var exe = Path.Combine(installDir, "NEXO.exe");
            if (!File.Exists(exe))
                throw new FileNotFoundException("NEXO.exe не найден.", exe);

            Process.Start(new ProcessStartInfo(exe)
            {
                UseShellExecute = true,
                WorkingDirectory = installDir
            });
        }
        catch (Exception ex)
        {
            MessageBox.Show(this, ex.Message, "NEXO Setup", MessageBoxButton.OK, MessageBoxImage.Warning);
        }
    }

    private static void CreateDesktopShortcut(string exePath, string workingDirectory)
    {
        var desktop = Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory);
        var shortcutPath = Path.Combine(desktop, "NEXO.lnk");
        var shellType = Type.GetTypeFromProgID("WScript.Shell") ?? throw new InvalidOperationException("Windows Script Host недоступен.");
        dynamic shell = Activator.CreateInstance(shellType) ?? throw new InvalidOperationException("Не удалось создать ярлык.");
        dynamic shortcut = shell.CreateShortcut(shortcutPath);
        shortcut.TargetPath = exePath;
        shortcut.WorkingDirectory = workingDirectory;
        shortcut.Description = "NEXO — удалённое управление компьютером";
        shortcut.IconLocation = exePath + ",0";
        shortcut.Save();
    }

    private static string FormatBytes(long value)
    {
        string[] units = { "Б", "КБ", "МБ", "ГБ" };
        double size = value;
        var index = 0;
        while (size >= 1024 && index < units.Length - 1)
        {
            size /= 1024;
            index++;
        }
        return $"{size:0.#} {units[index]}";
    }

    private static SolidColorBrush Brush(string hex)
    {
        var brush = new SolidColorBrush((Color)ColorConverter.ConvertFromString(hex));
        brush.Freeze();
        return brush;
    }
}
