import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:local_auth/local_auth.dart';

class V13WorkspaceSummary {
  final String serverId;
  final String serverName;
  final DateTime updatedUtc;
  final int profileCount;

  const V13WorkspaceSummary({
    required this.serverId,
    required this.serverName,
    required this.updatedUtc,
    required this.profileCount,
  });
}

class V13WorkspaceVault {
  static const FlutterSecureStorage _storage = FlutterSecureStorage();
  static const _indexKey = 'nexo_workspace_vault_index_v1';
  static const _prefix = 'nexo_workspace_vault_v1_';

  static String _key(String serverId) => '$_prefix$serverId';

  static Future<void> save(Map<String, dynamic> payload) async {
    final serverId = (payload['serverId'] ?? '').toString();
    if (serverId.isEmpty) return;

    final copy = Map<String, dynamic>.from(payload);
    copy['savedAtUtc'] = DateTime.now().toUtc().toIso8601String();
    await _storage.write(key: _key(serverId), value: jsonEncode(copy));

    final ids = await _loadIndex();
    if (!ids.contains(serverId)) {
      ids.add(serverId);
      await _storage.write(key: _indexKey, value: jsonEncode(ids));
    }
  }

  static Future<Map<String, dynamic>?> load(String serverId) async {
    try {
      final raw = await _storage.read(key: _key(serverId));
      if (raw == null || raw.isEmpty) return null;
      return Map<String, dynamic>.from(jsonDecode(raw) as Map);
    } catch (_) {
      return null;
    }
  }

  static Future<List<V13WorkspaceSummary>> summaries() async {
    final result = <V13WorkspaceSummary>[];
    for (final id in await _loadIndex()) {
      final payload = await load(id);
      if (payload == null) continue;
      final profiles = payload['profiles'] is List ? payload['profiles'] as List : const [];
      result.add(
        V13WorkspaceSummary(
          serverId: id,
          serverName: (payload['serverName'] ?? 'NEXO PC').toString(),
          updatedUtc: DateTime.tryParse((payload['updatedUtc'] ?? payload['savedAtUtc'] ?? '').toString())?.toUtc() ?? DateTime.fromMillisecondsSinceEpoch(0, isUtc: true),
          profileCount: profiles.length,
        ),
      );
    }
    result.sort((a, b) => b.updatedUtc.compareTo(a.updatedUtc));
    return result;
  }

  static Future<List<Map<String, dynamic>>> catalogJson() async {
    final result = <Map<String, dynamic>>[];
    for (final item in await summaries()) {
      result.add({
        'serverId': item.serverId,
        'serverName': item.serverName,
        'updatedUtc': item.updatedUtc.toIso8601String(),
        'profileCount': item.profileCount,
      });
    }
    return result;
  }

  static Future<void> remove(String serverId) async {
    await _storage.delete(key: _key(serverId));
    final ids = await _loadIndex();
    ids.remove(serverId);
    await _storage.write(key: _indexKey, value: jsonEncode(ids));
  }

  static Future<List<String>> _loadIndex() async {
    try {
      final raw = await _storage.read(key: _indexKey);
      if (raw == null || raw.isEmpty) return <String>[];
      return (jsonDecode(raw) as List).map((x) => x.toString()).where((x) => x.isNotEmpty).toList();
    } catch (_) {
      return <String>[];
    }
  }
}

Future<bool> v13UnlockWorkspaceVault() async {
  final auth = LocalAuthentication();
  try {
    if (!await auth.isDeviceSupported()) return false;
    return await auth.authenticate(
      localizedReason: 'Подтвердите личность, чтобы открыть сохранённые рабочие пространства NEXO',
      persistAcrossBackgrounding: true,
      biometricOnly: false,
      sensitiveTransaction: true,
    );
  } on LocalAuthException {
    return false;
  } catch (_) {
    return false;
  }
}
