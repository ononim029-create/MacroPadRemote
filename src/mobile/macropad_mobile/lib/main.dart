import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:universal_ble/universal_ble.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

const serviceUuid = '9b4981a0-7d70-4b1a-9df2-7997634c5001';
const commandUuid = '9b4981a0-7d70-4b1a-9df2-7997634c5002';
const stateUuid = '9b4981a0-7d70-4b1a-9df2-7997634c5003';
const discoveryPort = 8766;
const discoveryProbe = 'MACROPAD_DISCOVER_V1';

const mpBg = Color(0xff17191b);
const mpPanel = Color(0xff1d1f21);
const mpPanel2 = Color(0xff24272a);
const mpHover = Color(0xff2c3034);
const mpBorder = Color(0xff353a3e);
const mpText = Color(0xfff2f2f2);
const mpMuted = Color(0xff9da3a8);
const mpBlue = Color(0xff1688ff);
const mpGreen = Color(0xff62d16f);

void main() => runApp(const MacroPadApp());

enum ClientFormFactor { phone, tablet }
enum TransportKind { wifi, bluetooth }

ClientFormFactor formFactorOf(BuildContext context) {
  final view = View.maybeOf(context);
  if (view != null) {
    final display = view.display;
    final width = display.size.width / display.devicePixelRatio;
    final height = display.size.height / display.devicePixelRatio;
    return (width < height ? width : height) >= 600 ? ClientFormFactor.tablet : ClientFormFactor.phone;
  }
  return MediaQuery.sizeOf(context).shortestSide >= 600 ? ClientFormFactor.tablet : ClientFormFactor.phone;
}

String formFactorLabel(ClientFormFactor value) => value == ClientFormFactor.tablet ? 'Планшет' : 'Телефон';

Future<void> toggleScreenOrientation(BuildContext context) async {
  final orientation = MediaQuery.orientationOf(context);
  if (orientation == Orientation.portrait) {
    await SystemChrome.setPreferredOrientations(const [DeviceOrientation.landscapeLeft, DeviceOrientation.landscapeRight]);
  } else {
    await SystemChrome.setPreferredOrientations(const [DeviceOrientation.portraitUp]);
  }
}

class MacroPadMark extends StatelessWidget {
  final double size;
  const MacroPadMark({super.key, this.size = 28});

  @override
  Widget build(BuildContext context) {
    final gap = size * .08;
    final cell = (size - gap) / 2;
    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        children: [
          Positioned(left: 0, top: 0, width: cell, height: cell, child: Container(color: mpBlue)),
          Positioned(right: 0, top: 0, width: cell, height: cell, child: Container(color: mpText)),
          Positioned(left: 0, bottom: 0, width: cell, height: cell, child: Container(color: mpText)),
          Positioned(right: 0, bottom: 0, width: cell, height: cell, child: Container(color: mpPanel2, foregroundDecoration: BoxDecoration(border: Border.all(color: mpText, width: 1.2)))),
        ],
      ),
    );
  }
}

class MacroPadApp extends StatelessWidget {
  const MacroPadApp({super.key});

  @override
  Widget build(BuildContext context) {
    final square = RoundedRectangleBorder(borderRadius: BorderRadius.zero, side: const BorderSide(color: mpBorder));
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'NEXO',
      builder: (context, child) => MediaQuery(data: MediaQuery.of(context).copyWith(textScaler: MediaQuery.of(context).textScaler.clamp(minScaleFactor: .85, maxScaleFactor: 1.15)), child: child!),
      theme: ThemeData(
        brightness: Brightness.dark,
        useMaterial3: true,
        scaffoldBackgroundColor: mpBg,
        colorScheme: const ColorScheme.dark(
          primary: mpBlue,
          onPrimary: Colors.white,
          surface: mpPanel,
          onSurface: mpText,
          secondary: mpBlue,
          onSecondary: Colors.white,
          outline: mpBorder,
        ),
        appBarTheme: const AppBarTheme(backgroundColor: Color(0xff1b1d1f), foregroundColor: Colors.white, surfaceTintColor: Colors.transparent, elevation: 0),
        drawerTheme: const DrawerThemeData(backgroundColor: mpPanel, shape: RoundedRectangleBorder(borderRadius: BorderRadius.zero)),
        textTheme: ThemeData.dark().textTheme.apply(bodyColor: mpText, displayColor: mpText),
        dividerColor: mpBorder,
        inputDecorationTheme: const InputDecorationTheme(
          filled: true,
          fillColor: Color(0xff111315),
          labelStyle: TextStyle(color: mpMuted),
          hintStyle: TextStyle(color: mpMuted),
          border: OutlineInputBorder(borderRadius: BorderRadius.zero, borderSide: BorderSide(color: mpBorder)),
          enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.zero, borderSide: BorderSide(color: mpBorder)),
          focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.zero, borderSide: BorderSide(color: mpBlue)),
        ),
        filledButtonTheme: FilledButtonThemeData(
          style: ButtonStyle(
            backgroundColor: WidgetStateProperty.resolveWith((states) => states.contains(WidgetState.pressed) ? mpHover : mpPanel2),
            foregroundColor: const WidgetStatePropertyAll(Colors.white),
            overlayColor: const WidgetStatePropertyAll(mpHover),
            shape: WidgetStatePropertyAll(square),
          ),
        ),
        outlinedButtonTheme: OutlinedButtonThemeData(
          style: ButtonStyle(
            backgroundColor: const WidgetStatePropertyAll(mpPanel),
            foregroundColor: const WidgetStatePropertyAll(Colors.white),
            side: const WidgetStatePropertyAll(BorderSide(color: mpBorder)),
            overlayColor: const WidgetStatePropertyAll(mpHover),
            shape: WidgetStatePropertyAll(square),
          ),
        ),
        cardTheme: const CardThemeData(color: mpPanel2, surfaceTintColor: Colors.transparent, shape: RoundedRectangleBorder(borderRadius: BorderRadius.zero, side: BorderSide(color: mpBorder))),
        snackBarTheme: const SnackBarThemeData(backgroundColor: mpPanel2, contentTextStyle: TextStyle(color: Colors.white), shape: RoundedRectangleBorder(borderRadius: BorderRadius.zero), behavior: SnackBarBehavior.floating),
        dialogTheme: const DialogThemeData(backgroundColor: mpPanel, titleTextStyle: TextStyle(color: Colors.white, fontSize: 19, fontWeight: FontWeight.w600), contentTextStyle: TextStyle(color: mpText), shape: RoundedRectangleBorder(borderRadius: BorderRadius.zero, side: BorderSide(color: mpBorder))),
        popupMenuTheme: const PopupMenuThemeData(color: mpPanel2, textStyle: TextStyle(color: Colors.white)),
        listTileTheme: const ListTileThemeData(textColor: Colors.white, iconColor: Colors.white, selectedColor: Colors.white, selectedTileColor: mpHover),
        progressIndicatorTheme: const ProgressIndicatorThemeData(color: mpBlue),
        tooltipTheme: const TooltipThemeData(decoration: BoxDecoration(color: mpPanel2, border: Border.fromBorderSide(BorderSide(color: mpBorder))), textStyle: TextStyle(color: Colors.white)),
      ),
      home: const ConnectPage(),
    );
  }
}

class DiscoveredPc {
  final String name;
  final String serverId;
  final String host;
  final int port;
  final DateTime seenAt;

  DiscoveredPc({required this.name, required this.serverId, required this.host, required this.port, DateTime? seenAt}) : seenAt = seenAt ?? DateTime.now();

