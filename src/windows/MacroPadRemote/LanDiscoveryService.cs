using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;

namespace MacroPadRemote;

public sealed class LanDiscoveryService : IAsyncDisposable
{
    public const int DiscoveryPort = 8766;
    private readonly Func<string> _hostProvider;
    private readonly Func<string> _serverIdProvider;
    private readonly int _webSocketPort;
    private UdpClient? _udp;
    private CancellationTokenSource? _cts;

    public bool IsRunning => _udp is not null;
    public event Action<IPEndPoint>? PeerSeen;

    public LanDiscoveryService(int webSocketPort, Func<string> hostProvider, Func<string> serverIdProvider)
    {
        _webSocketPort = webSocketPort;
        _hostProvider = hostProvider;
        _serverIdProvider = serverIdProvider;
    }

    public Task StartAsync()
    {
        if (_udp is not null) return Task.CompletedTask;
        _cts = new CancellationTokenSource();
        _udp = new UdpClient(new IPEndPoint(IPAddress.Any, DiscoveryPort));
        _udp.EnableBroadcast = true;
        _ = ReceiveLoopAsync(_cts.Token);
        return Task.CompletedTask;
    }

    public Task StopAsync()
    {
        _cts?.Cancel();
        _cts?.Dispose();
        _cts = null;
        _udp?.Dispose();
        _udp = null;
        return Task.CompletedTask;
    }

    private async Task ReceiveLoopAsync(CancellationToken token)
    {
        while (!token.IsCancellationRequested && _udp is not null)
        {
            try
            {
                var result = await _udp.ReceiveAsync(token);
                var text = Encoding.UTF8.GetString(result.Buffer).Trim();
                if (!string.Equals(text, "MACROPAD_DISCOVER_V1", StringComparison.Ordinal))
                    continue;

                PeerSeen?.Invoke(result.RemoteEndPoint);

                // Resolve the IPv4 address Windows would actually use to reach this phone.
                // This avoids advertising WSL/Docker/Hyper-V adapters such as 172.18.x.x.
                var reachableHost = ResolveLocalAddressForPeer(result.RemoteEndPoint) ?? _hostProvider();
                var response = JsonSerializer.Serialize(new
                {
                    type = "macropad_discovery",
                    name = Environment.MachineName,
                    serverId = _serverIdProvider(),
                    host = reachableHost,
                    port = _webSocketPort,
                    requiresQr = true,
                    version = "0.6.1"
                });
                var bytes = Encoding.UTF8.GetBytes(response);
                await _udp.SendAsync(bytes, result.RemoteEndPoint, token);
            }
            catch (OperationCanceledException) { break; }
            catch (ObjectDisposedException) { break; }
            catch
            {
                await Task.Delay(250, token).ContinueWith(_ => { }, TaskScheduler.Default);
            }
        }
    }

    private static string? ResolveLocalAddressForPeer(IPEndPoint peer)
    {
        try
        {
            using var socket = new Socket(AddressFamily.InterNetwork, SocketType.Dgram, ProtocolType.Udp);
            socket.Connect(peer);
            return (socket.LocalEndPoint as IPEndPoint)?.Address.ToString();
        }
        catch
        {
            return null;
        }
    }

    public async ValueTask DisposeAsync() => await StopAsync();
}
