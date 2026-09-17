using Microsoft.Win32;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace MacroPadRemote;

public partial class MainWindow
{
    private sealed record BuiltInMacroIcon(string Name, string Glyph, string Group);

    private static readonly BuiltInMacroIcon[] BuiltInMacroIcons =
    {
        new("Клавиатура", "⌨", "Система"), new("Текст", "T", "Система"), new("Открыть", "↗", "Система"),
        new("Веб", "◎", "Система"), new("Папка", "□", "Система"), new("Список", "≡", "Система"),
        new("Переключить", "⇄", "Система"), new("Подтвердить", "✓", "Система"), new("Отмена", "✕", "Система"),
        new("Домой", "⌂", "Навигация"), new("Назад", "←", "Навигация"), new("Вперёд", "→", "Навигация"),
        new("Вверх", "↑", "Навигация"), new("Вниз", "↓", "Навигация"), new("Вернуться", "↩", "Навигация"),
        new("Обновить", "⟳", "Навигация"), new("Развернуть", "⤢", "Навигация"), new("Свернуть", "⤡", "Навигация"),
        new("Play", "▶", "Медиа"), new("Pause", "Ⅱ", "Медиа"), new("Stop", "■", "Медиа"),
        new("Предыдущий", "◀", "Медиа"), new("Следующий", "▶", "Медиа"), new("Громкость +", "+", "Медиа"),
        new("Громкость −", "−", "Медиа"), new("Mute", "◖", "Медиа"), new("Музыка", "♪", "Медиа"),
        new("Сохранить", "▣", "Работа"), new("Копировать", "▤", "Работа"), new("Вставить", "▥", "Работа"),
        new("Дублировать", "⧉", "Работа"), new("Редактировать", "✎", "Работа"), new("Вырезать", "✂", "Работа"),
        new("Добавить", "⊕", "Работа"), new("Уменьшить", "⊖", "Работа"), new("Окно", "▱", "Работа"),
        new("Сетка", "▦", "Работа"), new("Настройки", "⚙", "Работа")
    };

    private UIElement CreateTileIcon(Tile tile, bool blank)
    {
        var foreground = blank ? Brushes.Gray : Brushes.White;
        if (string.Equals(tile.IconKind, "library", StringComparison.OrdinalIgnoreCase))
        {
            var data = ResolveLibraryIcon(tile.IconValue);
            var bitmap = BitmapFromDataUri(data);
            if (bitmap is not null)
            {
                return new Image
                {
                    Source = bitmap,
                    Width = 42,
                    Height = 42,
                    Stretch = Stretch.Uniform,
                    HorizontalAlignment = HorizontalAlignment.Center,
                    Margin = new Thickness(0, 0, 0, 7)
                };
            }
        }

        var glyph = string.Equals(tile.IconKind, "glyph", StringComparison.OrdinalIgnoreCase) && !string.IsNullOrWhiteSpace(tile.IconValue)
            ? tile.IconValue
            : Glyph(tile);
        return new TextBlock
        {
            Text = glyph,
            FontSize = 26,
            HorizontalAlignment = HorizontalAlignment.Center,
            Margin = new Thickness(0, 0, 0, 7),
            Foreground = foreground
        };
    }

    private string SnapshotIconKind(Tile tile)
    {
        if (string.Equals(tile.IconKind, "glyph", StringComparison.OrdinalIgnoreCase) && !string.IsNullOrWhiteSpace(tile.IconValue)) return "glyph";
        if (string.Equals(tile.IconKind, "library", StringComparison.OrdinalIgnoreCase) && !string.IsNullOrWhiteSpace(ResolveLibraryIcon(tile.IconValue))) return "image";
        return "auto";
    }

    private string SnapshotIconValue(Tile tile)
    {
        return SnapshotIconKind(tile) switch
        {
            "glyph" => tile.IconValue,
            "image" => ResolveLibraryIcon(tile.IconValue),
            _ => ""
        };
    }

    private string ResolveLibraryIcon(string id)
        => _state.IconLibrary.FirstOrDefault(x => x.Id == id)?.DataUri ?? "";

