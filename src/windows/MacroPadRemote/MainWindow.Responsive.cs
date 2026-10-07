using System;
using System.Windows;
using System.Windows.Controls;

namespace MacroPadRemote;

public partial class MainWindow
{
    private bool _responsiveWindowInitialized;
    private int _responsiveInspectorMode = -1;

    private T? ResponsiveElement<T>(string name) where T : class
        => FindName(name) as T;

    private void ResponsiveWindow_Loaded(object sender, RoutedEventArgs e)
    {
        if (!_responsiveWindowInitialized)
        {
            _responsiveWindowInitialized = true;
            FitInitialWindowToWorkArea();
        }

        ApplyResponsiveLaptopLayout();
    }

    private void ResponsiveWindow_SizeChanged(object sender, SizeChangedEventArgs e)
        => ApplyResponsiveLaptopLayout();

    private void FitInitialWindowToWorkArea()
    {
        var work = SystemParameters.WorkArea;
        if (work.Width <= 0 || work.Height <= 0)
            return;

        var targetWidth = Math.Min(1480.0, work.Width * 0.96);
        var targetHeight = Math.Min(900.0, work.Height * 0.93);

        Width = Math.Max(MinWidth, targetWidth);
        Height = Math.Max(MinHeight, targetHeight);
        Left = work.Left + Math.Max(0, (work.Width - Width) / 2);
        Top = work.Top + Math.Max(0, (work.Height - Height) / 2);
    }

    private void ApplyResponsiveLaptopLayout()
    {
        if (!IsLoaded)
            return;

        var width = ActualWidth > 0 ? ActualWidth : Width;
        var height = ActualHeight > 0 ? ActualHeight : Height;

        var inspectorRow = ResponsiveElement<RowDefinition>("ResponsiveInspectorRow");
        var headerRow = ResponsiveElement<RowDefinition>("ResponsiveHeaderRow");
        var profilesColumn = ResponsiveElement<ColumnDefinition>("ResponsiveProfilesColumn");
        var actionLibraryColumn = ResponsiveElement<ColumnDefinition>("ResponsiveActionLibraryColumn");
        var centerHeaderRow = ResponsiveElement<RowDefinition>("ResponsiveDeckHeaderRow");
        var centerPagerRow = ResponsiveElement<RowDefinition>("ResponsiveDeckPagerRow");
        var headerStatus = ResponsiveElement<FrameworkElement>("ResponsiveHeaderStatus");
        var serverButton = ResponsiveElement<Button>("HeaderServerButton");
        var deckViewport = ResponsiveElement<ScrollViewer>("DeckViewport");

        if (inspectorRow is null || headerRow is null || actionLibraryColumn is null)
            return;

        double profilesWidth;
        double libraryWidth;
        double inspectorHeight;
        double headerHeight;
        double deckHeaderHeight;
        double pagerHeight;
        Thickness deckPadding;
        int inspectorMode;

        if (width >= 1500)
        {
            profilesWidth = 255;
            libraryWidth = 385;
            inspectorHeight = 250;
            headerHeight = 48;
            deckHeaderHeight = 92;
            pagerHeight = 52;
            deckPadding = new Thickness(24);
            inspectorMode = 0;
        }
        else if (width >= 1250)
        {
            profilesWidth = 225;
            libraryWidth = 320;
            inspectorHeight = 220;
            headerHeight = 46;
            deckHeaderHeight = 80;
            pagerHeight = 46;
            deckPadding = new Thickness(18);
            inspectorMode = 0;
        }
        else if (width >= 1020)
        {
            profilesWidth = 205;
            libraryWidth = 275;
            inspectorHeight = 215;
            headerHeight = 44;
            deckHeaderHeight = 72;
            pagerHeight = 42;
            deckPadding = new Thickness(14);
            inspectorMode = 1;
        }
        else
        {
            profilesWidth = 180;
            libraryWidth = 225;
            inspectorHeight = 205;
            headerHeight = 42;
            deckHeaderHeight = 66;
            pagerHeight = 38;
            deckPadding = new Thickness(10);
            inspectorMode = 1;
        }

        if (height < 760)
        {
            inspectorHeight = Math.Min(inspectorHeight, 185);
            headerHeight = Math.Min(headerHeight, 42);
            deckHeaderHeight = Math.Min(deckHeaderHeight, 66);
            pagerHeight = Math.Min(pagerHeight, 38);
        }

        if (height < 640)
        {
            inspectorHeight = Math.Min(inspectorHeight, 155);
            headerHeight = 40;
            deckHeaderHeight = 58;
            pagerHeight = 34;
            deckPadding = new Thickness(8);
        }

        if (profilesColumn is not null)
            profilesColumn.Width = new GridLength(profilesWidth);
        actionLibraryColumn.Width = new GridLength(libraryWidth);
        inspectorRow.Height = new GridLength(inspectorHeight);
        headerRow.Height = new GridLength(headerHeight);

        if (centerHeaderRow is not null)
            centerHeaderRow.Height = new GridLength(deckHeaderHeight);
        if (centerPagerRow is not null)
            centerPagerRow.Height = new GridLength(pagerHeight);
        if (deckViewport is not null)
            deckViewport.Padding = deckPadding;

        if (headerStatus is not null)
            headerStatus.Visibility = width < 1080 ? Visibility.Collapsed : Visibility.Visible;

        if (serverButton is not null)
        {
            serverButton.Content = width < 1120 ? "Связь" : "Связь активна";
            serverButton.Padding = width < 1120 ? new Thickness(8, 2, 8, 2) : new Thickness(12, 2, 12, 2);
        }

        ConfigureResponsiveInspector(inspectorMode);
    }

    private void ConfigureResponsiveInspector(int mode)
    {
        if (_responsiveInspectorMode == mode)
            return;

        var grid = ResponsiveElement<Grid>("ResponsiveInspectorGrid");
        var general = ResponsiveElement<FrameworkElement>("ResponsiveInspectorGeneral");
        var value = ResponsiveElement<FrameworkElement>("ResponsiveInspectorValue");
        var hotkey = ResponsiveElement<FrameworkElement>("ResponsiveInspectorHotkey");
        if (grid is null || general is null || value is null || hotkey is null)
            return;

        _responsiveInspectorMode = mode;
        grid.ColumnDefinitions.Clear();
        grid.RowDefinitions.Clear();

        if (mode == 0)
        {
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1.1, GridUnitType.Star) });
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            grid.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });

            Grid.SetRow(general, 0);
            Grid.SetColumn(general, 0);
            Grid.SetColumnSpan(general, 1);
            Grid.SetRow(value, 0);
            Grid.SetColumn(value, 1);
            Grid.SetColumnSpan(value, 1);
            Grid.SetRow(hotkey, 0);
            Grid.SetColumn(hotkey, 2);
            Grid.SetColumnSpan(hotkey, 1);
        }
        else
        {
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            grid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
            grid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });

            Grid.SetRow(general, 0);
            Grid.SetColumn(general, 0);
            Grid.SetColumnSpan(general, 1);
            Grid.SetRow(value, 0);
            Grid.SetColumn(value, 1);
            Grid.SetColumnSpan(value, 1);
            Grid.SetRow(hotkey, 1);
            Grid.SetColumn(hotkey, 0);
            Grid.SetColumnSpan(hotkey, 2);
        }
    }
}
