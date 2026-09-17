from pathlib import Path

# Mobile: real long-press start/end with one haptic pulse.
p=Path('src/mobile/macropad_mobile/lib/main.dart')
s=p.read_text(encoding='utf-8')
old="""  Future<void> _sendTile(TileSnapshot tile, {bool longPress = false}) async {
    await HapticFeedback.selectionClick();
    await widget.transport.send({'type': longPress ? 'longPress' : 'press', 'tileId': tile.id});
  }
"""
new="""  Future<void> _sendTile(TileSnapshot tile) async {
    await HapticFeedback.lightImpact();
    await widget.transport.send({'type': 'press', 'tileId': tile.id});
  }

  Future<void> _startLongPress(TileSnapshot tile) async {
    await HapticFeedback.mediumImpact();
    await widget.transport.send({'type': 'longPressStart', 'tileId': tile.id});
  }

  Future<void> _endLongPress(TileSnapshot tile) => widget.transport.send({'type': 'longPressEnd', 'tileId': tile.id});
"""
if old not in s: raise SystemExit('mobile send marker missing')
s=s.replace(old,new,1)
old2="""      child: InkWell(
        onTap: blank ? null : () => _sendTile(tile),
        onLongPress: blank ? null : () => _sendTile(tile, longPress: true),
        child: Padding(
          padding: EdgeInsets.all(padding),
          child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
            _tileIcon(tile, iconSize, blank),
            if (tile.showLabel) ...[
              SizedBox(height: (5 * scale).clamp(1.0, 6.0)),
              Flexible(child: Text(tile.title, textAlign: TextAlign.center, maxLines: scale < .52 ? 1 : 2, overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: fontSize, color: blank ? const Color(0xff7c8287) : Colors.white, fontWeight: FontWeight.w600, height: 1.05))),
            ],
          ]),
        ),
      ),
"""
new2="""      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: blank ? null : () => _sendTile(tile),
        onLongPressStart: blank ? null : (_) => _startLongPress(tile),
        onLongPressEnd: blank ? null : (_) => _endLongPress(tile),
        child: Padding(
          padding: EdgeInsets.all(padding),
          child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
            _tileIcon(tile, iconSize, blank),
            if (tile.showLabel) ...[
              SizedBox(height: (5 * scale).clamp(1.0, 6.0)),
              Flexible(child: Text(tile.title, textAlign: TextAlign.center, maxLines: scale < .52 ? 1 : 2, overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: fontSize, color: blank ? const Color(0xff7c8287) : Colors.white, fontWeight: FontWeight.w600, height: 1.05))),
            ],
          ]),
        ),
      ),
"""
if old2 not in s: raise SystemExit('mobile tile marker missing')
s=s.replace(old2,new2,1)
p.write_text(s,encoding='utf-8')

# Windows: hold hotkey/media down until mobile releases; non-key actions execute once at hold start.
p=Path('src/windows/MacroPadRemote/MainWindow.xaml.cs')
c=p.read_text(encoding='utf-8')
c=c.replace('    private Window? _qrWindow;', '    private Window? _qrWindow;\n    private readonly Dictionary<string, List<ushort>> _heldRemoteKeys = new();')
old3='''            if ((messageType == "press" || messageType == "longPress") && root.TryGetProperty("tileId", out var tileIdProp))
            {
                var tileId = tileIdProp.GetString();
                var tile = _state.Profiles.SelectMany(p => p.Pages).SelectMany(p => p.Tiles).FirstOrDefault(t => t.Id == tileId);
                if (tile is not null)
                {
                    Dispatcher.Invoke(() => DeviceStatus.Text = $"Команда получена: {tile.Title}");
                    var executeTask = await Dispatcher.InvokeAsync(() => ExecuteTileAsync(tile));
                    await executeTask;
                }
                else
                {
                    Dispatcher.Invoke(() => DeviceStatus.Text = $"Команда не найдена: {tileId}");
                }
                return;
            }
'''
new3='''            if ((messageType == "press" || messageType == "longPressStart" || messageType == "longPressEnd") && root.TryGetProperty("tileId", out var tileIdProp))
            {
                var tileId = tileIdProp.GetString() ?? "";
                var tile = _state.Profiles.SelectMany(p => p.Pages).SelectMany(p => p.Tiles).FirstOrDefault(t => t.Id == tileId);
                if (tile is null)
                {
                    Dispatcher.Invoke(() => DeviceStatus.Text = $"Команда не найдена: {tileId}");
                    return;
                }

                if (messageType == "longPressStart")
                {
                    await Dispatcher.InvokeAsync(() => StartRemoteHold(clientId, tile));
                    return;
                }
                if (messageType == "longPressEnd")
                {
                    await Dispatcher.InvokeAsync(() => EndRemoteHold(clientId, tile.Id));
                    return;
                }

                Dispatcher.Invoke(() => DeviceStatus.Text = $"Команда получена: {tile.Title}");
                var executeTask = await Dispatcher.InvokeAsync(() => ExecuteTileAsync(tile));
                await executeTask;
                return;
            }
'''
if old3 not in c: raise SystemExit('server tile marker missing')
c=c.replace(old3,new3,1)
# Insert hold helpers before ExecuteTileAsync
marker='''    private async Task ExecuteTileAsync(Tile tile)
    {'''
