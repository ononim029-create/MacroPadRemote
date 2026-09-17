using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.Windows.Media.Effects;
using System.Windows.Shapes;
using Microsoft.Win32;

namespace NexoUninstaller;

internal static class Program
{
    [STAThread]
    public static void Main()
    {
        if (Environment.GetCommandLineArgs().Any(x => string.Equals(x, "/silent", StringComparison.OrdinalIgnoreCase)))
        {
            UninstallCore();
            return;
        }

        var app = new Application { ShutdownMode = ShutdownMode.OnMainWindowClose };
        app.Run(new UninstallWindow());
    }

    internal static void UninstallCore()
    {
        var installDir = AppContext.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar);
        try
        {
            foreach (var p in Process.GetProcessesByName("NEXO"))
            {
                try { p.Kill(true); p.WaitForExit(3000); } catch { }
            }

            var desktopShortcut = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory), "NEXO.lnk");
            try { if (File.Exists(desktopShortcut)) File.Delete(desktopShortcut); } catch { }

            try
            {
                Registry.CurrentUser.DeleteSubKeyTree(@"Software\Microsoft\Windows\CurrentVersion\Uninstall\NEXO", false);
            }
            catch { }

            var escaped = installDir.Replace("'", "''");
            var command = $"Start-Sleep -Milliseconds 900; Remove-Item -LiteralPath '{escaped}' -Recurse -Force -ErrorAction SilentlyContinue";
            Process.Start(new ProcessStartInfo("powershell.exe", $"-NoProfile -WindowStyle Hidden -Command \"{command}\"")
            {
                CreateNoWindow = true,
                UseShellExecute = false
            });
        }
        catch { }
    }
}

internal sealed class UninstallWindow : Window
{
    private static readonly SolidColorBrush Bg = B("#17191B");
    private static readonly SolidColorBrush Panel = B("#1D1F21");
    private static readonly SolidColorBrush Panel2 = B("#24272A");
    private static readonly SolidColorBrush Border = B("#353A3E");
    private static readonly SolidColorBrush Text = B("#F2F2F2");
    private static readonly SolidColorBrush Muted = B("#9DA3A8");
    private static readonly SolidColorBrush Blue = B("#1688FF");

    private readonly Button _remove;
    private readonly TextBlock _status;

    public UninstallWindow()
    {
        Title = "Удаление NEXO";
        Width = 620;
        Height = 420;
        MinWidth = MaxWidth = 620;
        MinHeight = MaxHeight = 420;
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
            CornerRadius = new CornerRadius(18),
            Background = Bg,
            BorderBrush = Border,
            BorderThickness = new Thickness(1),
            Effect = new DropShadowEffect { BlurRadius = 28, ShadowDepth = 8, Opacity = 0.4 }
        };
        Content = shell;

        var grid = new Grid();
        grid.RowDefinitions.Add(new RowDefinition { Height = new GridLength(58) });
        grid.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
        shell.Child = grid;

        var header = new Border { Background = B("#1B1D1F"), BorderBrush = Border, BorderThickness = new Thickness(0, 0, 0, 1), CornerRadius = new CornerRadius(18, 18, 0, 0) };
        header.MouseLeftButtonDown += (_, e) => { if (e.ButtonState == MouseButtonState.Pressed) DragMove(); };
        grid.Children.Add(header);

        var hg = new Grid { Margin = new Thickness(18, 0, 12, 0) };
        hg.ColumnDefinitions.Add(new ColumnDefinition());
        hg.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        header.Child = hg;

        var brand = new StackPanel { Orientation = Orientation.Horizontal, VerticalAlignment = VerticalAlignment.Center };
        hg.Children.Add(brand);
        brand.Children.Add(BuildLogo(27));
        brand.Children.Add(new TextBlock { Text = "NEXO", FontSize = 18, FontWeight = FontWeights.SemiBold, Foreground = Text, VerticalAlignment = VerticalAlignment.Center, Margin = new Thickness(10, 0, 0, 0) });
        brand.Children.Add(new TextBlock { Text = "  Uninstall", FontSize = 11, Foreground = Muted, VerticalAlignment = VerticalAlignment.Center });

