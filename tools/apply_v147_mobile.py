from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)


def main() -> None:
    path = ROOT / "src/mobile/macropad_mobile/lib/main.dart"
    text = path.read_text(encoding="utf-8")

    marker = """  Future<void> _pairWifi(DiscoveredPc pc) async {
"""
    direct_qr = r'''  Future<void> _pairWifiDirectQr() async {
    final qr = await _scanQr();
    if (!mounted || qr == null) return;
    if (qr.transport != TransportKind.wifi) {
      return _message('Этот QR-код предназначен для Bluetooth.');
    }

    final host = (qr.host ?? '').trim();
    if (host.isEmpty || qr.serverId.isEmpty) {
      return _message('QR-код не содержит адрес или ID компьютера. Обновите NEXO на ПК и создайте QR заново.');
    }

    final remote = WifiRemoteTransport(
      host: host,
      port: qr.port,
      clientId: clientId,
      pairToken: qr.token,
    );

    await _openRemote(
      remote,
      serverId: qr.serverId,
      serverName: 'NEXO PC',
      host: host,
      port: qr.port,
      transportName: 'wifi',
    );
  }

'''
    text = replace_once(text, marker, direct_qr + marker, "direct QR Wi-Fi pairing")

    text = replace_once(
        text,
        """          IconButton(tooltip: 'Повернуть экран', onPressed: () => toggleScreenOrientation(context), icon: const Icon(Icons.screen_rotation)),
          IconButton(tooltip: 'Настройки', onPressed: _showSettings, icon: const Icon(Icons.settings)),
""",
        """          IconButton(tooltip: 'Повернуть экран', onPressed: () => toggleScreenOrientation(context), icon: const Icon(Icons.screen_rotation)),
          IconButton(tooltip: 'Подключить по QR', onPressed: _pairWifiDirectQr, icon: const Icon(Icons.qr_code_scanner)),
          IconButton(tooltip: 'Настройки', onPressed: _showSettings, icon: const Icon(Icons.settings)),
""",
        "direct QR button",
    )

    old_hint = """                Text(transport == TransportKind.wifi
                    ? 'Устройства в одной сети обнаруживаются автоматически. QR нужен только при первой привязке.'
                    : 'Bluetooth LE можно использовать для прямого соединения без общей Wi-Fi сети.', style: const TextStyle(color: mpMuted)),
"""
    new_hint = """                Text(transport == TransportKind.wifi
                    ? 'Устройства в одной сети обнаруживаются автоматически. На iPhone также можно подключиться напрямую по QR — это работает даже если сетевое обнаружение недоступно.'
                    : 'Bluetooth LE можно использовать для прямого соединения без общей Wi-Fi сети.', style: const TextStyle(color: mpMuted)),
"""
    if old_hint in text:
        text = text.replace(old_hint, new_hint, 1)

    path.write_text(text, encoding="utf-8")
    print(f"Applied NEXO v1.4.7 mobile/iPhone pairing: {path}")


if __name__ == "__main__":
    main()