  factory DiscoveredPc.fromJson(Map<String, dynamic> json, {String? networkHost}) => DiscoveredPc(
        name: '${json['name'] ?? 'NEXO PC'}',
        serverId: '${json['serverId'] ?? ''}',
        host: networkHost?.isNotEmpty == true ? networkHost! : '${json['host'] ?? ''}',
        port: (json['port'] as num?)?.toInt() ?? 8765,
      );
}

class QrPairing {
  final TransportKind transport;
  final String serverId;
  final String token;
  final String? host;
  final int port;
  final String? service;

  const QrPairing({required this.transport, required this.serverId, required this.token, this.host, this.port = 8765, this.service});

  static QrPairing? parse(String raw) {
    try {
      final uri = Uri.parse(raw);
      if (uri.scheme != 'macropad' || uri.host != 'connect') return null;
      final token = uri.queryParameters['token'] ?? '';
      if (token.isEmpty) return null;
      return QrPairing(
        transport: uri.queryParameters['transport'] == 'ble' ? TransportKind.bluetooth : TransportKind.wifi,
        serverId: uri.queryParameters['serverId'] ?? '',
        token: token,
        host: uri.queryParameters['host'],
        port: int.tryParse(uri.queryParameters['port'] ?? '') ?? 8765,
        service: uri.queryParameters['service'],
      );
    } catch (_) {
      return null;
    }
  }
}

class SavedPc {
  final String serverId;
  final String name;
  final String host;
  final int port;
  final String deviceToken;
  final String transport;
  final String? bleDeviceId;
  final DateTime lastSeen;

  const SavedPc({required this.serverId, required this.name, required this.host, required this.port, required this.deviceToken, required this.transport, this.bleDeviceId, required this.lastSeen});

  SavedPc copyWith({String? name, String? host, int? port, String? deviceToken, String? transport, String? bleDeviceId, DateTime? lastSeen}) => SavedPc(
        serverId: serverId,
        name: name ?? this.name,
        host: host ?? this.host,
        port: port ?? this.port,
        deviceToken: deviceToken ?? this.deviceToken,
        transport: transport ?? this.transport,
        bleDeviceId: bleDeviceId ?? this.bleDeviceId,
        lastSeen: lastSeen ?? this.lastSeen,
      );

  Map<String, dynamic> toJson() => {
        'serverId': serverId,
        'name': name,
        'host': host,
        'port': port,
        'deviceToken': deviceToken,
        'transport': transport,
        'bleDeviceId': bleDeviceId,
        'lastSeen': lastSeen.toIso8601String(),
      };

  factory SavedPc.fromJson(Map<String, dynamic> json) => SavedPc(
        serverId: '${json['serverId'] ?? ''}',
        name: '${json['name'] ?? 'NEXO PC'}',
        host: '${json['host'] ?? ''}',
        port: (json['port'] as num?)?.toInt() ?? 8765,
        deviceToken: '${json['deviceToken'] ?? ''}',
        transport: '${json['transport'] ?? 'wifi'}',
        bleDeviceId: json['bleDeviceId']?.toString(),
        lastSeen: DateTime.tryParse('${json['lastSeen'] ?? ''}') ?? DateTime.now(),
      );
}

class DeviceStore {
  static const FlutterSecureStorage _storage = FlutterSecureStorage();
  static const _clientKey = 'macropad_client_id_v1';
  static const _pcsKey = 'macropad_saved_pcs_v1';

  static Future<String> clientId() async {
    final existing = await _storage.read(key: _clientKey);
    if (existing != null && existing.isNotEmpty) return existing;
    final random = '${DateTime.now().microsecondsSinceEpoch.toRadixString(16)}-${Platform.operatingSystem}-${DateTime.now().millisecondsSinceEpoch.toRadixString(36)}';
    final id = base64Url.encode(utf8.encode(random)).replaceAll('=', '');
    await _storage.write(key: _clientKey, value: id);
    return id;
  }

  static Future<Map<String, SavedPc>> load() async {
    try {
      final raw = await _storage.read(key: _pcsKey);
      if (raw == null || raw.isEmpty) return {};
      final list = jsonDecode(raw) as List;
      final map = <String, SavedPc>{};
      for (final item in list) {
        final pc = SavedPc.fromJson(Map<String, dynamic>.from(item as Map));
        if (pc.serverId.isNotEmpty && pc.deviceToken.isNotEmpty) map[pc.serverId] = pc;
      }
      return map;
    } catch (_) {
      return {};
    }
  }

  static Future<void> saveAll(Map<String, SavedPc> pcs) => _storage.write(key: _pcsKey, value: jsonEncode(pcs.values.map((e) => e.toJson()).toList()));

  static Future<void> upsert(SavedPc pc) async {
    final all = await load();
    all[pc.serverId] = pc;
    await saveAll(all);
  }

  static Future<void> remove(String serverId) async {
    final all = await load();
    all.remove(serverId);
    await saveAll(all);
  }
}

class ConnectPage extends StatefulWidget {
  const ConnectPage({super.key});
  @override
  State<ConnectPage> createState() => _ConnectPageState();
}

class _ConnectPageState extends State<ConnectPage> {
  TransportKind transport = TransportKind.wifi;
  final Map<String, DiscoveredPc> pcs = {};
  final Map<String, BleDevice> bleDevices = {};
  Map<String, SavedPc> savedPcs = {};
  RawDatagramSocket? udp;
  Timer? probeTimer;
  StreamSubscription<BleDevice>? bleScanSub;
  String status = 'Подготовка…';
  bool scanningBle = false;
  String clientId = '';

  @override
  void initState() {
    super.initState();
    _initialize();
  }

  Future<void> _initialize() async {
    clientId = await DeviceStore.clientId();
    savedPcs = await DeviceStore.load();
    if (mounted) setState(() {});
    await _startLanDiscovery();
  }

  @override
  void dispose() {
    probeTimer?.cancel();
    udp?.close();
    bleScanSub?.cancel();
    UniversalBle.stopScan();
    super.dispose();
  }

  Future<void> _reloadSaved() async {
    savedPcs = await DeviceStore.load();
    if (mounted) setState(() {});
  }

  Future<void> _startLanDiscovery() async {
    await _stopBleScan();
    udp?.close();
    probeTimer?.cancel();
    pcs.clear();
    try {
      final socket = await RawDatagramSocket.bind(InternetAddress.anyIPv4, 0);
      socket.broadcastEnabled = true;
      udp = socket;
      socket.listen((event) {
        if (event != RawSocketEvent.read) return;
        final datagram = socket.receive();
        if (datagram == null) return;
        try {
          final json = jsonDecode(utf8.decode(datagram.data));
          if (json is! Map<String, dynamic> || json['type'] != 'macropad_discovery') return;
          final pc = DiscoveredPc.fromJson(json, networkHost: datagram.address.address);
          if (pc.serverId.isEmpty) return;
          final oldSaved = savedPcs[pc.serverId];
          if (oldSaved != null && (oldSaved.host != pc.host || oldSaved.port != pc.port)) {
            final updated = oldSaved.copyWith(host: pc.host, port: pc.port, lastSeen: DateTime.now());
            savedPcs[pc.serverId] = updated;
            DeviceStore.upsert(updated);
          }
          if (!mounted) return;
          setState(() {
            pcs[pc.serverId] = pc;
            status = pcs.length == 1 ? 'Найден 1 компьютер' : 'Найдено компьютеров: ${pcs.length}';
          });
        } catch (_) {}
      });
      void probe() => socket.send(utf8.encode(discoveryProbe), InternetAddress('255.255.255.255'), discoveryPort);
      probe();
      probeTimer = Timer.periodic(const Duration(seconds: 2), (_) => probe());
      if (mounted) setState(() => status = 'Поиск NEXO в этой Wi‑Fi сети…');
    } catch (e) {
      if (mounted) setState(() => status = 'Не удалось запустить сетевой поиск: $e');
    }
  }