    private void RefreshIconInspector()
    {
        if (InspectorIconPreview is null || InspectorIconStatus is null) return;
        InspectorIconPreview.Child = null;
        var enabled = _selected is not null;
        IconLibraryButton.IsEnabled = enabled;
        IconImportButton.IsEnabled = enabled;
        IconScreenshotButton.IsEnabled = enabled;
        IconResetButton.IsEnabled = enabled;
        if (_selected is null)
        {
            InspectorIconStatus.Text = "Автоматически";
            return;
        }

        var visual = CreateTileIcon(_selected, IsBlank(_selected));
        if (visual is FrameworkElement fe)
        {
            fe.Margin = new Thickness(0);
            fe.VerticalAlignment = VerticalAlignment.Center;
        }
        InspectorIconPreview.Child = visual;
        InspectorIconStatus.Text = _selected.IconKind switch
        {
            "glyph" => "Иконка из библиотеки",
            "library" => _state.IconLibrary.FirstOrDefault(x => x.Id == _selected.IconValue)?.Name ?? "Пользовательская иконка",
            _ => "Автоматически по типу команды"
        };
    }

    private void IconLibrary_Click(object sender, RoutedEventArgs e)
    {
        if (_selected is null) return;
        ShowIconLibraryWindow();
    }

    private void IconImport_Click(object sender, RoutedEventArgs e)
    {
        if (_selected is null) return;
        ImportIconAndAssign();
    }

    private async void IconScreenshot_Click(object sender, RoutedEventArgs e)
    {
        if (_selected is null) return;
        var wasMaximized = WindowState == WindowState.Maximized;
        Hide();
        await Task.Delay(180);
        Rect? region = null;
        BitmapSource? captured = null;
        try
        {
            region = ScreenRegionSelector.SelectRegion();
            if (region is not null)
            {
                await Task.Delay(90);
                captured = ScreenRegionSelector.Capture(region.Value);
            }
        }
        finally
        {
            Show();
            if (wasMaximized) WindowState = WindowState.Maximized;
            Activate();
        }

        if (captured is null) return;
        var data = NormalizeBitmap(captured);
        if (string.IsNullOrWhiteSpace(data)) return;
        var asset = new IconAsset { Name = $"Снимок {DateTime.Now:HH-mm-ss}", DataUri = data };
        _state.IconLibrary.Add(asset);
        _selected.IconKind = "library";
        _selected.IconValue = asset.Id;
        SaveAndBroadcast();
        RefreshInspector();
    }

    private void IconReset_Click(object sender, RoutedEventArgs e)
    {
        if (_selected is null) return;
        _selected.IconKind = "auto";
        _selected.IconValue = "";
        SaveAndBroadcast();
        RefreshInspector();
    }

    private void ImportIconAndAssign()
    {
        if (_selected is null) return;
        var dialog = new OpenFileDialog
        {
            Title = "Добавить иконку в библиотеку",
            Filter = "Изображения|*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.gif|Все файлы|*.*",
            Multiselect = false
        };
        if (dialog.ShowDialog(this) != true) return;
        try
        {
            using var stream = File.OpenRead(dialog.FileName);
            var data = NormalizeImage(stream);
            if (string.IsNullOrWhiteSpace(data)) throw new InvalidOperationException("Не удалось преобразовать изображение.");
            var asset = new IconAsset { Name = Path.GetFileNameWithoutExtension(dialog.FileName), DataUri = data };
            _state.IconLibrary.Add(asset);
            _selected.IconKind = "library";
            _selected.IconValue = asset.Id;
            SaveAndBroadcast();
            RefreshInspector();
        }
        catch (Exception ex)
        {
            MessageBox.Show(this, $"Не удалось импортировать иконку: {ex.Message}", "MacroPad Remote", MessageBoxButton.OK, MessageBoxImage.Warning);
        }
    }

