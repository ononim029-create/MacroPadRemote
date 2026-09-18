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

    marker = """      if (json['type'] == 'transferPackageRequest') {
        final requestedServerId = (json['sourceServerId'] ?? '').toString();
        final workspace = requestedServerId.isEmpty
            ? await V13WorkspaceVault.loadPending()
            : await V13WorkspaceVault.load(requestedServerId);
        try {
          await widget.transport.send({
            'type': 'transferPackageResponse',
            'sourceServerId': requestedServerId,
            'workspace': workspace,
          });
        } catch (_) {}
        return;
      }
"""

    replacement = """      if (json['type'] == 'transferCatalogRequest') {
        try {
          await widget.transport.send({
            'type': 'transferCatalogResponse',
            'devices': await V13WorkspaceVault.catalogJson(),
          });
        } catch (_) {}
        return;
      }
      if (json['type'] == 'linkRelationUpdate') {
        final aServerId = (json['aServerId'] ?? '').toString();
        final aServerName = (json['aServerName'] ?? 'NEXO PC').toString();
        final bServerId = (json['bServerId'] ?? '').toString();
        final bServerName = (json['bServerName'] ?? 'NEXO PC').toString();
        final enabled = json['enabled'] != false;
        await V13WorkspaceVault.saveLinkRelation(
          aServerId: aServerId,
          aServerName: aServerName,
          bServerId: bServerId,
          bServerName: bServerName,
          enabled: enabled,
        );
        try {
          await widget.transport.send({
            'type': 'linkRelationStored',
            'aServerId': aServerId,
            'bServerId': bServerId,
            'enabled': enabled,
          });
        } catch (_) {}
        return;
      }
      if (json['type'] == 'linkPeersRequest') {
        final serverId = (json['serverId'] ?? '').toString();
        try {
          await widget.transport.send({
            'type': 'linkPeersResponse',
            'serverId': serverId,
            'peers': await V13WorkspaceVault.linkedPeersJson(serverId),
          });
        } catch (_) {}
        return;
      }
""" + marker

    text = replace_once(text, marker, replacement, "v1.4.1 bidirectional link protocol")
    path.write_text(text, encoding="utf-8")
    print(f"Applied NEXO v1.4.1 mobile link protocol: {path}")


if __name__ == "__main__":
    main()