  Future<void> _startBleScan() async {
    udp?.close();
    udp = null;
    probeTimer?.cancel();
    pcs.clear();
    await UniversalBle.requestPermissions();
    await bleScanSub?.cancel();
    bleDevices.clear();
    bleScanSub = UniversalBle.scanStream.listen((device) {
      if (!mounted) return;
      setState(() {
        bleDevices[device.deviceId] = device;
        status = 'Найдено Bluetooth-устройств: ${bleDevices.length}';
      });
    });
    scanningBle = true;
    await UniversalBle.startScan(scanFilter: ScanFilter(withServices: [serviceUuid]));
    if (mounted) setState(() => status = 'Поиск NEXO по Bluetooth LE…');
  }

  Future<void> _stopBleScan() async {
    if (!scanningBle) return;
    scanningBle = false;
    try { await UniversalBle.stopScan(); } catch (_) {}
    await bleScanSub?.cancel();
    bleScanSub = null;
  }

  Future<void> _switchTransport(TransportKind value) async {
    if (value == transport) return;
    setState(() {
      transport = value;
      status = value == TransportKind.wifi ? 'Поиск компьютеров в сети…' : 'Поиск Bluetooth…';
    });
    if (value == TransportKind.wifi) {
      await _startLanDiscovery();
    } else {
      await _startBleScan();
    }
  }

  Future<void> _showSettings() async {
    await showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Row(children: [Icon(Icons.settings), SizedBox(width: 9), Text('Настройки')]),
        content: StatefulBuilder(
          builder: (context, setLocal) => SizedBox(
            width: 420,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Text('Способ подключения', style: TextStyle(color: mpMuted, fontSize: 11)),
                const SizedBox(height: 7),
                SegmentedButton<TransportKind>(
                  segments: const [
                    ButtonSegment(value: TransportKind.wifi, icon: Icon(Icons.wifi), label: Text('Wi‑Fi')),
                    ButtonSegment(value: TransportKind.bluetooth, icon: Icon(Icons.bluetooth), label: Text('Bluetooth')),
                  ],
                  selected: {transport},
                  onSelectionChanged: (values) async {
                    final next = values.first;
                    setLocal(() {});
                    Navigator.of(dialogContext).pop();
                    await _switchTransport(next);
                  },
                  style: ButtonStyle(
                    backgroundColor: WidgetStateProperty.resolveWith((states) => states.contains(WidgetState.selected) ? mpHover : mpPanel),
                    foregroundColor: const WidgetStatePropertyAll(Colors.white),
                    side: const WidgetStatePropertyAll(BorderSide(color: mpBorder)),
                    shape: const WidgetStatePropertyAll(RoundedRectangleBorder(borderRadius: BorderRadius.zero)),
                  ),
                ),
                const SizedBox(height: 10),
                Text(transport == TransportKind.wifi
                    ? 'Устройства в одной сети обнаруживаются автоматически. QR нужен только при первой привязке.'
                    : 'Bluetooth LE можно использовать для прямого соединения без общей Wi‑Fi сети.', style: const TextStyle(color: mpMuted)),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Future<QrPairing?> _scanQr() => Navigator.of(context).push<QrPairing>(MaterialPageRoute(builder: (_) => const QrScannerPage()));

  Future<void> _pairWifi(DiscoveredPc pc) async {
    final qr = await _scanQr();
    if (!mounted || qr == null) return;
    if (qr.transport != TransportKind.wifi) return _message('Этот QR-код предназначен для Bluetooth.');
    if (qr.serverId.isNotEmpty && qr.serverId != pc.serverId) return _message('QR-код относится к другому компьютеру.');
    final remote = WifiRemoteTransport(host: pc.host, port: pc.port, clientId: clientId, pairToken: qr.token);
    await _openRemote(remote, serverId: pc.serverId, serverName: pc.name, host: pc.host, port: pc.port, transportName: 'wifi');
  }

  Future<void> _pairBle(BleDevice device) async {
    final qr = await _scanQr();
    if (!mounted || qr == null) return;
    if (qr.transport != TransportKind.bluetooth) return _message('Этот QR-код предназначен для Wi‑Fi.');
    await _stopBleScan();
    final remote = BleRemoteTransport(device: device, clientId: clientId, pairToken: qr.token);
    await _openRemote(remote, serverId: qr.serverId, serverName: device.name ?? 'NEXO', host: '', port: 0, transportName: 'ble', bleDeviceId: device.deviceId);
    if (mounted && transport == TransportKind.bluetooth) await _startBleScan();
  }

  Future<void> _connectSaved(SavedPc saved) async {
    if (saved.transport == 'ble') {
      final deviceId = saved.bleDeviceId;
      if (deviceId == null || !bleDevices.containsKey(deviceId)) {
        if (transport != TransportKind.bluetooth) await _switchTransport(TransportKind.bluetooth);
        return _message('Привязанный Bluetooth ПК пока не найден. Дождитесь появления устройства в списке.');
      }
      final device = bleDevices[deviceId]!;
      final remote = BleRemoteTransport(device: device, clientId: clientId, deviceToken: saved.deviceToken);
      await _openRemote(remote, serverId: saved.serverId, serverName: saved.name, host: saved.host, port: saved.port, transportName: 'ble', bleDeviceId: deviceId);
      return;
    }

    final discovered = pcs[saved.serverId];
    final host = discovered?.host ?? saved.host;
    final port = discovered?.port ?? saved.port;
    if (host.isEmpty) return _message('Привязанный ПК сейчас не найден в локальной сети.');
    final remote = WifiRemoteTransport(host: host, port: port, clientId: clientId, deviceToken: saved.deviceToken);
    await _openRemote(remote, serverId: saved.serverId, serverName: discovered?.name ?? saved.name, host: host, port: port, transportName: 'wifi');
  }

  Future<void> _openRemote(RemoteTransport remote, {required String serverId, required String serverName, required String host, required int port, required String transportName, String? bleDeviceId}) async {
    try {
      final switchTo = await Navigator.of(context).push<String>(
        MaterialPageRoute(
          builder: (_) => RemotePage(
            transport: remote,
            formFactor: formFactorOf(context),
            clientId: clientId,
            initialServerId: serverId,
            initialServerName: serverName,
            host: host,
            port: port,
            transportName: transportName,
            bleDeviceId: bleDeviceId,
            savedDevices: savedPcs.values.toList(),
            onPaired: (pc) async {
              await DeviceStore.upsert(pc);
              savedPcs[pc.serverId] = pc;
            },
          ),
        ),
      );
      await _reloadSaved();
      if (switchTo != null && mounted) {
        if (switchTo == '__device_list__') return;
        final target = savedPcs[switchTo];
        if (target != null) await _connectSaved(target);
      }
    } catch (e) {
      if (mounted) _message('Не удалось подключиться: $e');
    }
  }

  void _message(String text) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));

  @override
  Widget build(BuildContext context) {
    final formFactor = formFactorOf(context);
    return Scaffold(
      appBar: AppBar(
        title: const Row(mainAxisSize: MainAxisSize.min, children: [MacroPadMark(size: 24), SizedBox(width: 10), Text('NEXO')]),
        actions: [
          Center(child: Text(formFactorLabel(formFactor), style: const TextStyle(fontSize: 11, color: mpMuted))),
          const SizedBox(width: 5),
          IconButton(tooltip: 'Повернуть экран', onPressed: () => toggleScreenOrientation(context), icon: const Icon(Icons.screen_rotation)),
          IconButton(tooltip: 'Настройки', onPressed: _showSettings, icon: const Icon(Icons.settings)),
          const SizedBox(width: 3),
        ],
      ),
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 760),
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Row(children: [
                    Expanded(child: Text(status, style: const TextStyle(color: mpMuted))),
                    IconButton(tooltip: 'Обновить поиск', onPressed: transport == TransportKind.wifi ? _startLanDiscovery : _startBleScan, icon: const Icon(Icons.refresh)),
                  ]),
                  if (savedPcs.isNotEmpty) ...[
                    const Text('Привязанные устройства', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
                    const SizedBox(height: 7),
                    SizedBox(height: 92, child: _savedDevicesStrip()),
                    const SizedBox(height: 12),
                  ],
                  Text(transport == TransportKind.wifi ? 'Компьютеры в этой сети' : 'Bluetooth устройства', style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
                  const SizedBox(height: 7),
                  Expanded(child: transport == TransportKind.wifi ? _wifiList() : _bleList()),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _savedDevicesStrip() {
    final values = savedPcs.values.toList()..sort((a, b) => b.lastSeen.compareTo(a.lastSeen));
    return ListView.separated(
      scrollDirection: Axis.horizontal,
      itemCount: values.length,
      separatorBuilder: (_, _) => const SizedBox(width: 7),
      itemBuilder: (_, index) {
        final saved = values[index];
        final online = saved.transport == 'wifi' ? pcs.containsKey(saved.serverId) : (saved.bleDeviceId != null && bleDevices.containsKey(saved.bleDeviceId));
        return InkWell(
          onTap: () => _connectSaved(saved),
          child: Container(
            width: 210,
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(color: mpPanel2, border: Border.all(color: online ? mpBlue : mpBorder)),
            child: Row(children: [
              Icon(saved.transport == 'ble' ? Icons.bluetooth : Icons.computer, color: online ? Colors.white : mpMuted),
              const SizedBox(width: 9),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.center, children: [
                Text(saved.name, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w600)),
                const SizedBox(height: 3),
                Text(online ? '● Доступен • без QR' : '○ Не в сети', style: TextStyle(color: online ? mpGreen : mpMuted, fontSize: 10)),
              ])),
              PopupMenuButton<String>(
                icon: const Icon(Icons.more_vert, size: 18),
                shape: const RoundedRectangleBorder(borderRadius: BorderRadius.zero),
                color: mpHover,
                onSelected: (value) async {
                  if (value == 'forget') {
                    await DeviceStore.remove(saved.serverId);
                    await _reloadSaved();
                  }
                },
                itemBuilder: (_) => const [PopupMenuItem(value: 'forget', child: Text('Забыть устройство', style: TextStyle(color: Colors.white)))],
              ),
            ]),
          ),
        );
      },
    );
  }

  Widget _wifiList() {
    if (pcs.isEmpty) return const _EmptyDiscovery(icon: Icons.wifi_find, text: 'Ожидание компьютера NEXO в локальной сети…');
    final values = pcs.values.toList()..sort((a, b) => a.name.compareTo(b.name));
    return ListView.separated(
      itemCount: values.length,
      separatorBuilder: (_, _) => const SizedBox(height: 7),
      itemBuilder: (_, index) {
        final pc = values[index];
        final saved = savedPcs[pc.serverId];
        return Card(
          margin: EdgeInsets.zero,
          child: ListTile(
            leading: const Icon(Icons.computer),
            title: Text(pc.name),
            subtitle: Text(saved == null ? '${pc.host}:${pc.port} • первая привязка через QR' : '${pc.host}:${pc.port} • привязан'),
            trailing: FilledButton(onPressed: () => saved == null ? _pairWifi(pc) : _connectSaved(saved.copyWith(host: pc.host, port: pc.port)), child: Text(saved == null ? 'QR' : 'Подключить')),
          ),
        );
      },
    );
  }

  Widget _bleList() {
    if (bleDevices.isEmpty) return const _EmptyDiscovery(icon: Icons.bluetooth_searching, text: 'Поиск NEXO по Bluetooth LE…');
    final values = bleDevices.values.toList();
    return ListView.separated(
      itemCount: values.length,
      separatorBuilder: (_, _) => const SizedBox(height: 7),
      itemBuilder: (_, index) {
        final device = values[index];
        final name = device.name?.trim().isNotEmpty == true ? device.name!.trim() : 'NEXO';
        final saved = savedPcs.values.where((x) => x.bleDeviceId == device.deviceId).firstOrNull;
        return Card(
          margin: EdgeInsets.zero,
          child: ListTile(
            leading: const Icon(Icons.bluetooth),
            title: Text(name),
            subtitle: Text(saved == null ? 'Первая привязка через QR' : 'Привязан • без QR'),
            trailing: FilledButton(onPressed: () => saved == null ? _pairBle(device) : _connectSaved(saved), child: Text(saved == null ? 'QR' : 'Подключить')),
          ),
        );
      },
    );
  }
}

extension _IterableFirstOrNull<T> on Iterable<T> {
  T? get firstOrNull => isEmpty ? null : first;
}

class _EmptyDiscovery extends StatelessWidget {
  final IconData icon;
  final String text;
  const _EmptyDiscovery({required this.icon, required this.text});
  @override
  Widget build(BuildContext context) => Center(child: Column(mainAxisSize: MainAxisSize.min, children: [Icon(icon, size: 54, color: mpMuted), const SizedBox(height: 12), Text(text, textAlign: TextAlign.center, style: const TextStyle(color: mpMuted))]));
}

class QrScannerPage extends StatefulWidget {
  const QrScannerPage({super.key});
  @override
  State<QrScannerPage> createState() => _QrScannerPageState();
}

class _QrScannerPageState extends State<QrScannerPage> {
  bool handled = false;
  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Row(children: [MacroPadMark(size: 22), SizedBox(width: 9), Text('Сканировать QR')])),
        body: MobileScanner(
          onDetect: (capture) {
            if (handled) return;
            for (final barcode in capture.barcodes) {
              final raw = barcode.rawValue;
              if (raw == null) continue;
              final pairing = QrPairing.parse(raw);
              if (pairing == null) continue;
              handled = true;
              Navigator.of(context).pop(pairing);
              return;
            }
          },
        ),
      );
}

