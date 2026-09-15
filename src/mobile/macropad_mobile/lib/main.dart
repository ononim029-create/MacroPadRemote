import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

void main() => runApp(const MacroPadApp());

class MacroPadApp extends StatelessWidget {
  const MacroPadApp({super.key});
  @override
  Widget build(BuildContext context) {
    final scheme = const ColorScheme.dark(
      primary: Colors.white,
      onPrimary: Colors.black,
      surface: Color(0xff1d1f21),
      onSurface: Colors.white,
      secondary: Color(0xff1688ff),
    );
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'MacroPad Remote',
      theme: ThemeData.dark(useMaterial3: true).copyWith(
        colorScheme: scheme,
        scaffoldBackgroundColor: const Color(0xff17191b),
        appBarTheme: const AppBarTheme(backgroundColor: Color(0xff17191b)),
        inputDecorationTheme: const InputDecorationTheme(
          filled: true,
          fillColor: Color(0xff111315),
          border: OutlineInputBorder(borderRadius: BorderRadius.zero),
          enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.zero, borderSide: BorderSide(color: Color(0xff353a3e))),
          focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.zero, borderSide: BorderSide(color: Colors.white)),
        ),
        filledButtonTheme: FilledButtonThemeData(style: FilledButton.styleFrom(shape: const RoundedRectangleBorder(borderRadius: BorderRadius.zero))),
        outlinedButtonTheme: OutlinedButtonThemeData(style: OutlinedButton.styleFrom(shape: const RoundedRectangleBorder(borderRadius: BorderRadius.zero))),
        cardTheme: const CardThemeData(shape: RoundedRectangleBorder(borderRadius: BorderRadius.zero), color: Color(0xff202326)),
      ),
      home: const ConnectPage(),
    );
  }
}

class ConnectPage extends StatefulWidget {
  const ConnectPage({super.key});
  @override
  State<ConnectPage> createState() => _ConnectPageState();
}

class _ConnectPageState extends State<ConnectPage> {
  final host = TextEditingController(text: '192.168.1.100');
  final port = TextEditingController(text: '8765');
  final code = TextEditingController();
  String transport = 'wifi';