    private void ShowIconLibraryWindow()
    {
        if (_selected is null) return;
        var window = new Window
        {
            Owner = this,
            Title = "Иконки макроса",
            Width = 720,
            Height = 610,
            MinWidth = 580,
            MinHeight = 460,
            WindowStartupLocation = WindowStartupLocation.CenterOwner,
            Background = (Brush)FindResource("Bg")
        };
        var root = new Grid { Margin = new Thickness(16) };
        root.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        root.RowDefinitions.Add(new RowDefinition());
        root.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        var title = new StackPanel();
        title.Children.Add(new TextBlock { Text = "Библиотека иконок", FontSize = 21, FontWeight = FontWeights.SemiBold });
        title.Children.Add(new TextBlock { Text = "Выберите готовую пиктограмму или добавьте своё изображение. Пользовательская библиотека сохраняется на ПК.", Foreground = (Brush)FindResource("Muted"), TextWrapping = TextWrapping.Wrap, Margin = new Thickness(0, 5, 0, 12) });
        root.Children.Add(title);

        var scroll = new ScrollViewer { VerticalScrollBarVisibility = ScrollBarVisibility.Auto };
        var items = new StackPanel();
        scroll.Content = items;
        Grid.SetRow(scroll, 1);
        root.Children.Add(scroll);

        void rebuild()
        {
            items.Children.Clear();
            AddAutomaticIconChoice(items, window);
            foreach (var group in BuiltInMacroIcons.GroupBy(x => x.Group))
            {
                items.Children.Add(new TextBlock { Text = group.Key, FontWeight = FontWeights.SemiBold, Foreground = (Brush)FindResource("Muted"), Margin = new Thickness(0, 12, 0, 6) });
                var wrap = new WrapPanel();
                foreach (var icon in group) AddGlyphChoice(wrap, window, icon);
                items.Children.Add(wrap);
            }
            items.Children.Add(new TextBlock { Text = "Моя библиотека", FontWeight = FontWeights.SemiBold, Foreground = (Brush)FindResource("Muted"), Margin = new Thickness(0, 16, 0, 6) });
            var userWrap = new WrapPanel();
            foreach (var asset in _state.IconLibrary.ToList()) AddImageChoice(userWrap, window, asset, rebuild);
            if (_state.IconLibrary.Count == 0)
                userWrap.Children.Add(new TextBlock { Text = "Пока пусто — импортируйте изображение или создайте иконку снимком экрана.", Foreground = (Brush)FindResource("Muted"), Margin = new Thickness(4, 8, 0, 8) });
            items.Children.Add(userWrap);
        }
        rebuild();

        var footer = new Grid { Margin = new Thickness(0, 12, 0, 0) };
        footer.ColumnDefinitions.Add(new ColumnDefinition());
        footer.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        var add = new Button { Content = "＋ Импортировать изображение", Padding = new Thickness(12, 6, 12, 6), HorizontalAlignment = HorizontalAlignment.Left };
        add.Click += (_, _) => { ImportIconAndAssign(); rebuild(); };
        footer.Children.Add(add);
        var close = new Button { Content = "Закрыть", Width = 100, Height = 32 };
        close.Click += (_, _) => window.Close();
        Grid.SetColumn(close, 1);
        footer.Children.Add(close);
        Grid.SetRow(footer, 2);
        root.Children.Add(footer);
        window.Content = root;
        window.ShowDialog();
    }

    private void AddAutomaticIconChoice(Panel panel, Window owner)
    {
        var button = IconChoiceButton("Авто", new TextBlock { Text = "A", FontSize = 24, FontWeight = FontWeights.Bold, Foreground = Brushes.White });
        button.Click += (_, _) =>
        {
            if (_selected is null) return;
            _selected.IconKind = "auto";
            _selected.IconValue = "";
            SaveAndBroadcast(); RefreshInspector(); owner.Close();
        };
        panel.Children.Add(button);
    }

    private void AddGlyphChoice(Panel panel, Window owner, BuiltInMacroIcon icon)
    {
        var button = IconChoiceButton(icon.Name, new TextBlock { Text = icon.Glyph, FontSize = 25, Foreground = Brushes.White, HorizontalAlignment = HorizontalAlignment.Center });
        button.Click += (_, _) =>
        {
            if (_selected is null) return;
            _selected.IconKind = "glyph";
            _selected.IconValue = icon.Glyph;
            SaveAndBroadcast(); RefreshInspector(); owner.Close();
        };
        panel.Children.Add(button);
    }

    private void AddImageChoice(Panel panel, Window owner, IconAsset asset, Action rebuild)
    {
        var bitmap = BitmapFromDataUri(asset.DataUri);
        var visual = bitmap is null
            ? (UIElement)new TextBlock { Text = "?", FontSize = 24, HorizontalAlignment = HorizontalAlignment.Center }
            : new Image { Source = bitmap, Width = 44, Height = 44, Stretch = Stretch.Uniform };
        var button = IconChoiceButton(asset.Name, visual);
        button.Click += (_, _) =>
        {
            if (_selected is null) return;
            _selected.IconKind = "library";
            _selected.IconValue = asset.Id;
            SaveAndBroadcast(); RefreshInspector(); owner.Close();
        };
        var menu = new ContextMenu();
        var remove = new MenuItem { Header = "Удалить из библиотеки" };
        remove.Click += (_, _) =>
        {
            _state.IconLibrary.RemoveAll(x => x.Id == asset.Id);
            SaveState();
            rebuild();
        };
        menu.Items.Add(remove);
        button.ContextMenu = menu;
        panel.Children.Add(button);
    }

