import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
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
  static const _pendingKey = 'nexo_transfer_pending_v14';
  static const _linksKey = 'nexo_link_relations_v141';

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
          serverName: (payload['sourceServerName'] ?? payload['serverName'] ?? 'NEXO PC').toString(),
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

  static Future<void> saveTransfer(Map<String, dynamic> payload, {bool markPending = true}) async {
    final sourceServerId = (payload['sourceServerId'] ?? payload['serverId'] ?? '').toString();
    if (sourceServerId.isEmpty) return;

    final copy = Map<String, dynamic>.from(payload);
    copy['serverId'] = sourceServerId;
    copy['savedAtUtc'] = DateTime.now().toUtc().toIso8601String();
    await save(copy);
    if (markPending) {
      await _storage.write(key: _pendingKey, value: sourceServerId);
    }
  }

  static Future<Map<String, dynamic>?> loadPending() async {
    final sourceServerId = await _storage.read(key: _pendingKey);
    if (sourceServerId == null || sourceServerId.isEmpty) return null;
    return load(sourceServerId);
  }

  static Future<void> clearPending() async {
    await _storage.delete(key: _pendingKey);
  }


  static Future<void> saveLinkRelation({
    required String aServerId,
    required String aServerName,
    required String bServerId,
    required String bServerName,
    required bool enabled,
  }) async {
    if (aServerId.isEmpty || bServerId.isEmpty || aServerId == bServerId) return;
    final map = await _loadLinks();

    void updateOne(String ownerId, String peerId, String peerName) {
      final peers = Map<String, dynamic>.from(map[ownerId] is Map ? map[ownerId] as Map : const {});
      if (enabled) {
        peers[peerId] = {
          'serverId': peerId,
          'serverName': peerName.isEmpty ? 'NEXO PC' : peerName,
        };
      } else {
        peers.remove(peerId);
      }
      map[ownerId] = peers;
    }

    updateOne(aServerId, bServerId, bServerName);
    updateOne(bServerId, aServerId, aServerName);
    await _storage.write(key: _linksKey, value: jsonEncode(map));
  }

  static Future<List<Map<String, dynamic>>> linkedPeersJson(String serverId) async {
    final map = await _loadLinks();
    final peers = map[serverId];
    if (peers is! Map) return <Map<String, dynamic>>[];

    return peers.values
        .whereType<Map>()
        .map((x) => Map<String, dynamic>.from(x))
        .where((x) => (x['serverId'] ?? '').toString().isNotEmpty)
        .toList();
  }

  static Future<Map<String, dynamic>> _loadLinks() async {
    try {
      final raw = await _storage.read(key: _linksKey);
      if (raw == null || raw.isEmpty) return <String, dynamic>{};
      return Map<String, dynamic>.from(jsonDecode(raw) as Map);
    } catch (_) {
      return <String, dynamic>{};
    }
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

Future<bool> v13UnlockWorkspaceVault() async => true;
