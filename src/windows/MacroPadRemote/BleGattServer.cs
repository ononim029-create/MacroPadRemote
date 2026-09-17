using System.Text;
using Windows.Devices.Bluetooth;
using Windows.Devices.Bluetooth.GenericAttributeProfile;
using Windows.Storage.Streams;

namespace MacroPadRemote;

public sealed class BleGattServer : IAsyncDisposable
{
    public static readonly Guid ServiceUuid = Guid.Parse("9B4981A0-7D70-4B1A-9DF2-7997634C5001");
    public static readonly Guid CommandUuid = Guid.Parse("9B4981A0-7D70-4B1A-9DF2-7997634C5002");
    public static readonly Guid StateUuid = Guid.Parse("9B4981A0-7D70-4B1A-9DF2-7997634C5003");

    private GattServiceProvider? _provider;
    private GattLocalCharacteristic? _command;
    private GattLocalCharacteristic? _state;
    private string _snapshot = "{}";

    public bool IsRunning => _provider is not null;
    public string StatusText => _provider?.AdvertisementStatus.ToString() ?? "Stopped";
    public event Func<string, Task>? MessageReceived;
    public event Action<string>? StatusChanged;

    public async Task StartAsync()
    {
        if (_provider is not null) return;

        var create = await GattServiceProvider.CreateAsync(ServiceUuid);
        if (create.Error != BluetoothError.Success || create.ServiceProvider is null)
            throw new InvalidOperationException($"Не удалось создать BLE GATT service: {create.Error}");

        _provider = create.ServiceProvider;
        _provider.AdvertisementStatusChanged += (_, args) => StatusChanged?.Invoke(args.Status.ToString());

        var commandParameters = new GattLocalCharacteristicParameters
        {
            CharacteristicProperties = GattCharacteristicProperties.Write | GattCharacteristicProperties.WriteWithoutResponse,
            WriteProtectionLevel = GattProtectionLevel.Plain,
            UserDescription = "MacroPad command"
        };
        var commandResult = await _provider.Service.CreateCharacteristicAsync(CommandUuid, commandParameters);
        if (commandResult.Error != BluetoothError.Success || commandResult.Characteristic is null)
            throw new InvalidOperationException($"Не удалось создать BLE command characteristic: {commandResult.Error}");
        _command = commandResult.Characteristic;
        _command.WriteRequested += Command_WriteRequested;

        var stateParameters = new GattLocalCharacteristicParameters
        {
            CharacteristicProperties = GattCharacteristicProperties.Read | GattCharacteristicProperties.Notify,
            ReadProtectionLevel = GattProtectionLevel.Plain,
            UserDescription = "MacroPad state"
        };
        var stateResult = await _provider.Service.CreateCharacteristicAsync(StateUuid, stateParameters);
        if (stateResult.Error != BluetoothError.Success || stateResult.Characteristic is null)
            throw new InvalidOperationException($"Не удалось создать BLE state characteristic: {stateResult.Error}");
        _state = stateResult.Characteristic;
        _state.ReadRequested += State_ReadRequested;

        _provider.StartAdvertising(new GattServiceProviderAdvertisingParameters
        {
            IsConnectable = true,
            IsDiscoverable = true
        });
        StatusChanged?.Invoke(_provider.AdvertisementStatus.ToString());
    }

    public Task StopAsync()
    {
        if (_command is not null) _command.WriteRequested -= Command_WriteRequested;
        if (_state is not null) _state.ReadRequested -= State_ReadRequested;
        try { _provider?.StopAdvertising(); } catch { }
        _command = null;
        _state = null;
        _provider = null;
        StatusChanged?.Invoke("Stopped");
        return Task.CompletedTask;
    }

    public async Task SetSnapshotAsync(string json)
    {
        _snapshot = json;
        if (_state is null || _state.SubscribedClients.Count == 0) return;
        try
        {
            // BLE notifications should stay small. The phone re-reads the full snapshot.
            var writer = new DataWriter();
            writer.WriteBytes(Encoding.UTF8.GetBytes("{\"type\":\"state_changed\"}"));
            await _state.NotifyValueAsync(writer.DetachBuffer());
        }
        catch { }
    }

    private async void Command_WriteRequested(GattLocalCharacteristic sender, GattWriteRequestedEventArgs args)
    {
        using var deferral = args.GetDeferral();
        try
        {
            var request = await args.GetRequestAsync();
            if (request is null) return;
            using var reader = DataReader.FromBuffer(request.Value);
            var bytes = new byte[reader.UnconsumedBufferLength];
            reader.ReadBytes(bytes);
            var message = Encoding.UTF8.GetString(bytes);
            if (MessageReceived is not null)
                await MessageReceived(message);
            if (request.Option == GattWriteOption.WriteWithResponse)
                request.Respond();
        }
        catch { }
    }

    private async void State_ReadRequested(GattLocalCharacteristic sender, GattReadRequestedEventArgs args)
    {
        using var deferral = args.GetDeferral();
        try
        {
            var request = await args.GetRequestAsync();
            if (request is null) return;
            var bytes = Encoding.UTF8.GetBytes(_snapshot);
            var offset = Math.Clamp((int)request.Offset, 0, bytes.Length);
            var remaining = bytes.AsSpan(offset).ToArray();
            var writer = new DataWriter();
            writer.WriteBytes(remaining);
            request.RespondWithValue(writer.DetachBuffer());
        }
        catch { }
    }

    public async ValueTask DisposeAsync() => await StopAsync();
}