abstract class RemoteTransport {
  Stream<String> get messages;
  String get label;
  Future<void> connect();
  Future<void> send(Map<String, dynamic> message);
  Future<void> close();
}

class WifiRemoteTransport implements RemoteTransport {
  final String host;
  final int port;
  final String clientId;
  final String? pairToken;
  final String? deviceToken;
  WebSocketChannel? channel;
  StreamController<String>? controller;
  StreamSubscription? subscription;

  WifiRemoteTransport({required this.host, required this.port, required this.clientId, this.pairToken, this.deviceToken});

  @override
  String get label => 'Wi‑Fi';
  @override
  Stream<String> get messages => controller!.stream;

  @override
  Future<void> connect() async {
    controller = StreamController<String>();
    final query = <String, String>{'clientId': clientId};
    if (pairToken?.isNotEmpty == true) query['token'] = pairToken!;
    if (deviceToken?.isNotEmpty == true) query['deviceToken'] = deviceToken!;
    final uri = Uri(scheme: 'ws', host: host, port: port, path: '/ws', queryParameters: query);
    final ch = WebSocketChannel.connect(uri);
    await ch.ready;
    channel = ch;
    subscription = ch.stream.listen((value) => controller?.add(value.toString()), onError: (Object error, StackTrace stack) => controller?.addError(error, stack), onDone: () => controller?.close());
  }

  @override
  Future<void> send(Map<String, dynamic> message) async => channel?.sink.add(jsonEncode(message));

  @override
  Future<void> close() async {
    await subscription?.cancel();
    await channel?.sink.close();
    await controller?.close();
  }
}

class BleRemoteTransport implements RemoteTransport {
  final BleDevice device;
  final String clientId;
  final String? pairToken;
  final String? deviceToken;
  final controller = StreamController<String>();
  BleCharacteristic? command;
  BleCharacteristic? state;
  StreamSubscription<Uint8List>? values;

