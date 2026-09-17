namespace MacroPadRemote;

public partial class MainWindow
{
    private async Task SetLanDiscoverableAsync(bool visible)
    {
        _state.Discoverable = visible;
        SaveState();
        if (SelectedTransport() == "Wifi" && _server is not null)
        {
            if (visible)
                await _lanDiscovery.StartAsync();
            else
                await _lanDiscovery.StopAsync();
        }
        SyncConnectionUi();
        UpdateConnectionStatus();
    }

    private async Task SetConnectionsEnabledAsync(bool enabled)
    {
        if (_state.AcceptConnections == enabled) return;
        _state.AcceptConnections = enabled;
        SaveState();
        if (enabled)
            await StartSelectedTransportAsync();
        else
            await StopAllTransportsAsync();
        SyncConnectionUi();
        UpdateConnectionStatus();
    }
}