  Future<void> scanQr() async {
    final value = await Navigator.push<String>(context, MaterialPageRoute(builder: (_) => const QrScannerPage()));
    if (value == null) return;
    try {
      final uri = Uri.parse(value);
      if (uri.scheme != 'macropad' || uri.host != 'connect') throw const FormatException('wrong scheme');
      final h = uri.queryParameters['host'];
      final p = uri.queryParameters['port'];
      final t = uri.queryParameters['token'];
      if (h == null || p == null || t == null) throw const FormatException('missing fields');
      setState(() {
        transport = 'wifi';
        host.text = h;
        port.text = p;
        code.text = t;
      });
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('QR-код не относится к MacroPad Remote')));
    }
  }

  void connect() {
    if (transport != 'wifi') {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Bluetooth будет подключён в следующей preview-сборке')));
      return;
    }
    final h = host.text.trim();
    final p = int.tryParse(port.text.trim()) ?? 8765;
    final token = code.text.trim();
    if (h.isEmpty || token.isEmpty) return;
    Navigator.push(context, MaterialPageRoute(builder: (_) => RemotePage(url: 'ws://$h:$p/ws?token=$token')));
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('MacroPad Remote')),
        body: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(22),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 520),
              child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                const Icon(Icons.grid_view_rounded, size: 64),
                const SizedBox(height: 18),
                const Text('Подключение к ПК', style: TextStyle(fontSize: 25, fontWeight: FontWeight.w600)),
                const SizedBox(height: 18),
                SegmentedButton<String>(
                  segments: const [
                    ButtonSegment(value: 'wifi', label: Text('Wi‑Fi'), icon: Icon(Icons.wifi)),
                    ButtonSegment(value: 'bluetooth', label: Text('Bluetooth'), icon: Icon(Icons.bluetooth)),
                  ],
                  selected: {transport},
                  onSelectionChanged: (value) => setState(() => transport = value.first),
                  style: const ButtonStyle(shape: WidgetStatePropertyAll(RoundedRectangleBorder(borderRadius: BorderRadius.zero))),
                ),
                const SizedBox(height: 14),
                TextField(controller: host, enabled: transport == 'wifi', decoration: const InputDecoration(labelText: 'IP компьютера')),
                const SizedBox(height: 10),
                TextField(controller: port, enabled: transport == 'wifi', keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Порт')),
                const SizedBox(height: 10),
                TextField(controller: code, enabled: transport == 'wifi', keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Код подключения')),
                const SizedBox(height: 12),
                OutlinedButton.icon(onPressed: transport == 'wifi' ? scanQr : null, icon: const Icon(Icons.qr_code_scanner), label: const Padding(padding: EdgeInsets.all(13), child: Text('Сканировать QR-код'))),
                const SizedBox(height: 10),
                FilledButton(onPressed: connect, child: const Padding(padding: EdgeInsets.all(14), child: Text('Подключиться'))),
                if (transport == 'bluetooth') const Padding(padding: EdgeInsets.only(top: 12), child: Text('Bluetooth выбран. BLE-транспорт будет активирован следующим этапом.', style: TextStyle(color: Colors.grey))),
              ]),
            ),
          ),
        ),
      );
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
        appBar: AppBar(title: const Text('Сканировать QR')),
        body: Stack(children: [
          MobileScanner(
            onDetect: (capture) {
              if (handled || capture.barcodes.isEmpty) return;
              final raw = capture.barcodes.first.rawValue;
              if (raw == null || raw.isEmpty) return;
              handled = true;
              Navigator.pop(context, raw);
            },
          ),
          Center(child: Container(width: 250, height: 250, decoration: BoxDecoration(border: Border.all(color: Colors.white, width: 2)))),
          const Positioned(left: 20, right: 20, bottom: 28, child: Text('Наведите камеру на QR-код в приложении на ПК', textAlign: TextAlign.center)),
        ]),
      );
}

class RemotePage extends StatefulWidget {
  final String url;
  const RemotePage({super.key, required this.url});
  @override
  State<RemotePage> createState() => _RemotePageState();
}

class _RemotePageState extends State<RemotePage> {
  WebSocketChannel? channel;
  StreamSubscription? sub;
  RemoteProfile? profile;
  int tab = 0;
  String status = 'Подключение...';

  @override
  void initState() { super.initState(); connect(); }

  Future<void> connect() async {
    try {
      final ch = WebSocketChannel.connect(Uri.parse(widget.url));
      await ch.ready;
      if (!mounted) return;
      setState(() { channel = ch; status = 'Подключено'; });
      sub = ch.stream.listen(onData, onError: (_) { if (mounted) setState(() => status = 'Ошибка'); }, onDone: () { if (mounted) setState(() => status = 'Отключено'); });
    } catch (_) { if (mounted) setState(() => status = 'Не удалось подключиться'); }
  }

  void onData(dynamic message) {
    try {
      final json = jsonDecode(message as String);
      if (json['type'] == 'profile' && json['profile'] != null) setState(() => profile = RemoteProfile.fromJson(Map<String, dynamic>.from(json['profile'])));
    } catch (_) {}
  }