  BleRemoteTransport({required this.device, required this.clientId, this.pairToken, this.deviceToken});

  @override
  String get label => 'Bluetooth LE';
  @override
  Stream<String> get messages => controller.stream;

  @override
  Future<void> connect() async {
    await device.connect();
    await device.discoverServices();
    command = await device.getCharacteristic(commandUuid, service: serviceUuid);
    state = await device.getCharacteristic(stateUuid, service: serviceUuid);
    values = UniversalBle.characteristicValueStream(device.deviceId, stateUuid).listen((data) async {
      final text = utf8.decode(data, allowMalformed: true);
      try {
        final json = jsonDecode(text);
        if (json is Map && json['type'] == 'state_changed') {
          await _readState();
        } else {
          controller.add(text);
        }
      } catch (_) { controller.add(text); }
    });
    try { await UniversalBle.subscribeNotifications(device.deviceId, serviceUuid, stateUuid); } catch (_) {}
    await command!.write(utf8.encode(jsonEncode({'type': 'auth', 'clientId': clientId, 'token': pairToken ?? '', 'deviceToken': deviceToken ?? ''})), withResponse: true);
    await Future<void>.delayed(const Duration(milliseconds: 150));
    await _readState();
  }

  Future<void> _readState() async {
    final data = await state!.read();
    if (data.isNotEmpty) controller.add(utf8.decode(data, allowMalformed: true));
  }

  @override
  Future<void> send(Map<String, dynamic> message) async => command!.write(utf8.encode(jsonEncode(message)), withResponse: true);

  @override
  Future<void> close() async {
    await values?.cancel();
    try { if (state != null) await state!.unsubscribe(); } catch (_) {}
    try { await device.disconnect(); } catch (_) {}
    await controller.close();
  }
}

class RemotePage extends StatefulWidget {
  final RemoteTransport transport;
  final ClientFormFactor formFactor;
  final String clientId;
  final String initialServerId;
  final String initialServerName;
  final String host;
  final int port;
  final String transportName;
  final String? bleDeviceId;
  final List<SavedPc> savedDevices;
  final Future<void> Function(SavedPc pc) onPaired;

  const RemotePage({super.key, required this.transport, required this.formFactor, required this.clientId, required this.initialServerId, required this.initialServerName, required this.host, required this.port, required this.transportName, required this.savedDevices, required this.onPaired, this.bleDeviceId});

  @override
  State<RemotePage> createState() => _RemotePageState();
}

class _RemotePageState extends State<RemotePage> with SingleTickerProviderStateMixin {
  StreamSubscription<String>? subscription;
  ProfileSnapshot? profile;
  List<WorkspaceProfileSummary> profiles = const [];
  int tab = 0;
  String status = 'Подключение…';
  String? connectionError;
  String serverId = '';
  String serverName = '';
  bool scaleLocked = false;
  bool panLocked = false;
  bool bottomNavVisible = false;
  Orientation? _lastOrientation;
  final TransformationController _deckTransform = TransformationController();
  late final AnimationController _deckReturnController;
  Animation<Matrix4>? _deckReturnAnimation;

  @override
  void initState() {
    super.initState();
    serverId = widget.initialServerId;
    serverName = widget.initialServerName;
    _deckReturnController = AnimationController(vsync: this, duration: const Duration(milliseconds: 260))
      ..addListener(() { if (_deckReturnAnimation != null) _deckTransform.value = _deckReturnAnimation!.value; });
    _connect();
  }

  Future<void> _connect() async {
    if (mounted) setState(() { status = 'Подключение…'; connectionError = null; });
    try {
      await widget.transport.connect();
      subscription = widget.transport.messages.listen(_onMessage, onError: (Object error) {
        if (mounted) setState(() { status = 'Ошибка связи'; connectionError = _friendlyConnectionError(error); });
      }, onDone: () {
        if (mounted) setState(() => status = 'Отключено');
      });
      await widget.transport.send({
        'type': 'clientInfo',
        'clientId': widget.clientId,
        'formFactor': widget.formFactor == ClientFormFactor.tablet ? 'tablet' : 'phone',
        'deviceName': '${formFactorLabel(widget.formFactor)} ${widget.clientId.length > 4 ? widget.clientId.substring(widget.clientId.length - 4) : widget.clientId}',
      });
      if (mounted) setState(() => status = widget.transport.label);
    } catch (e) {
      if (mounted) setState(() { status = 'Ошибка подключения'; connectionError = _friendlyConnectionError(e); });
    }
  }

  String _friendlyConnectionError(Object error) {
    final raw = error.toString();
    if (raw.contains('401')) return 'ПК отклонил сохранённую привязку. Удалите устройство из списка и выполните подключение через QR заново.';
    if (raw.contains('No route to host') || raw.contains('Network is unreachable')) return 'ПК найден, но сетевой адрес недоступен. Устройства должны быть в одной локальной сети.';
    if (raw.contains('Connection refused')) return 'ПК доступен, но NEXO не принимает соединение. Проверьте приложение на ПК и Windows Firewall.';
    return raw;
  }

  Future<void> _onMessage(String message) async {
    try {
      final json = jsonDecode(message);
      if (json is! Map<String, dynamic>) return;
      if (json['type'] == 'paired') {
        serverId = '${json['serverId'] ?? serverId}';
        serverName = '${json['serverName'] ?? serverName}';
        final token = '${json['deviceToken'] ?? ''}';
        if (token.isNotEmpty && serverId.isNotEmpty) {
          await widget.onPaired(SavedPc(
            serverId: serverId,
            name: serverName.isEmpty ? 'NEXO PC' : serverName,
            host: widget.host,
            port: widget.port,
            deviceToken: token,
            transport: widget.transportName,
            bleDeviceId: widget.bleDeviceId,
            lastSeen: DateTime.now(),
          ));
        }
        return;
      }
      if (json['type'] == 'profile' && json['profile'] is Map) {
        serverId = '${json['serverId'] ?? serverId}';
        serverName = '${json['serverName'] ?? serverName}';
        final pairedToken = '${json['deviceToken'] ?? ''}';
        if (pairedToken.isNotEmpty && serverId.isNotEmpty) {
          await widget.onPaired(SavedPc(
            serverId: serverId,
            name: serverName.isEmpty ? 'NEXO PC' : serverName,
            host: widget.host,
            port: widget.port,
            deviceToken: pairedToken,
            transport: widget.transportName,
            bleDeviceId: widget.bleDeviceId,
            lastSeen: DateTime.now(),
          ));
        }
        final p = ProfileSnapshot.fromJson(Map<String, dynamic>.from(json['profile'] as Map));
        final summaries = ((json['profiles'] ?? const []) as List)
            .map((item) => WorkspaceProfileSummary.fromJson(Map<String, dynamic>.from(item as Map)))
            .toList();
        if (mounted) setState(() { profile = p; profiles = summaries; });
      }
    } catch (_) {}
  }

  Future<void> _sendTile(TileSnapshot tile) async {
    await HapticFeedback.lightImpact();
    await widget.transport.send({'type': 'press', 'tileId': tile.id});
  }

  Future<void> _startLongPress(TileSnapshot tile) async {
    await HapticFeedback.mediumImpact();
    await widget.transport.send({'type': 'longPressStart', 'tileId': tile.id});
  }

  Future<void> _endLongPress(TileSnapshot tile) => widget.transport.send({'type': 'longPressEnd', 'tileId': tile.id});
  Future<void> _sendHotkey(String hotkey) => widget.transport.send({'type': 'hotkey', 'hotkey': hotkey});
  Future<void> _switchProfile(String profileId) => widget.transport.send({'type': 'switchProfile', 'profileId': profileId, 'force': true});
  Future<void> _switchPage(String pageId) => widget.transport.send({'type': 'switchPage', 'pageId': pageId});