    private Button IconChoiceButton(string name, UIElement visual)
    {
        var stack = new StackPanel { Width = 82 };
        var preview = new Border { Width = 58, Height = 58, Background = (Brush)FindResource("Panel2"), BorderBrush = (Brush)FindResource("Border"), BorderThickness = new Thickness(1), Padding = new Thickness(7), HorizontalAlignment = HorizontalAlignment.Center };
        preview.Child = visual;
        stack.Children.Add(preview);
        stack.Children.Add(new TextBlock { Text = name, TextAlignment = TextAlignment.Center, TextWrapping = TextWrapping.Wrap, FontSize = 9, MaxHeight = 28, Margin = new Thickness(0, 4, 0, 0) });
        return new Button { Content = stack, Width = 92, Height = 100, Margin = new Thickness(3), Padding = new Thickness(2), Background = Brushes.Transparent };
    }

    private static string NormalizeImage(Stream stream)
    {
        var decoder = BitmapDecoder.Create(stream, BitmapCreateOptions.PreservePixelFormat, BitmapCacheOption.OnLoad);
        if (decoder.Frames.Count == 0) return "";
        return NormalizeBitmap(decoder.Frames[0]);
    }

    private static string NormalizeBitmap(BitmapSource source)
    {
        const int size = 96;
        var visual = new DrawingVisual();
        using (var dc = visual.RenderOpen())
        {
            var scale = Math.Min(size / (double)Math.Max(1, source.PixelWidth), size / (double)Math.Max(1, source.PixelHeight));
            var w = source.PixelWidth * scale;
            var h = source.PixelHeight * scale;
            dc.DrawImage(source, new Rect((size - w) / 2, (size - h) / 2, w, h));
        }
        var rendered = new RenderTargetBitmap(size, size, 96, 96, PixelFormats.Pbgra32);
        rendered.Render(visual);
        rendered.Freeze();

        using var pngStream = new MemoryStream();
        var png = new PngBitmapEncoder();
        png.Frames.Add(BitmapFrame.Create(rendered));
        png.Save(pngStream);
        if (pngStream.Length <= 36_000)
            return "data:image/png;base64," + Convert.ToBase64String(pngStream.ToArray());

        var jpegVisual = new DrawingVisual();
        using (var dc = jpegVisual.RenderOpen())
        {
            dc.DrawRectangle(new SolidColorBrush(Color.FromRgb(36, 39, 42)), null, new Rect(0, 0, size, size));
            dc.DrawImage(rendered, new Rect(0, 0, size, size));
        }
        var jpegBitmap = new RenderTargetBitmap(size, size, 96, 96, PixelFormats.Pbgra32);
        jpegBitmap.Render(jpegVisual);
        using var jpgStream = new MemoryStream();
        var jpg = new JpegBitmapEncoder { QualityLevel = 82 };
        jpg.Frames.Add(BitmapFrame.Create(jpegBitmap));
        jpg.Save(jpgStream);
        return "data:image/jpeg;base64," + Convert.ToBase64String(jpgStream.ToArray());
    }

    private static BitmapSource? BitmapFromDataUri(string? value)
    {
        if (string.IsNullOrWhiteSpace(value)) return null;
        try
        {
            var comma = value.IndexOf(',');
            var raw = comma >= 0 ? value[(comma + 1)..] : value;
            var bytes = Convert.FromBase64String(raw);
            using var stream = new MemoryStream(bytes);
            var bitmap = new BitmapImage();
            bitmap.BeginInit();
            bitmap.CacheOption = BitmapCacheOption.OnLoad;
            bitmap.StreamSource = stream;
            bitmap.EndInit();
            bitmap.Freeze();
            return bitmap;
        }
        catch { return null; }
    }
}

public sealed class IconAsset
{
    public string Id { get; set; } = Guid.NewGuid().ToString("N");
    public string Name { get; set; } = "Иконка";
    public string DataUri { get; set; } = "";
}
