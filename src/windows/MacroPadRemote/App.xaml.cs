using System;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;

namespace MacroPadRemote;

public partial class App : Application
{
    private const string MutexName = @"Local\NEXO.Desktop.SingleInstance";
    private const string ShowWindowEventName = @"Local\NEXO.Desktop.ShowWindow";

    private Mutex? _singleInstanceMutex;
    private EventWaitHandle? _showWindowEvent;
    private CancellationTokenSource? _showListenerCts;
    private bool _ownsInstanceMutex;

    protected override void OnStartup(StartupEventArgs e)
    {
        _showWindowEvent = new EventWaitHandle(false, EventResetMode.AutoReset, ShowWindowEventName);
        _singleInstanceMutex = new Mutex(true, MutexName, out _ownsInstanceMutex);

        if (!_ownsInstanceMutex)
        {
            try { _showWindowEvent.Set(); } catch { }
            Shutdown(0);
            return;
        }

        base.OnStartup(e);

        var window = new MacroPadRemote.MainWindow();
        MainWindow = window;
        window.Show();

        _showListenerCts = new CancellationTokenSource();
        _ = Task.Run(() => ListenForShowRequests(_showListenerCts.Token));
    }

    private void ListenForShowRequests(CancellationToken token)
    {
        while (!token.IsCancellationRequested)
        {
            try
            {
                if (_showWindowEvent?.WaitOne(500) != true) continue;
                if (token.IsCancellationRequested) break;

                Dispatcher.BeginInvoke(new Action(() =>
                {
                    if (MainWindow is MacroPadRemote.MainWindow window)
                        window.RestoreFromSecondLaunch();
                }));
            }
            catch (ObjectDisposedException)
            {
                break;
            }
        }
    }

    protected override void OnExit(ExitEventArgs e)
    {
        try
        {
            _showListenerCts?.Cancel();
            _showWindowEvent?.Set();
        }
        catch { }

        _showListenerCts?.Dispose();
        _showWindowEvent?.Dispose();

        if (_ownsInstanceMutex)
        {
            try { _singleInstanceMutex?.ReleaseMutex(); } catch { }
        }

        _singleInstanceMutex?.Dispose();
        base.OnExit(e);
    }
}