  void send(String hotkey) { if (hotkey.isNotEmpty) channel?.sink.add(jsonEncode({'hotkey': hotkey})); }
  @override
  void dispose() { sub?.cancel(); channel?.sink.close(); super.dispose(); }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: Text(profile?.name ?? 'MacroPad Remote'), actions: [Padding(padding: const EdgeInsets.only(right: 14), child: Center(child: Row(children: [Icon(Icons.circle, size: 9, color: status == 'Подключено' ? Colors.green : Colors.grey), const SizedBox(width: 7), Text(status)])))]),
        body: SafeArea(child: [deck(), touchpad(), keyboard(), media()][tab]),
        bottomNavigationBar: NavigationBar(
          selectedIndex: tab,
          onDestinationSelected: (i) => setState(() => tab = i),
          destinations: const [
            NavigationDestination(icon: Icon(Icons.grid_view), label: 'Deck'),
            NavigationDestination(icon: Icon(Icons.touch_app), label: 'Touchpad'),
            NavigationDestination(icon: Icon(Icons.keyboard), label: 'Keyboard'),
            NavigationDestination(icon: Icon(Icons.play_circle), label: 'Media'),
          ],
        ),
      );

  Widget deck() {
    final p = profile;
    if (p == null) return const Center(child: CircularProgressIndicator());
    return LayoutBuilder(builder: (context, bounds) {
      const gap = 7.0;
      final cols = p.columns.clamp(1, 12).toInt();
      final rows = p.rows.clamp(1, 12).toInt();
      final cellW = (bounds.maxWidth - 24 - gap * (cols - 1)) / cols;
      final cellH = cellW * 0.82;
      final placements = packTiles(p.tiles, rows, cols);
      final height = rows * cellH + gap * (rows - 1) + 24;
      return SingleChildScrollView(
        padding: const EdgeInsets.all(12),
        child: SizedBox(
          height: height,
          child: Stack(
            children: placements.map((placed) {
              final t = placed.tile;
              return Positioned(
                left: placed.col * (cellW + gap),
                top: placed.row * (cellH + gap),
                width: placed.columnSpan * cellW + (placed.columnSpan - 1) * gap,
                height: placed.rowSpan * cellH + (placed.rowSpan - 1) * gap,
                child: Material(
                  color: const Color(0xff24282c),
                  shape: const RoundedRectangleBorder(side: BorderSide(color: Color(0xff3b4147))),
                  child: InkWell(
                    onTap: () => send(t.hotkey),
                    child: Padding(
                      padding: const EdgeInsets.all(7),
                      child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                        Icon(iconFor(t.title), size: 30),
                        const SizedBox(height: 8),
                        Text(t.title, textAlign: TextAlign.center, maxLines: 2, overflow: TextOverflow.ellipsis),
                      ]),
                    ),
                  ),
                ),
              );
            }).toList(),
          ),
        ),
      );
    });
  }

  List<PlacedTile> packTiles(List<RemoteTile> tiles, int rows, int cols) {
    final used = List.generate(rows, (_) => List<bool>.filled(cols, false));
    final result = <PlacedTile>[];
    for (final tile in tiles) {
      final rs = tile.rowSpan.clamp(1, rows).toInt();
      final cs = tile.columnSpan.clamp(1, cols).toInt();
      var placed = false;
      for (var r = 0; r < rows && !placed; r++) {
        for (var c = 0; c < cols && !placed; c++) {
          if (r + rs > rows || c + cs > cols) continue;
          var ok = true;
          for (var y = 0; y < rs && ok; y++) {
            for (var x = 0; x < cs; x++) {
              if (used[r + y][c + x]) { ok = false; break; }
            }
          }
          if (!ok) continue;
          for (var y = 0; y < rs; y++) {
            for (var x = 0; x < cs; x++) { used[r + y][c + x] = true; }
          }
          result.add(PlacedTile(tile, r, c, rs, cs));
          placed = true;
        }
      }
    }
    return result;
  }

  IconData iconFor(String title) {
    final q = title.toLowerCase();
    if (q.contains('сохран')) return Icons.save_outlined;
    if (q.contains('скрин')) return Icons.crop_free;
    if (q.contains('брауз')) return Icons.public;
    if (q.contains('пап')) return Icons.folder_outlined;
    if (q.contains('восп')) return Icons.play_arrow;
    if (q.contains('звук')) return Icons.volume_off;
    if (q.contains('назад')) return Icons.arrow_back;
    return Icons.apps;
  }

  Widget touchpad() => Padding(
        padding: const EdgeInsets.all(16),
        child: Column(children: [
          Expanded(child: Container(decoration: BoxDecoration(color: const Color(0xff202326), border: Border.all(color: const Color(0xff3b4147))), child: const Center(child: Text('Touchpad\nследующий этап', textAlign: TextAlign.center, style: TextStyle(color: Colors.grey))))),
          const SizedBox(height: 10),
          Row(children: [Expanded(child: OutlinedButton(onPressed: () => send('ENTER'), child: const Text('Left'))), const SizedBox(width: 8), Expanded(child: OutlinedButton(onPressed: () => send('ESC'), child: const Text('Right')))]),
        ]),
      );

  Widget keyboard() => ListView(padding: const EdgeInsets.all(16), children: [
        const Text('Keyboard', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w600)),
        const SizedBox(height: 14),
        Wrap(spacing: 8, runSpacing: 8, children: [key('Ctrl+C', 'CTRL+C'), key('Ctrl+V', 'CTRL+V'), key('Ctrl+Z', 'CTRL+Z'), key('Ctrl+S', 'CTRL+S'), key('Alt+Tab', 'ALT+TAB'), key('Win+D', 'WIN+D'), key('Enter', 'ENTER'), key('Esc', 'ESC'), key('←', 'LEFT'), key('↑', 'UP'), key('↓', 'DOWN'), key('→', 'RIGHT')]),
      ]);

  Widget key(String title, String hotkey) => SizedBox(width: 105, height: 62, child: OutlinedButton(onPressed: () => send(hotkey), child: Text(title, textAlign: TextAlign.center)));

  Widget media() => Center(child: Wrap(spacing: 12, runSpacing: 12, children: [
        IconButton.filledTonal(onPressed: () => send('VOLUME_DOWN'), icon: const Icon(Icons.volume_down), iconSize: 34),
        IconButton.filled(onPressed: () => send('MEDIA_PLAY'), icon: const Icon(Icons.play_arrow), iconSize: 38),
        IconButton.filledTonal(onPressed: () => send('VOLUME_UP'), icon: const Icon(Icons.volume_up), iconSize: 34),
        IconButton.filledTonal(onPressed: () => send('VOLUME_MUTE'), icon: const Icon(Icons.volume_off), iconSize: 34),
      ]));
}

