from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)


def insert_before_once(text: str, marker: str, insertion: str, label: str) -> str:
    count = text.count(marker)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one marker, got {count}")
    return text.replace(marker, insertion + marker, 1)


def patch_mobile() -> None:
    path = ROOT / "src/mobile/macropad_mobile/lib/main.dart"
    text = path.read_text(encoding="utf-8")

    text = replace_once(
        text,
        "import 'package:web_socket_channel/web_socket_channel.dart';\n",
        "import 'package:web_socket_channel/web_socket_channel.dart';\n\nimport 'v13_backup.dart';\n",
        "v1.3 backup import",
    )

    text = replace_once(
        text,
        '''  final String? service;

  const QrPairing({required this.transport, required this.serverId, required this.token, this.host, this.port = 8765, this.service});''',
        '''  final String? service;
  final String mode;

  const QrPairing({required this.transport, required this.serverId, required this.token, this.host, this.port = 8765, this.service, this.mode = "control"});''',
        "v1.3 QR mode field",
    )

    text = replace_once(
        text,
        '''        service: uri.queryParameters['service'],
      );''',
        '''        service: uri.queryParameters['service'],
        mode: uri.queryParameters['mode'] ?? 'control',
      );''',
        "v1.3 QR mode parse",
    )

    settings_anchor = """                Text(transport == TransportKind.wifi
                    ? 'Устройства в одной сети обнаруживаются автоматически. QR нужен только при первой привязке.'
                    : 'Bluetooth LE можно использовать для прямого соединения без общей Wi‑Fi сети.', style: const TextStyle(color: mpMuted)),"""
    settings_new = settings_anchor + """
                const SizedBox(height: 14),
                OutlinedButton.icon(
                  icon: const Icon(Icons.move_to_inbox_outlined),
                  label: const Text('Перенос / библиотека устройств'),
                  onPressed: () async {
                    Navigator.of(dialogContext).pop();
                    await _v13ScanRestoreQr();
                  },
                ),"""
    text = replace_once(text, settings_anchor, settings_new, "v1.3 transfer entry")

    scan_marker = "  Future<void> _pairWifi(DiscoveredPc pc) async {"
    scan_impl = r'''  Future<void> _v13ScanRestoreQr() async {
    final qr = await _scanQr();
    if (!mounted || qr == null) return;
    if (qr.mode != 'restore') {
      _message('Этот QR предназначен для обычного подключения. Для переноса используйте QR из мастера первого запуска на ПК.');
      return;
    }
    if (qr.transport != TransportKind.wifi || qr.host == null || qr.host!.isEmpty) {
      _message('Перенос рабочих пространств выполняется по Wi‑Fi.');
      return;
    }

    final unlocked = await v13UnlockWorkspaceVault();
    if (!mounted || !unlocked) {
      _message('Доступ к сохранённым рабочим пространствам не подтверждён.');
      return;
    }

    final summaries = await V13WorkspaceVault.summaries();
    if (!mounted) return;
    if (summaries.isEmpty) {
      _message('На этом устройстве пока нет сохранённых рабочих пространств NEXO.');
      return;
    }

    final selected = await showDialog<V13WorkspaceSummary>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Выберите исходный компьютер'),
        content: SizedBox(
          width: 440,
          height: 360,
          child: ListView.separated(
            itemCount: summaries.length,
            separatorBuilder: (_, _) => const Divider(height: 1),
            itemBuilder: (_, index) {
              final item = summaries[index];
              return ListTile(
                leading: const Icon(Icons.computer),
                title: Text(item.serverName),
                subtitle: Text('${item.profileCount} проф. • ${item.updatedUtc.toLocal()}'),
                onTap: () => Navigator.of(dialogContext).pop(item),
              );
            },
          ),
        ),
      ),
    );
    if (selected == null) return;

    final workspace = await V13WorkspaceVault.load(selected.serverId);
    if (workspace == null) {
      _message('Не удалось прочитать сохранённое рабочее пространство.');
      return;
    }

    final remote = WifiRemoteTransport(host: qr.host!, port: qr.port, clientId: clientId, pairToken: qr.token);
    StreamSubscription<String>? transferSub;
    try {
      await remote.connect();
      String newToken = '';
      String newName = 'NEXO PC';
      final paired = Completer<void>();
      transferSub = remote.messages.listen((message) async {
        try {
          final json = jsonDecode(message);
          if (json is Map && json['type'] == 'paired') {
            newToken = '${json['deviceToken'] ?? ''}';
            newName = '${json['serverName'] ?? newName}';
            if (!paired.isCompleted) paired.complete();
          }
        } catch (_) {}
      });

      await remote.send({'type': 'restoreWorkspace', 'workspace': workspace});
      await Future.any([paired.future, Future<void>.delayed(const Duration(milliseconds: 900))]);

      if (newToken.isNotEmpty && qr.serverId.isNotEmpty) {
        final pc = SavedPc(
          serverId: qr.serverId,
          name: newName,
          host: qr.host!,
          port: qr.port,
          deviceToken: newToken,
          transport: 'wifi',
          lastSeen: DateTime.now(),
        );
        await DeviceStore.upsert(pc);
        savedPcs[pc.serverId] = pc;
      }

      if (mounted) {
        _message('Рабочее пространство «${selected.serverName}» передано на новый ПК.');
      }
    } catch (e) {
      if (mounted) _message('Не удалось передать рабочее пространство: $e');
    } finally {
      await transferSub?.cancel();
      await remote.close();
    }
  }

'''
    text = insert_before_once(text, scan_marker, scan_impl, "v1.3 restore scanner")

    text = replace_once(
        text,
        '''      await widget.transport.send({
        'type': 'clientInfo',
        'clientId': widget.clientId,
        'formFactor': widget.formFactor == ClientFormFactor.tablet ? 'tablet' : 'phone',
        'deviceName': '${formFactorLabel(widget.formFactor)} ${widget.clientId.length > 4 ? widget.clientId.substring(widget.clientId.length - 4) : widget.clientId}',
      });
      _remoteRevoked = false;
      _resumeReconnectPending = false;
      if (mounted) setState(() => status = widget.transport.label);''',
        '''      await widget.transport.send({
        'type': 'clientInfo',
        'clientId': widget.clientId,
        'formFactor': widget.formFactor == ClientFormFactor.tablet ? 'tablet' : 'phone',
        'deviceName': '${formFactorLabel(widget.formFactor)} ${widget.clientId.length > 4 ? widget.clientId.substring(widget.clientId.length - 4) : widget.clientId}',
      });
      _remoteRevoked = false;
      _resumeReconnectPending = false;
      await widget.transport.send({'type': 'workspaceBackupRequest'});
      if (mounted) setState(() => status = widget.transport.label);''',
        "v1.3 request full workspace on connect",
    )

    text = replace_once(
        text,
        "      if (json is! Map<String, dynamic>) return;\n",
        """      if (json is! Map<String, dynamic>) return;
      if (json['type'] == 'workspaceBackup') {
        await V13WorkspaceVault.save(json);
        return;
      }
      if (json['type'] == 'backupCatalogRequest') {
        if (await v13UnlockWorkspaceVault()) {
          await widget.transport.send({
            'type': 'backupCatalogResponse',
            'devices': await V13WorkspaceVault.catalogJson(),
          });
        }
        return;
      }
      if (json['type'] == 'backupWorkspaceRequest') {
        final requestedServerId = '${json['serverId'] ?? ''}';
        if (requestedServerId.isNotEmpty && await v13UnlockWorkspaceVault()) {
          final workspace = await V13WorkspaceVault.load(requestedServerId);
          if (workspace != null) {
            await widget.transport.send({
              'type': 'backupWorkspaceResponse',
              'serverId': requestedServerId,
              'workspace': workspace,
            });
          }
        }
        return;
      }
""",
        "v1.3 mobile backup protocol",
    )

    path.write_text(text, encoding="utf-8")
    print(f"Applied v1.3 mobile fixes: {path}")



if __name__ == "__main__":
    patch_mobile()