  void _toggleScaleLock() => setState(() => scaleLocked = !scaleLocked);
  void _togglePanLock() => setState(() => panLocked = !panLocked);
  void _fitDeck() {
    _deckReturnController.stop();
    _deckReturnAnimation = Matrix4Tween(begin: _deckTransform.value.clone(), end: Matrix4.identity())
        .animate(CurvedAnimation(parent: _deckReturnController, curve: Curves.easeOutCubic));
    _deckReturnController.forward(from: 0);
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final o = MediaQuery.orientationOf(context);
    if (_lastOrientation != null && _lastOrientation != o) {
      WidgetsBinding.instance.addPostFrameCallback((_) { if (mounted) _fitDeck(); });
      if (o == Orientation.landscape) bottomNavVisible = false;
    }
    _lastOrientation = o;
  }

  Future<void> _forgetCurrentDevice() async {
    if (serverId.isEmpty) return;
    await DeviceStore.remove(serverId);
    await widget.transport.close();
    if (mounted) Navigator.of(context).pop();
  }

  @override
  void dispose() {
    subscription?.cancel();
    _deckReturnController.dispose();
    _deckTransform.dispose();
    widget.transport.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final pages = <Widget>[deck(), media()];
    if (tab >= pages.length) tab = 0;
    final compact = widget.formFactor == ClientFormFactor.phone && MediaQuery.orientationOf(context) == Orientation.landscape;
    return PopScope(
      canPop: false,
      child: Scaffold(
        drawer: _drawer(compact: compact),
        appBar: AppBar(
          toolbarHeight: compact ? 38 : null,
          titleSpacing: compact ? 8 : null,
          title: Row(mainAxisSize: MainAxisSize.min, children: [MacroPadMark(size: compact ? 17 : 22), SizedBox(width: compact ? 6 : 9), Flexible(child: Text(profile?.name ?? 'NEXO', overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: compact ? 13 : null)))]),
          actions: [
            IconButton(tooltip: 'Повернуть экран', visualDensity: compact ? VisualDensity.compact : VisualDensity.standard, onPressed: () => toggleScreenOrientation(context), icon: Icon(Icons.screen_rotation, size: compact ? 19 : 23)),
            Padding(padding: EdgeInsets.only(right: compact ? 5 : 10), child: Center(child: Row(children: [Icon(Icons.circle, size: 7, color: connectionError == null && status != 'Отключено' ? mpGreen : mpMuted), const SizedBox(width: 5), if (!compact) Text(status, style: const TextStyle(fontSize: 11))]))),
          ],
        ),
        body: SafeArea(child: connectionError == null ? _workspaceBody(pages, compact) : _connectionErrorView()),
        bottomNavigationBar: connectionError == null && !compact ? _SharpBottomNav(compact: false, selectedIndex: tab, onSelected: (value) => setState(() => tab = value), items: const [_SharpNavItem(Icons.grid_view, 'Deck'), _SharpNavItem(Icons.play_circle_outline, 'Media')]) : null,
      ),
    );
  }


  Widget _workspaceBody(List<Widget> pages, bool compact) {
    if (!compact) return pages[tab];
    return Stack(children: [
      Positioned.fill(child: pages[tab]),
      if (bottomNavVisible)
        Positioned(left: 18, right: 18, bottom: 26, child: ClipRRect(
          borderRadius: BorderRadius.circular(14),
          child: _SharpBottomNav(compact: true, selectedIndex: tab, onSelected: (value) => setState(() => tab = value), items: const [_SharpNavItem(Icons.grid_view, 'Deck'), _SharpNavItem(Icons.play_circle_outline, 'Media')]),
        )),
      Positioned(left: 0, right: 0, bottom: 2, child: Center(child: Material(
        color: mpPanel2,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12), side: const BorderSide(color: mpBorder)),
        child: InkWell(borderRadius: BorderRadius.circular(12), onTap: () => setState(() => bottomNavVisible = !bottomNavVisible),
          child: Padding(padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 3), child: Icon(bottomNavVisible ? Icons.keyboard_arrow_down : Icons.keyboard_arrow_up, size: 18))),
      ))),
    ]);
  }

  Widget _drawer({required bool compact}) {
    final activeId = profile?.id;
    final saved = widget.savedDevices;
    return Drawer(
      width: compact ? 250 : null,
      child: SafeArea(
        child: Column(
          children: [
            Container(
              height: 68,
              padding: const EdgeInsets.symmetric(horizontal: 16),
              decoration: const BoxDecoration(border: Border(bottom: BorderSide(color: mpBorder))),
              child: Row(children: [const MacroPadMark(size: 28), const SizedBox(width: 11), Expanded(child: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.start, children: [const Text('NEXO', style: TextStyle(fontWeight: FontWeight.w600)), Text(serverName.isEmpty ? 'Подключено' : serverName, style: const TextStyle(color: mpMuted, fontSize: 11))]))]),
            ),
            Expanded(
              child: ListView(
                padding: EdgeInsets.zero,
                children: [
                  const Padding(padding: EdgeInsets.fromLTRB(16, 14, 16, 6), child: Text('ПРОФИЛИ', style: TextStyle(color: mpMuted, fontSize: 10, letterSpacing: 1))),
                  for (final item in profiles)
                    ListTile(
                      dense: true,
                      selected: item.id == activeId,
                      selectedTileColor: mpHover,
                      leading: Text(item.icon.isEmpty ? '•' : item.icon, style: TextStyle(color: item.id == activeId ? mpBlue : Colors.white, fontWeight: FontWeight.bold)),
                      title: Text(item.name),
                      onTap: () async { Navigator.of(context).pop(); if (item.id != activeId) await _switchProfile(item.id); },
                    ),
                  if (profile != null) ...[
                    const Divider(height: 1),
                    const Padding(padding: EdgeInsets.fromLTRB(16, 14, 16, 6), child: Text('СТРАНИЦЫ', style: TextStyle(color: mpMuted, fontSize: 10, letterSpacing: 1))),
                    for (var i = 0; i < profile!.pages.length; i++)
                      ListTile(
                        dense: true,
                        selected: profile!.pages[i].id == profile!.pageId,
                        selectedTileColor: mpHover,
                        leading: SizedBox(width: 24, child: Text('${i + 1}', textAlign: TextAlign.center)),
                        title: Text(profile!.pages[i].name),
                        onTap: () async { Navigator.of(context).pop(); if (profile!.pages[i].id != profile!.pageId) await _switchPage(profile!.pages[i].id); },
                      ),
                  ],
                  const Divider(height: 1),
                  const Padding(padding: EdgeInsets.fromLTRB(16, 14, 16, 6), child: Text('СМЕНИТЬ УСТРОЙСТВО', style: TextStyle(color: mpMuted, fontSize: 10, letterSpacing: 1))),
                  for (final pc in saved)
                    ListTile(
                      dense: true,
                      selected: pc.serverId == serverId,
                      selectedTileColor: mpHover,
                      leading: Icon(pc.transport == 'ble' ? Icons.bluetooth : Icons.computer, size: 20),
                      title: Text(pc.name, maxLines: 1, overflow: TextOverflow.ellipsis),
                      subtitle: Text(pc.serverId == serverId ? 'Текущее устройство' : 'Переключить без QR', style: const TextStyle(fontSize: 10, color: mpMuted)),
                      onTap: pc.serverId == serverId ? null : () {
                        Navigator.of(context).pop();
                        Future<void>.delayed(const Duration(milliseconds: 120), () {
                          if (mounted) Navigator.of(context).pop(pc.serverId);
                        });
                      },
                    ),
                  const Divider(height: 1),
                  ListTile(
                    dense: true,
                    leading: const Icon(Icons.devices_other, size: 20),
                    title: const Text('Сменить устройство'),
                    subtitle: const Text('Вернуться к списку устройств', style: TextStyle(fontSize: 10, color: mpMuted)),
                    onTap: () { Navigator.of(context).pop(); Future<void>.delayed(const Duration(milliseconds: 100), () { if (mounted) Navigator.of(context).pop('__device_list__'); }); },
                  ),
                  ListTile(
                    dense: true,
                    leading: const Icon(Icons.link_off, size: 20),
                    title: const Text('Забыть текущее устройство'),
                    subtitle: const Text('Для следующего подключения потребуется QR', style: TextStyle(fontSize: 10, color: mpMuted)),
                    onTap: () async { Navigator.of(context).pop(); await _forgetCurrentDevice(); },
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _connectionErrorView() => Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 560),
          child: Container(
            margin: const EdgeInsets.all(18),
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(color: mpPanel, border: Border.all(color: mpBorder)),
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              const Text('Не удалось подключиться', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w600)),
              const SizedBox(height: 10),
              Text(connectionError ?? '', style: const TextStyle(color: mpMuted)),
              const SizedBox(height: 14),
              Row(children: [Expanded(child: OutlinedButton(onPressed: () => Navigator.of(context).pop('__device_list__'), child: const Text('Сменить устройство'))), const SizedBox(width: 8), Expanded(child: FilledButton(onPressed: _connect, child: const Text('Повторить')))]),
            ]),
          ),
        ),
      );

  Widget deck() {
    final p = profile;
    if (p == null) return const Center(child: CircularProgressIndicator());
    return Column(
      children: [
        Expanded(child: _deckCanvas(p)),
        _pageSelector(p),
      ],
    );
  }

  Widget _pageSelector(ProfileSnapshot p) {
    if (p.pages.length <= 1) return const SizedBox(height: 6);
    return Container(
      height: widget.formFactor == ClientFormFactor.phone && MediaQuery.orientationOf(context) == Orientation.landscape ? 34 : 48,
      decoration: const BoxDecoration(color: mpPanel, border: Border(bottom: BorderSide(color: mpBorder))),
      child: ListView.separated(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
        scrollDirection: Axis.horizontal,
        itemCount: p.pages.length,
        separatorBuilder: (_, _) => const SizedBox(width: 5),
        itemBuilder: (_, i) {
          final page = p.pages[i];
          final selected = page.id == p.pageId;
          return InkWell(
            onTap: selected ? null : () => _switchPage(page.id),
            child: Container(
              constraints: const BoxConstraints(minWidth: 34),
              padding: const EdgeInsets.symmetric(horizontal: 10),
              decoration: BoxDecoration(color: selected ? mpHover : mpPanel2, border: Border.all(color: selected ? mpBlue : mpBorder)),
              alignment: Alignment.center,
              child: Text('${i + 1}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600)),
            ),
          );
        },
      ),
    );
  }

  Widget _deckCanvas(ProfileSnapshot p) {
    return LayoutBuilder(
      builder: (_, constraints) {
        final columns = p.columns.clamp(1, 12).toInt();
        final rows = p.rows.clamp(1, 12).toInt();
        const gapBase = 7.0;
        const padBase = 10.0;
        final compact = widget.formFactor == ClientFormFactor.phone && MediaQuery.orientationOf(context) == Orientation.landscape;
        final availableW = (constraints.maxWidth - padBase * 2 - gapBase * (columns - 1)).clamp(1.0, double.infinity);
        final availableH = (constraints.maxHeight - padBase * 2 - gapBase * (rows - 1)).clamp(1.0, double.infinity);
        final fitW = availableW / columns;
        final fitH = availableH / rows;
        final cellW = min(fitW, fitH / .76).clamp(18.0, 150.0);
        final cellH = cellW * .76;
        final uiScale = (cellW / 105).clamp(.38, 1.18);
        final packed = packTiles(p.tiles, rows, columns);
        final totalW = padBase * 2 + columns * cellW + (columns - 1) * gapBase;
        final totalH = padBase * 2 + rows * cellH + (rows - 1) * gapBase;
        final canvas = SizedBox(
          width: totalW, height: totalH,
          child: Stack(children: [
            for (final item in packed) Positioned(
              left: padBase + item.column * (cellW + gapBase),
              top: padBase + item.row * (cellH + gapBase),
              width: item.columnSpan * cellW + (item.columnSpan - 1) * gapBase,
              height: item.rowSpan * cellH + (item.rowSpan - 1) * gapBase,
              child: _remoteTile(item.tile, uiScale),
            ),
          ]),
        );
        return Stack(children: [
          Center(child: InteractiveViewer(
            transformationController: _deckTransform,
            panEnabled: !panLocked, scaleEnabled: !scaleLocked,
            minScale: .35, maxScale: 3.2, boundaryMargin: const EdgeInsets.all(500), constrained: false,
            child: canvas,
          )),
          Positioned(right: compact ? 5 : 8, top: compact ? 5 : 8, child: Material(
            color: const Color(0xee202326),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10), side: const BorderSide(color: mpBorder)),
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              IconButton(tooltip: scaleLocked ? 'Разблокировать масштаб' : 'Зафиксировать масштаб', onPressed: _toggleScaleLock, icon: Icon(scaleLocked ? Icons.lock : Icons.lock_open), iconSize: compact ? 16 : 19, visualDensity: VisualDensity.compact),
              IconButton(tooltip: panLocked ? 'Разблокировать перемещение' : 'Заблокировать перемещение', onPressed: _togglePanLock, icon: Icon(panLocked ? Icons.pan_tool_alt : Icons.pan_tool_outlined), iconSize: compact ? 16 : 19, visualDensity: VisualDensity.compact),
              IconButton(tooltip: 'Вписать и центрировать', onPressed: _fitDeck, icon: const Icon(Icons.center_focus_strong), iconSize: compact ? 16 : 19, visualDensity: VisualDensity.compact),
            ]),
          )),
        ]);
      },
    );
  }

  Widget _remoteTile(TileSnapshot tile, double scale) {
    final blank = tile.actionType.isEmpty && tile.title.toLowerCase() == 'добавить';
    final iconSize = (27 * scale).clamp(13.0, 30.0);
    final fontSize = (12 * scale).clamp(7.5, 13.0);
    final padding = (7 * scale).clamp(2.0, 8.0);
    return Material(
      color: blank ? mpPanel : mpPanel2,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.zero, side: BorderSide(color: mpBorder, width: 1)),
      child: GestureDetector(
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
    );
  }

  Widget _tileIcon(TileSnapshot tile, double size, bool blank) {
    final color = blank ? const Color(0xff7c8287) : Colors.white;
    if (tile.iconKind == 'image' && tile.iconValue.isNotEmpty) {
      try {
        final comma = tile.iconValue.indexOf(',');
        final payload = comma >= 0 ? tile.iconValue.substring(comma + 1) : tile.iconValue;
        final bytes = base64Decode(payload);
        return SizedBox(width: size * 1.55, height: size * 1.55, child: Image.memory(bytes, fit: BoxFit.contain, gaplessPlayback: true));
      } catch (_) {}
    }
    if (tile.iconKind == 'glyph' && tile.iconValue.isNotEmpty) {
      return Text(tile.iconValue, style: TextStyle(fontSize: size, color: color, fontWeight: FontWeight.w600, height: 1));
    }
    return Icon(_iconFor(tile), size: size, color: color);
  }

  IconData _iconFor(TileSnapshot tile) => switch (tile.actionType) {
        'hotkey' => Icons.keyboard,
        'text' => Icons.text_fields,
        'open' => Icons.open_in_new,
        'url' => Icons.public,
        'folder' => Icons.folder_outlined,
        'multi' => Icons.queue_play_next,
        'profile' => Icons.swap_horiz,
        'media' => Icons.play_arrow,
        _ => Icons.add,
      };

  Widget media() => Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 520),
          child: GridView.count(
            padding: const EdgeInsets.all(18),
            shrinkWrap: true,
            crossAxisCount: 2,
            mainAxisSpacing: 8,
            crossAxisSpacing: 8,
            childAspectRatio: 2.0,
            children: [
              _mediaButton(Icons.volume_down, 'Громкость −', 'VOLUME_DOWN'),
              _mediaButton(Icons.volume_up, 'Громкость +', 'VOLUME_UP'),
              _mediaButton(Icons.play_arrow, 'Play / Pause', 'MEDIA_PLAY'),
              _mediaButton(Icons.volume_off, 'Без звука', 'VOLUME_MUTE'),
            ],
          ),
        ),
      );

  Widget _mediaButton(IconData icon, String label, String hotkey) => Material(
        color: mpPanel2,
        shape: const RoundedRectangleBorder(borderRadius: BorderRadius.zero, side: BorderSide(color: mpBorder)),
        child: InkWell(onTap: () => _sendHotkey(hotkey), child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [Icon(icon, color: Colors.white, size: 30), const SizedBox(height: 7), Text(label, textAlign: TextAlign.center, style: const TextStyle(color: Colors.white))])),
      );
}