class RemoteProfile {
  final String name;
  final int rows;
  final int columns;
  final List<RemoteTile> tiles;
  RemoteProfile(this.name, this.rows, this.columns, this.tiles);
  factory RemoteProfile.fromJson(Map<String, dynamic> json) => RemoteProfile(
        json['name'] ?? json['Name'] ?? 'Profile',
        (json['rows'] ?? json['Rows'] ?? 3) as int,
        (json['columns'] ?? json['Columns'] ?? 4) as int,
        ((json['tiles'] ?? json['Tiles'] ?? []) as List).map((e) => RemoteTile.fromJson(Map<String, dynamic>.from(e))).toList(),
      );
}

class RemoteTile {
  final String title;
  final String hotkey;
  final int rowSpan;
  final int columnSpan;
  RemoteTile(this.title, this.hotkey, this.rowSpan, this.columnSpan);
  factory RemoteTile.fromJson(Map<String, dynamic> json) => RemoteTile(
        json['title'] ?? json['Title'] ?? 'Кнопка',
        json['hotkey'] ?? json['Hotkey'] ?? '',
        (json['rowSpan'] ?? json['RowSpan'] ?? 1) as int,
        (json['columnSpan'] ?? json['ColumnSpan'] ?? 1) as int,
      );
}

class PlacedTile {
  final RemoteTile tile;
  final int row;
  final int col;
  final int rowSpan;
  final int columnSpan;
  PlacedTile(this.tile, this.row, this.col, this.rowSpan, this.columnSpan);
}
