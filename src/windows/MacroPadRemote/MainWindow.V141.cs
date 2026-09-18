using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Interop;
using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace MacroPadRemote;

public sealed class V141AppChoice
{
    public string Name { get; init; } = "";
    public ImageSource? Icon { get; init; }
    public string Path { get; init; } = "";
    public override string ToString() => Name;
}

public sealed class V141LinkedDevice
{
    public string ServerId { get; set; } = "";
    public string Name { get; set; } = "NEXO PC";
    public bool Enabled { get; set; } = true;
    public DateTime LastSyncUtc { get; set; } = DateTime.MinValue;
    public DateTime LastRemoteUpdateUtc { get; set; } = DateTime.MinValue;
}

public partial class MainWindow
{
    private string? V141PromptNewProfileName(Window? owner = null)
    {
        while (true)
        {
            var name = Prompt("Новый профиль", "");
            if (name is null) return null;
            name = name.Trim();
            if (name.Length > 0) return name;
            MessageBox.Show(owner ?? this, "Введите название профиля.", "NEXO", MessageBoxButton.OK, MessageBoxImage.Information);
        }
    }

    private List<V141AppChoice> V141RunningApplications()
    {
        var result = new List<V141AppChoice>
        {
            new() { Name = "Нет", Path = "" }
        };

        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var process in Process.GetProcesses())
        {
            try
            {
                var rawName = process.ProcessName;
                if (string.IsNullOrWhiteSpace(rawName)) continue;
                var name = V14NormalizeExeName(rawName);
                if (string.IsNullOrWhiteSpace(name) || !seen.Add(name)) continue;

                string path = "";
                try { path = process.MainModule?.FileName ?? ""; } catch { }

                result.Add(new V141AppChoice
                {
                    Name = name,
                    Path = path,
                    Icon = string.IsNullOrWhiteSpace(path) ? null : V141SmallIcon(path)
                });
            }
            catch { }
            finally
            {
                process.Dispose();
            }
        }

        return result
            .Skip(1)
            .OrderBy(x => x.Name, StringComparer.OrdinalIgnoreCase)
            .Prepend(result[0])
            .ToList();
    }

    private ComboBox V141ApplicationCombo(IReadOnlyList<V141AppChoice> apps)
    {
        var template = new DataTemplate(typeof(V141AppChoice));
        var row = new FrameworkElementFactory(typeof(StackPanel));
        row.SetValue(StackPanel.OrientationProperty, Orientation.Horizontal);

        var image = new FrameworkElementFactory(typeof(Image));
        image.SetValue(FrameworkElement.WidthProperty, 18.0);
        image.SetValue(FrameworkElement.HeightProperty, 18.0);
        image.SetValue(FrameworkElement.MarginProperty, new Thickness(0, 0, 8, 0));
        image.SetValue(Image.StretchProperty, Stretch.Uniform);
        image.SetBinding(Image.SourceProperty, new Binding(nameof(V141AppChoice.Icon)));
        row.AppendChild(image);

        var text = new FrameworkElementFactory(typeof(TextBlock));
        text.SetValue(TextBlock.VerticalAlignmentProperty, VerticalAlignment.Center);
        text.SetValue(TextBlock.ForegroundProperty, Brushes.White);
        text.SetBinding(TextBlock.TextProperty, new Binding(nameof(V141AppChoice.Name)));
        row.AppendChild(text);
        template.VisualTree = row;

        var combo = new ComboBox
        {
            IsEditable = true,
            IsTextSearchEnabled = true,
            ItemsSource = apps,
            ItemTemplate = template,
            Height = 34,
            Background = new SolidColorBrush(Color.FromRgb(44, 48, 52)),
            Foreground = Brushes.White,
            BorderBrush = new SolidColorBrush(Color.FromRgb(75, 81, 86))
        };
        TextSearch.SetTextPath(combo, nameof(V141AppChoice.Name));
        return combo;
    }

    private static ImageSource? V141SmallIcon(string executablePath)
    {
        try
        {
            var info = new SHFILEINFO();
            var result = SHGetFileInfo(
                executablePath,
                0,
                ref info,
                (uint)Marshal.SizeOf<SHFILEINFO>(),
                SHGFI_ICON | SHGFI_SMALLICON);

            if (result == IntPtr.Zero || info.hIcon == IntPtr.Zero) return null;
            try
            {
                var source = Imaging.CreateBitmapSourceFromHIcon(
                    info.hIcon,
                    Int32Rect.Empty,
                    BitmapSizeOptions.FromWidthAndHeight(18, 18));
                source.Freeze();
                return source;
            }
            finally
            {
                DestroyIcon(info.hIcon);
            }
        }
        catch
        {
            return null;
        }
    }

    private V141LinkedDevice V141UpsertLinkedDevice(string serverId, string name, DateTime? remoteUpdatedUtc = null)
    {
        _state.LinkedDevices ??= new List<V141LinkedDevice>();
        var item = _state.LinkedDevices.FirstOrDefault(x => string.Equals(x.ServerId, serverId, StringComparison.Ordinal));
        if (item is null)
        {
            item = new V141LinkedDevice { ServerId = serverId, Name = string.IsNullOrWhiteSpace(name) ? "NEXO PC" : name };
            _state.LinkedDevices.Add(item);
        }
        else if (!string.IsNullOrWhiteSpace(name))
        {
            item.Name = name;
        }

        item.Enabled = true;
        if (remoteUpdatedUtc is not null)
            item.LastRemoteUpdateUtc = remoteUpdatedUtc.Value.ToUniversalTime();
        return item;
    }

    private IReadOnlyList<V141LinkedDevice> V141ActiveLinkedDevices()
    {
        _state.LinkedDevices ??= new List<V141LinkedDevice>();
        return _state.LinkedDevices
            .Where(x => x.Enabled && !string.IsNullOrWhiteSpace(x.ServerId)
                && !string.Equals(x.ServerId, _state.ServerId, StringComparison.Ordinal))
            .ToList();
    }

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Auto)]
    private struct SHFILEINFO
    {
        public IntPtr hIcon;
        public int iIcon;
        public uint dwAttributes;

        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 260)]
        public string szDisplayName;

        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 80)]
        public string szTypeName;
    }

    private const uint SHGFI_ICON = 0x000000100;
    private const uint SHGFI_SMALLICON = 0x000000001;

    [DllImport("shell32.dll", CharSet = CharSet.Auto)]
    private static extern IntPtr SHGetFileInfo(
        string pszPath,
        uint dwFileAttributes,
        ref SHFILEINFO psfi,
        uint cbFileInfo,
        uint uFlags);

    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool DestroyIcon(IntPtr hIcon);
}