helpers='''    private string HoldKey(string clientId, string tileId) => $"{clientId}:{tileId}";

    private void StartRemoteHold(string clientId, Tile tile)
    {
        var hotkey = tile.ActionType == "media" ? tile.ActionValue : tile.Hotkey;
        if (tile.ActionType == "hotkey" || tile.ActionType == "media" || (!string.IsNullOrWhiteSpace(hotkey) && string.IsNullOrWhiteSpace(tile.ActionType)))
        {
            var keys = HotkeyVirtualKeys(hotkey);
            if (keys.Count == 0) return;
            var key = HoldKey(clientId, tile.Id);
            if (_heldRemoteKeys.ContainsKey(key)) return;
            SendInputs(keys.Select(vk => KeyInput(vk, false)).ToArray());
            _heldRemoteKeys[key] = keys;
            DeviceStatus.Text = $"Удерживается: {tile.Title}";
            return;
        }

        _ = ExecuteTileAsync(tile);
    }

    private void EndRemoteHold(string clientId, string tileId)
    {
        var key = HoldKey(clientId, tileId);
        if (!_heldRemoteKeys.Remove(key, out var keys)) return;
        SendInputs(keys.AsEnumerable().Reverse().Select(vk => KeyInput(vk, true)).ToArray());
        DeviceStatus.Text = "Удержание завершено";
    }

    private void ReleaseRemoteHolds(string clientId)
    {
        foreach (var key in _heldRemoteKeys.Keys.Where(k => k.StartsWith(clientId + ":", StringComparison.Ordinal)).ToList())
        {
            if (!_heldRemoteKeys.Remove(key, out var keys)) continue;
            try { SendInputs(keys.AsEnumerable().Reverse().Select(vk => KeyInput(vk, true)).ToArray()); } catch { }
        }
    }

    private static List<ushort> HotkeyVirtualKeys(string hotkey)
    {
        if (string.IsNullOrWhiteSpace(hotkey)) return new List<ushort>();
        return hotkey.Split('+', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
            .Select(TokenToVk).Where(vk => vk != 0).ToList();
    }

'''
if marker not in c: raise SystemExit('execute marker missing')
c=c.replace(marker,helpers+marker,1)
# Release any held keys when Wi-Fi socket disappears.
old4='''            if (!stillOnline) MarkTrustedClient(clientId, false, "Wi‑Fi");
            Dispatcher.Invoke(UpdateConnectionStatus);'''
new4='''            if (!stillOnline)
            {
                Dispatcher.Invoke(() => ReleaseRemoteHolds(clientId));
                MarkTrustedClient(clientId, false, "Wi‑Fi");
            }
            Dispatcher.Invoke(UpdateConnectionStatus);'''
if old4 not in c: raise SystemExit('socket finally marker missing')
c=c.replace(old4,new4,1)
p.write_text(c,encoding='utf-8')
print('proper hold behavior patched')