        var close = Button("×", Panel2, 38, 32);
        close.FontSize = 20;
        close.Click += (_, _) => Close();
        Grid.SetColumn(close, 1);
        hg.Children.Add(close);

        var body = new Grid { Margin = new Thickness(38, 34, 38, 30) };
        body.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        body.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        body.RowDefinitions.Add(new RowDefinition());
        body.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        Grid.SetRow(body, 1);
        grid.Children.Add(body);

        body.Children.Add(new TextBlock { Text = "Удалить NEXO?", FontSize = 29, FontWeight = FontWeights.SemiBold, Foreground = Text });

        var info = new Border { Background = Panel, BorderBrush = Border, BorderThickness = new Thickness(1), CornerRadius = new CornerRadius(12), Padding = new Thickness(18), Margin = new Thickness(0, 22, 0, 0) };
        Grid.SetRow(info, 1);
        body.Children.Add(info);
        info.Child = new TextBlock
        {
            Text = "Приложение NEXO будет закрыто и удалено с этого компьютера. Ярлык на рабочем столе и запись в списке установленных программ также будут удалены.",
            Foreground = Muted,
            FontSize = 12,
            TextWrapping = TextWrapping.Wrap,
            LineHeight = 20
        };

        _status = new TextBlock { Text = "Версия 1.1 preview", Foreground = Muted, FontSize = 11, VerticalAlignment = VerticalAlignment.Center };
        Grid.SetRow(_status, 3);
        body.Children.Add(_status);

        var buttons = new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Right };
        Grid.SetRow(buttons, 3);
        body.Children.Add(buttons);

        var cancel = Button("Отмена", Panel2, 104, 42);
        cancel.Click += (_, _) => Close();
        buttons.Children.Add(cancel);

        _remove = Button("Удалить NEXO", Blue, 154, 42);
        _remove.Margin = new Thickness(10, 0, 0, 0);
        _remove.FontWeight = FontWeights.SemiBold;
        _remove.Click += Remove_Click;
        buttons.Children.Add(_remove);

        Loaded += (_, _) => BeginAnimation(OpacityProperty, new DoubleAnimation(0, 1, TimeSpan.FromMilliseconds(240)) { EasingFunction = new CubicEase { EasingMode = EasingMode.EaseOut } });
    }

    private async void Remove_Click(object sender, RoutedEventArgs e)
    {
        _remove.IsEnabled = false;
        _status.Text = "Удаление…";
        await System.Threading.Tasks.Task.Delay(180);
        Program.UninstallCore();
        _status.Text = "NEXO удалён";
        await System.Threading.Tasks.Task.Delay(350);
        Application.Current.Shutdown();
    }

    private static Grid BuildLogo(double size)
    {
        var grid = new Grid { Width = size, Height = size };
        grid.RowDefinitions.Add(new RowDefinition());
        grid.RowDefinitions.Add(new RowDefinition());
        grid.ColumnDefinitions.Add(new ColumnDefinition());
        grid.ColumnDefinitions.Add(new ColumnDefinition());
        Add(grid, 0, 0, Blue, null);
        Add(grid, 0, 1, Text, null);
        Add(grid, 1, 0, Text, null);
        Add(grid, 1, 1, Panel2, Text);
        return grid;
    }

    private static void Add(Grid grid, int row, int col, Brush fill, Brush? stroke)
    {
        var r = new Rectangle { Fill = fill, Stroke = stroke, StrokeThickness = stroke is null ? 0 : 1, Margin = new Thickness(col == 0 ? 0 : 2, row == 0 ? 0 : 2, col == 0 ? 2 : 0, row == 0 ? 2 : 0) };
        Grid.SetRow(r, row); Grid.SetColumn(r, col); grid.Children.Add(r);
    }

    private static Button Button(string text, Brush background, double width, double height) => new()
    {
        Content = text,
        Width = width,
        Height = height,
        Background = background,
        Foreground = Text,
        BorderBrush = Border,
        BorderThickness = new Thickness(1),
        Cursor = Cursors.Hand,
        Padding = new Thickness(10, 6, 10, 6)
    };

    private static SolidColorBrush B(string value)
    {
        var b = new SolidColorBrush((Color)ColorConverter.ConvertFromString(value));
        b.Freeze();
        return b;
    }
}