class _SharpNavItem {
  final IconData icon;
  final String label;
  const _SharpNavItem(this.icon, this.label);
}

class _SharpBottomNav extends StatelessWidget {
  final int selectedIndex;
  final ValueChanged<int> onSelected;
  final List<_SharpNavItem> items;
  final bool compact;
  const _SharpBottomNav({required this.selectedIndex, required this.onSelected, required this.items, this.compact = false});

  @override
  Widget build(BuildContext context) => Container(
        decoration: const BoxDecoration(color: mpPanel, border: Border(top: BorderSide(color: mpBorder))),
        child: SafeArea(
          top: false,
          child: SizedBox(
            height: compact ? 44 : 66,
            child: Row(children: [
              for (var i = 0; i < items.length; i++)
                Expanded(
                  child: InkWell(
                    onTap: () => onSelected(i),
                    child: Container(
                      decoration: BoxDecoration(color: i == selectedIndex ? mpHover : mpPanel, border: Border(top: BorderSide(color: i == selectedIndex ? mpBlue : Colors.transparent, width: 2), right: i < items.length - 1 ? const BorderSide(color: mpBorder) : BorderSide.none)),
                      child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [Icon(items[i].icon, color: Colors.white, size: compact ? 18 : 23), SizedBox(height: compact ? 1 : 4), Text(items[i].label, style: TextStyle(color: Colors.white, fontSize: compact ? 9 : 11))]),
                    ),
                  ),
                ),
            ]),
          ),
        ),
      );
}

