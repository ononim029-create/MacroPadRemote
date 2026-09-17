using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Interop;
using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace MacroPadRemote;

public sealed class ScreenRegionSelector : Window
{
    private readonly Canvas _canvas = new();
    private readonly Border _selection = new()
    {
        BorderBrush = Brushes.DeepSkyBlue,
        BorderThickness = new Thickness(2),
        Background = new SolidColorBrush(Color.FromArgb(34, 22, 136, 255)),
        Visibility = Visibility.Collapsed
    };
    private Point _start;
    private bool _dragging;

    public Rect? SelectedScreenPixels { get; private set; }

    private ScreenRegionSelector()
    {
        WindowStyle = WindowStyle.None;
        ResizeMode = ResizeMode.NoResize;
        AllowsTransparency = true;
        Background = new SolidColorBrush(Color.FromArgb(96, 0, 0, 0));
        Topmost = true;
        ShowInTaskbar = false;
        Cursor = Cursors.Cross;
        Left = SystemParameters.VirtualScreenLeft;
        Top = SystemParameters.VirtualScreenTop;
        Width = SystemParameters.VirtualScreenWidth;
        Height = SystemParameters.VirtualScreenHeight;
        Content = _canvas;
        _canvas.Children.Add(_selection);

        var hint = new Border
        {
            Background = new SolidColorBrush(Color.FromArgb(220, 25, 27, 29)),
            BorderBrush = new SolidColorBrush(Color.FromRgb(74, 80, 85)),
            BorderThickness = new Thickness(1),
            Padding = new Thickness(12, 8, 12, 8),
            Child = new TextBlock { Text = "Выделите область для иконки • Esc — отмена", Foreground = Brushes.White, FontSize = 14 }
        };
        Canvas.SetLeft(hint, 18);
        Canvas.SetTop(hint, 18);
        _canvas.Children.Add(hint);

        PreviewMouseLeftButtonDown += OnMouseDown;
        PreviewMouseMove += OnMouseMove;
        PreviewMouseLeftButtonUp += OnMouseUp;
        PreviewKeyDown += OnKeyDown;
    }

    public static Rect? SelectRegion()
    {
        var selector = new ScreenRegionSelector();
        selector.ShowDialog();
        return selector.SelectedScreenPixels;
    }

    private void OnMouseDown(object sender, MouseButtonEventArgs e)
    {
        _start = e.GetPosition(_canvas);
        _dragging = true;
        _selection.Visibility = Visibility.Visible;
        Canvas.SetLeft(_selection, _start.X);
        Canvas.SetTop(_selection, _start.Y);
        _selection.Width = 1;
        _selection.Height = 1;
        Mouse.Capture(this);
    }

    private void OnMouseMove(object sender, MouseEventArgs e)
    {
        if (!_dragging) return;
        var p = e.GetPosition(_canvas);
        var x = Math.Min(_start.X, p.X);
        var y = Math.Min(_start.Y, p.Y);
        var w = Math.Abs(p.X - _start.X);
        var h = Math.Abs(p.Y - _start.Y);
        Canvas.SetLeft(_selection, x);
        Canvas.SetTop(_selection, y);
        _selection.Width = Math.Max(1, w);
        _selection.Height = Math.Max(1, h);
    }

    private void OnMouseUp(object sender, MouseButtonEventArgs e)
    {
        if (!_dragging) return;
        _dragging = false;
        Mouse.Capture(null);
        var p = e.GetPosition(_canvas);
        var x1 = Math.Min(_start.X, p.X);
        var y1 = Math.Min(_start.Y, p.Y);
        var x2 = Math.Max(_start.X, p.X);
        var y2 = Math.Max(_start.Y, p.Y);
        if (x2 - x1 < 4 || y2 - y1 < 4)
        {
            SelectedScreenPixels = null;
            Close();
            return;
        }

        var a = PointToScreen(new Point(x1, y1));
        var b = PointToScreen(new Point(x2, y2));
        SelectedScreenPixels = new Rect(a.X, a.Y, Math.Max(1, b.X - a.X), Math.Max(1, b.Y - a.Y));
        Close();
    }

    private void OnKeyDown(object sender, KeyEventArgs e)
    {
        if (e.Key != Key.Escape) return;
        SelectedScreenPixels = null;
        Close();
    }

    public static BitmapSource Capture(Rect screenPixelRect)
    {
        var x = (int)Math.Round(screenPixelRect.X);
        var y = (int)Math.Round(screenPixelRect.Y);
        var width = Math.Max(1, (int)Math.Round(screenPixelRect.Width));
        var height = Math.Max(1, (int)Math.Round(screenPixelRect.Height));

        var screenDc = GetDC(IntPtr.Zero);
        if (screenDc == IntPtr.Zero) throw new InvalidOperationException("Не удалось получить изображение экрана.");
        var memoryDc = CreateCompatibleDC(screenDc);
        if (memoryDc == IntPtr.Zero)
        {
            ReleaseDC(IntPtr.Zero, screenDc);
            throw new InvalidOperationException("Не удалось создать буфер снимка.");
        }
        var bitmap = CreateCompatibleBitmap(screenDc, width, height);
        if (bitmap == IntPtr.Zero)
        {
            DeleteDC(memoryDc);
            ReleaseDC(IntPtr.Zero, screenDc);
            throw new InvalidOperationException("Не удалось создать снимок выбранной области.");
        }

        var old = SelectObject(memoryDc, bitmap);
        try
        {
            if (!BitBlt(memoryDc, 0, 0, width, height, screenDc, x, y, 0x00CC0020 | 0x40000000))
                throw new InvalidOperationException("Windows не разрешила захват выбранной области.");
            var source = Imaging.CreateBitmapSourceFromHBitmap(bitmap, IntPtr.Zero, Int32Rect.Empty, BitmapSizeOptions.FromEmptyOptions());
            source.Freeze();
            return source;
        }
        finally
        {
            SelectObject(memoryDc, old);
            DeleteObject(bitmap);
            DeleteDC(memoryDc);
            ReleaseDC(IntPtr.Zero, screenDc);
        }
    }

    [DllImport("user32.dll")] private static extern IntPtr GetDC(IntPtr hWnd);
    [DllImport("user32.dll")] private static extern int ReleaseDC(IntPtr hWnd, IntPtr hDc);
    [DllImport("gdi32.dll")] private static extern IntPtr CreateCompatibleDC(IntPtr hDc);
    [DllImport("gdi32.dll")] private static extern bool DeleteDC(IntPtr hDc);
    [DllImport("gdi32.dll")] private static extern IntPtr CreateCompatibleBitmap(IntPtr hDc, int width, int height);
    [DllImport("gdi32.dll")] private static extern IntPtr SelectObject(IntPtr hDc, IntPtr hObject);
    [DllImport("gdi32.dll")] private static extern bool DeleteObject(IntPtr hObject);
    [DllImport("gdi32.dll", SetLastError = true)] private static extern bool BitBlt(IntPtr hDestDc, int x, int y, int width, int height, IntPtr hSrcDc, int xSrc, int ySrc, int rop);
}