class PageSummary {
  final String id;
  final String name;
  const PageSummary({required this.id, required this.name});
  factory PageSummary.fromJson(Map<String, dynamic> json) => PageSummary(id: '${json['id'] ?? ''}', name: '${json['name'] ?? 'Страница'}');
}

class WorkspaceProfileSummary {
  final String id;
  final String name;
  final String icon;
  final String activePageId;
  final List<PageSummary> pages;
  const WorkspaceProfileSummary({required this.id, required this.name, required this.icon, required this.activePageId, required this.pages});
  factory WorkspaceProfileSummary.fromJson(Map<String, dynamic> json) => WorkspaceProfileSummary(
        id: '${json['id'] ?? ''}',
        name: '${json['name'] ?? 'Profile'}',
        icon: '${json['icon'] ?? ''}',
        activePageId: '${json['activePageId'] ?? ''}',
        pages: ((json['pages'] ?? const []) as List).map((x) => PageSummary.fromJson(Map<String, dynamic>.from(x as Map))).toList(),
      );
}

class ProfileSnapshot {
  final String id;
  final String name;
  final String icon;
  final String pageId;
  final String pageName;
  final int rows;
  final int columns;
  final List<PageSummary> pages;
  final List<TileSnapshot> tiles;
  const ProfileSnapshot({required this.id, required this.name, required this.icon, required this.pageId, required this.pageName, required this.rows, required this.columns, required this.pages, required this.tiles});

  factory ProfileSnapshot.fromJson(Map<String, dynamic> json) => ProfileSnapshot(
        id: '${json['id'] ?? ''}',
        name: '${json['name'] ?? 'Profile'}',
        icon: '${json['icon'] ?? ''}',
        pageId: '${json['pageId'] ?? json['activePageId'] ?? ''}',
        pageName: '${json['pageName'] ?? 'Страница'}',
        rows: (json['rows'] as num?)?.toInt() ?? 3,
        columns: (json['columns'] as num?)?.toInt() ?? 4,
        pages: ((json['pages'] ?? const []) as List).map((x) => PageSummary.fromJson(Map<String, dynamic>.from(x as Map))).toList(),
        tiles: ((json['tiles'] ?? const []) as List).map((item) => TileSnapshot.fromJson(Map<String, dynamic>.from(item as Map))).toList(),
      );
}

class TileSnapshot {
  final String id;
  final String title;
  final String actionType;
  final String iconKind;
  final String iconValue;
  final bool showLabel;
  final int rowSpan;
  final int columnSpan;
  const TileSnapshot({required this.id, required this.title, required this.actionType, required this.iconKind, required this.iconValue, required this.showLabel, required this.rowSpan, required this.columnSpan});
  factory TileSnapshot.fromJson(Map<String, dynamic> json) => TileSnapshot(
        id: '${json['id'] ?? ''}',
        title: '${json['title'] ?? 'Кнопка'}',
        actionType: '${json['actionType'] ?? ''}',
        iconKind: '${json['iconKind'] ?? 'auto'}',
        iconValue: '${json['iconValue'] ?? ''}',
        showLabel: json['showLabel'] != false,
        rowSpan: ((json['rowSpan'] as num?)?.toInt() ?? 1).clamp(1, 12).toInt(),
        columnSpan: ((json['columnSpan'] as num?)?.toInt() ?? 1).clamp(1, 12).toInt(),
      );
}

class PackedTile {
  final TileSnapshot tile;
  final int row;
  final int column;
  final int rowSpan;
  final int columnSpan;
  const PackedTile(this.tile, this.row, this.column, this.rowSpan, this.columnSpan);
}

List<PackedTile> packTiles(List<TileSnapshot> tiles, int rawRows, int rawColumns) {
  final rows = rawRows.clamp(1, 12).toInt();
  final columns = rawColumns.clamp(1, 12).toInt();
  final used = List.generate(rows, (_) => List<bool>.filled(columns, false));
  final result = <PackedTile>[];
  for (final tile in tiles) {
    final rs = tile.rowSpan.clamp(1, rows);
    final cs = tile.columnSpan.clamp(1, columns);
    var placed = false;
    for (var row = 0; row < rows && !placed; row++) {
      for (var column = 0; column < columns && !placed; column++) {
        if (row + rs > rows || column + cs > columns) continue;
        var free = true;
        for (var y = 0; y < rs && free; y++) {
          for (var x = 0; x < cs; x++) {
            if (used[row + y][column + x]) { free = false; break; }
          }
        }
        if (!free) continue;
        for (var y = 0; y < rs; y++) {
          for (var x = 0; x < cs; x++) {
            used[row + y][column + x] = true;
          }
        }
        result.add(PackedTile(tile, row, column, rs, cs));
        placed = true;
      }
    }
  }
  return result;
}
