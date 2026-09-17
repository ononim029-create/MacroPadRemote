from pathlib import Path
import re

root = Path('.')
mobile = root / 'src/mobile/macropad_mobile/lib/main.dart'
xaml = root / 'src/windows/MacroPadRemote/MainWindow.xaml'
cs = root / 'src/windows/MacroPadRemote/MainWindow.xaml.cs'
proj = root / 'src/windows/MacroPadRemote/MacroPadRemote.csproj'
pubspec = root / 'src/mobile/macropad_mobile/pubspec.yaml'
workflow = root / '.github/workflows/release.yml'


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'Missing pattern: {label}')
    return text.replace(old, new, 1)

# ---------------- Mobile / tablet ----------------
s = mobile.read_text(encoding='utf-8')

s = replace_once(s, "const mpGreen = Color(0xff62d16f);\n\nvoid main() => runApp(const MacroPadApp());", "const mpGreen = Color(0xff62d16f);\nconst _deviceChannel = MethodChannel('nexo/device');\n\nvoid main() {\n  WidgetsFlutterBinding.ensureInitialized();\n  runApp(const MacroPadApp());\n}", 'mobile channel')

s = replace_once(s, "      home: const ConnectPage(),", "      home: const NexoBootstrap(),", 'bootstrap home')

bootstrap = r'''

class NexoBootstrap extends StatefulWidget {
  const NexoBootstrap({super.key});
  @override
  State<NexoBootstrap> createState() => _NexoBootstrapState();
}

class _NexoBootstrapState extends State<NexoBootstrap> with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _fade;
  late final Animation<double> _scale;
  bool ready = false;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(vsync: this, duration: const Duration(milliseconds: 720));
    _fade = CurvedAnimation(parent: _controller, curve: Curves.easeOutCubic);
    _scale = Tween<double>(begin: .88, end: 1).animate(CurvedAnimation(parent: _controller, curve: Curves.easeOutBack));
    _controller.forward();
    Future<void>.delayed(const Duration(milliseconds: 780), () {
      if (mounted) setState(() => ready = true);
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (ready) return const ConnectPage();
    return Scaffold(
      body: Center(
        child: FadeTransition(
          opacity: _fade,
          child: ScaleTransition(
            scale: _scale,
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              const MacroPadMark(size: 72),
              const SizedBox(height: 18),
              const Text('NEXO', style: TextStyle(fontSize: 27, fontWeight: FontWeight.w700, letterSpacing: 3)),
              const SizedBox(height: 22),
              SizedBox(width: 110, child: LinearProgressIndicator(minHeight: 2, backgroundColor: mpPanel2, valueColor: const AlwaysStoppedAnimation(mpBlue))),
            ]),
          ),
        ),
      ),
    );
  }
}
'''
s = replace_once(s, "\nclass DiscoveredPc {", bootstrap + "\nclass DiscoveredPc {", 'bootstrap class')

s = replace_once(s, "  bool bottomNavVisible = false;\n  Orientation? _lastOrientation;", "  bool bottomNavVisible = false;\n  bool tabletKeyboardVisible = true;\n  bool externalKeyboardConnected = false;\n  double tabletKeyboardHeight = 250;\n  final Set<String> _keyboardModifiers = <String>{};\n  Timer? _hardwareKeyboardTimer;\n  Orientation? _lastOrientation;", 'tablet fields')

s = replace_once(s, "    _connect();\n  }", "    if (widget.formFactor == ClientFormFactor.tablet) {\n      _deviceChannel.setMethodCallHandler((call) async {\n        if (call.method == 'hardwareKeyboardChanged') {\n          final connected = call.arguments == true;\n          if (mounted && connected != externalKeyboardConnected) {\n            setState(() { externalKeyboardConnected = connected; if (connected) tabletKeyboardVisible = false; });\n          }\n        }\n      });\n      _refreshHardwareKeyboard();\n      _hardwareKeyboardTimer = Timer.periodic(const Duration(seconds: 2), (_) => _refreshHardwareKeyboard());\n    }\n    _connect();\n  }", 'tablet init')

helpers = r'''

  Future<void> _refreshHardwareKeyboard() async {
    if (widget.formFactor != ClientFormFactor.tablet) return;
    try {
      final connected = await _deviceChannel.invokeMethod<bool>('hasHardwareKeyboard') ?? false;
      if (!mounted || connected == externalKeyboardConnected) return;
      setState(() {
        externalKeyboardConnected = connected;
        if (connected) tabletKeyboardVisible = false;
      });
    } catch (_) {
      final connected = HardwareKeyboard.instance.physicalKeysPressed.isNotEmpty;
      if (mounted && connected != externalKeyboardConnected) {
        setState(() {
          externalKeyboardConnected = connected;
          if (connected) tabletKeyboardVisible = false;
        });
      }
    }
  }

  Future<void> _virtualKey(String key, {bool modifier = false}) async {
    if (modifier) {
      setState(() {
        if (_keyboardModifiers.contains(key)) { _keyboardModifiers.remove(key); } else { _keyboardModifiers.add(key); }
      });
      await HapticFeedback.selectionClick();
      return;
    }
    final mods = <String>[];
    for (final candidate in const ['CTRL', 'ALT', 'SHIFT']) {
      if (_keyboardModifiers.contains(candidate)) mods.add(candidate);
    }
    final hotkey = [...mods, key].join('+');
    await HapticFeedback.lightImpact();
    await _sendHotkey(hotkey);
  }
'''
s = replace_once(s, "\n  Future<void> _connect() async {", helpers + "\n  Future<void> _connect() async {", 'tablet helpers')

s = replace_once(s, "    subscription?.cancel();\n    _deckReturnController.dispose();", "    subscription?.cancel();\n    _hardwareKeyboardTimer?.cancel();\n    if (widget.formFactor == ClientFormFactor.tablet) _deviceChannel.setMethodCallHandler(null);\n    _deckReturnController.dispose();", 'tablet dispose')

old_workspace = r'''  Widget _workspaceBody(List<Widget> pages, bool compact) {
    if (!compact) return pages[tab];
    return Stack(children: [
      Positioned.fill(child: pages[tab]),'''
new_workspace = r'''  Widget _workspaceBody(List<Widget> pages, bool compact) {
    if (widget.formFactor == ClientFormFactor.tablet) return _tabletWorkspace(pages);
    if (!compact) return pages[tab];
    return Stack(children: [
      Positioned.fill(child: pages[tab]),'''
s = replace_once(s, old_workspace, new_workspace, 'tablet workspace route')

tablet_workspace = r'''

  Widget _tabletWorkspace(List<Widget> pages) {
    final showKeyboardCapability = !externalKeyboardConnected && tab == 0;
    return Column(children: [
      Expanded(child: pages[tab]),
      if (showKeyboardCapability && tabletKeyboardVisible)
        SizedBox(
          height: tabletKeyboardHeight,
          child: Column(children: [
            GestureDetector(
              behavior: HitTestBehavior.opaque,
              onVerticalDragUpdate: (details) => setState(() => tabletKeyboardHeight = (tabletKeyboardHeight - details.delta.dy).clamp(150.0, 430.0)),
              child: Container(
                height: 18,
                color: const Color(0xaa24272a),
                alignment: Alignment.center,
                child: const Icon(Icons.drag_handle, size: 17, color: Color(0xffb8bdc2)),
              ),
            ),
            Expanded(child: _TabletRemoteKeyboard(onKey: _virtualKey, activeModifiers: _keyboardModifiers)),
          ]),
        ),
      if (showKeyboardCapability)
        Center(
          child: Material(
            color: const Color(0x9924272a),
            borderRadius: BorderRadius.circular(12),
            child: InkWell(
              borderRadius: BorderRadius.circular(12),
              onTap: () => setState(() => tabletKeyboardVisible = !tabletKeyboardVisible),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 30, vertical: 2),
                child: Icon(tabletKeyboardVisible ? Icons.keyboard_arrow_down : Icons.keyboard_arrow_up, size: 20, color: const Color(0xffc5c9cc)),
              ),
            ),
          ),
        ),
    ]);
  }
'''
s = replace_once(s, "\n  Widget _drawer({required bool compact}) {", tablet_workspace + "\n  Widget _drawer({required bool compact}) {", 'tablet workspace')

keyboard_widget = r'''

class _TabletRemoteKeyboard extends StatelessWidget {
  final Future<void> Function(String key, {bool modifier}) onKey;
  final Set<String> activeModifiers;
  const _TabletRemoteKeyboard({required this.onKey, required this.activeModifiers});

  static const _rows = <List<String>>[
    ['ESC','1','2','3','4','5','6','7','8','9','0','BACKSPACE'],
    ['TAB','Q','W','E','R','T','Y','U','I','O','P','ENTER'],
    ['SHIFT','A','S','D','F','G','H','J','K','L','UP','DELETE'],
    ['CTRL','ALT','Z','X','C','V','B','N','M','LEFT','DOWN','RIGHT'],
  ];

  @override
  Widget build(BuildContext context) => Container(
        color: const Color(0xff111315),
        padding: const EdgeInsets.fromLTRB(8, 5, 8, 6),
        child: Column(children: [
          for (final row in _rows)
            Expanded(child: Row(children: [for (final key in row) Expanded(flex: _flex(key), child: _key(key))])),
          Expanded(child: Row(children: [
            Expanded(flex: 2, child: _key('CTRL')),
            Expanded(flex: 2, child: _key('ALT')),
            Expanded(flex: 8, child: _key('SPACE', label: 'ПРОБЕЛ')),
            Expanded(flex: 2, child: _key('SHIFT')),
          ])),
        ]),
      );

  int _flex(String key) => switch (key) { 'BACKSPACE' || 'ENTER' || 'SHIFT' || 'CTRL' || 'ALT' || 'TAB' => 2, _ => 1 };

  Widget _key(String key, {String? label}) {
    final modifier = key == 'CTRL' || key == 'ALT' || key == 'SHIFT';
    final active = activeModifiers.contains(key);
    return Padding(
      padding: const EdgeInsets.all(2.5),
      child: Material(
        color: active ? const Color(0xff264e73) : mpPanel2,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6), side: BorderSide(color: active ? mpBlue : mpBorder)),
        child: InkWell(
          borderRadius: BorderRadius.circular(6),
          onTap: () => onKey(key, modifier: modifier),
          child: Center(child: Text(label ?? _label(key), maxLines: 1, overflow: TextOverflow.fade, style: TextStyle(fontSize: _fontSize(key), color: Colors.white, fontWeight: active ? FontWeight.w700 : FontWeight.w500))),
        ),
      ),
    );
  }

  double _fontSize(String key) => key.length > 5 ? 9.0 : 12.0;
  String _label(String key) => switch (key) { 'BACKSPACE' => '⌫', 'ENTER' => '↵', 'SHIFT' => '⇧', 'CTRL' => 'Ctrl', 'ALT' => 'Alt', 'TAB' => 'Tab', 'DELETE' => 'Del', 'LEFT' => '←', 'RIGHT' => '→', 'UP' => '↑', 'DOWN' => '↓', 'ESC' => 'Esc', _ => key };
}
'''
s = replace_once(s, "\nclass _SharpNavItem {", keyboard_widget + "\nclass _SharpNavItem {", 'tablet keyboard widget')

mobile.write_text(s, encoding='utf-8')

# pubspec version
p = pubspec.read_text(encoding='utf-8')
p = re.sub(r'^version:\s*[^\n]+', 'version: 1.1.0+42', p, flags=re.M)
pubspec.write_text(p, encoding='utf-8')

# ---------------- Windows loading / branding ----------------
x = xaml.read_text(encoding='utf-8')
x = x.replace('  v1.0 preview', '  v1.1 preview')
old_mark = '<TextBlock Text="▦" FontSize="23" FontWeight="Bold" Margin="0,0,10,0"/>'
new_mark = '''<Grid Width="24" Height="24" Margin="0,0,10,0">
                        <Grid.RowDefinitions><RowDefinition/><RowDefinition/></Grid.RowDefinitions>
                        <Grid.ColumnDefinitions><ColumnDefinition/><ColumnDefinition/></Grid.ColumnDefinitions>
                        <Rectangle Fill="#1688FF" Margin="0,0,2,2"/>
                        <Rectangle Grid.Column="1" Fill="#F2F2F2" Margin="2,0,0,2"/>
                        <Rectangle Grid.Row="1" Fill="#F2F2F2" Margin="0,2,2,0"/>
                        <Rectangle Grid.Row="1" Grid.Column="1" Fill="#24272A" Stroke="#F2F2F2" StrokeThickness="1" Margin="2,2,0,0"/>
                    </Grid>'''
x = replace_once(x, old_mark, new_mark, 'windows header mark')

end_marker = '    </Grid>\n</Window>'
overlay = '''        <Border x:Name="StartupOverlay" Grid.RowSpan="3" Grid.ColumnSpan="3" Panel.ZIndex="999" Background="#17191B" Opacity="1">
            <Grid>
                <StackPanel HorizontalAlignment="Center" VerticalAlignment="Center">
                    <Grid Width="76" Height="76" HorizontalAlignment="Center" RenderTransformOrigin="0.5,0.5">
                        <Grid.RenderTransform><ScaleTransform x:Name="StartupMarkScale" ScaleX="0.86" ScaleY="0.86"/></Grid.RenderTransform>
                        <Grid.RowDefinitions><RowDefinition/><RowDefinition/></Grid.RowDefinitions>
                        <Grid.ColumnDefinitions><ColumnDefinition/><ColumnDefinition/></Grid.ColumnDefinitions>
                        <Rectangle Fill="#1688FF" Margin="0,0,5,5"/>
                        <Rectangle Grid.Column="1" Fill="#F2F2F2" Margin="5,0,0,5"/>
                        <Rectangle Grid.Row="1" Fill="#F2F2F2" Margin="0,5,5,0"/>
                        <Rectangle Grid.Row="1" Grid.Column="1" Fill="#24272A" Stroke="#F2F2F2" StrokeThickness="2" Margin="5,5,0,0"/>
                    </Grid>
                    <TextBlock Text="NEXO" HorizontalAlignment="Center" Margin="0,18,0,0" FontSize="25" FontWeight="Bold" CharacterSpacing="220"/>
                    <ProgressBar Width="120" Height="2" IsIndeterminate="True" Margin="0,22,0,0" Foreground="#1688FF" Background="#24272A"/>
                </StackPanel>
            </Grid>
        </Border>
'''
x = replace_once(x, end_marker, overlay + end_marker, 'startup overlay')
xaml.write_text(x, encoding='utf-8')

c = cs.read_text(encoding='utf-8')
c = replace_once(c, 'using System.Windows.Media;\n', 'using System.Windows.Media;\nusing System.Windows.Media.Animation;\n', 'animation using')
old_loaded = '''    private async void MainWindow_Loaded(object sender, RoutedEventArgs e)
    {
        UpdateZoom();
        try
        {
            await StartSelectedTransportAsync();
        }
        catch (Exception ex)
        {
            DeviceStatus.Text = $"Ошибка связи: {ex.Message}";
        }
    }'''
new_loaded = '''    private async void MainWindow_Loaded(object sender, RoutedEventArgs e)
    {
        BeginStartupAnimation();
        UpdateZoom();
        try
        {
            await StartSelectedTransportAsync();
        }
        catch (Exception ex)
        {
            DeviceStatus.Text = $"Ошибка связи: {ex.Message}";
        }
        await Task.Delay(420);
        HideStartupOverlay();
    }

    private void BeginStartupAnimation()
    {
        var scale = new DoubleAnimation(.86, 1.0, TimeSpan.FromMilliseconds(620)) { EasingFunction = new BackEase { EasingMode = EasingMode.EaseOut, Amplitude = .18 } };
        StartupMarkScale.BeginAnimation(ScaleTransform.ScaleXProperty, scale);
        StartupMarkScale.BeginAnimation(ScaleTransform.ScaleYProperty, scale);
    }

    private void HideStartupOverlay()
    {
        var fade = new DoubleAnimation(1, 0, TimeSpan.FromMilliseconds(260)) { EasingFunction = new CubicEase { EasingMode = EasingMode.EaseOut } };
        fade.Completed += (_, _) => StartupOverlay.Visibility = Visibility.Collapsed;
        StartupOverlay.BeginAnimation(OpacityProperty, fade);
    }'''
c = replace_once(c, old_loaded, new_loaded, 'windows splash code')
cs.write_text(c, encoding='utf-8')

# Project version
pr = proj.read_text(encoding='utf-8')
pr = pr.replace('<Version>1.0.0</Version>', '<Version>1.1.0</Version>').replace('<InformationalVersion>1.0.0-preview</InformationalVersion>', '<InformationalVersion>1.1.0-preview</InformationalVersion>')
proj.write_text(pr, encoding='utf-8')

# ---------------- Build workflow / Android native keyboard detector / installer ----------------
w = workflow.read_text(encoding='utf-8')
w = replace_once(w, "          dotnet publish src/windows/MacroPadRemote/MacroPadRemote.csproj -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -o dist/windows\n          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }\n          Compress-Archive -Path dist/windows/* -DestinationPath dist/NEXO-win-x64.zip -Force", "          dotnet publish src/windows/MacroPadRemote/MacroPadRemote.csproj -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -o dist/windows\n          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }\n          Copy-Item dist/windows/NEXO.exe dist/NEXO.exe -Force\n          Compress-Archive -Path dist/windows/* -DestinationPath dist/NEXO-win-x64.zip -Force\n          @'\n          @echo off\n          setlocal EnableExtensions\n          title NEXO Setup\n          echo.\n          echo ==============================\n          echo        NEXO Setup v1.1\n          echo ==============================\n          echo.\n          set \"DEFAULT_DIR=%LOCALAPPDATA%\\NEXO\"\n          set /p \"INSTALL_DIR=Install folder [%%DEFAULT_DIR%%]: \"\n          if not defined INSTALL_DIR set \"INSTALL_DIR=%DEFAULT_DIR%\"\n          echo.\n          echo Downloading NEXO...\n          powershell -NoProfile -ExecutionPolicy Bypass -Command \"$ErrorActionPreference='Stop'; $u='https://github.com/${{ github.repository }}/releases/download/preview/NEXO-win-x64.zip'; $z=Join-Path $env:TEMP 'NEXO-win-x64.zip'; Invoke-WebRequest -UseBasicParsing $u -OutFile $z; if(Test-Path '%INSTALL_DIR%'){Remove-Item '%INSTALL_DIR%' -Recurse -Force}; New-Item -ItemType Directory -Force '%INSTALL_DIR%' | Out-Null; Expand-Archive $z '%INSTALL_DIR%' -Force; Remove-Item $z -Force\"\n          if errorlevel 1 goto :fail\n          set /p \"SHORTCUT=Create desktop shortcut? [Y/n]: \"\n          if /I not \"%SHORTCUT%\"==\"n\" powershell -NoProfile -ExecutionPolicy Bypass -Command \"$ws=New-Object -ComObject WScript.Shell; $s=$ws.CreateShortcut([Environment]::GetFolderPath('Desktop')+'\\NEXO.lnk'); $s.TargetPath='%INSTALL_DIR%\\NEXO.exe'; $s.WorkingDirectory='%INSTALL_DIR%'; $s.Description='NEXO'; $s.Save()\"\n          echo.\n          echo NEXO installed to: %INSTALL_DIR%\n          set /p \"RUN=Launch NEXO now? [Y/n]: \"\n          if /I not \"%RUN%\"==\"n\" start \"\" \"%INSTALL_DIR%\\NEXO.exe\"\n          exit /b 0\n          :fail\n          echo Installation failed. Check internet connection and permissions.\n          pause\n          exit /b 1\n          '@ | Set-Content -Path dist/NEXO-Setup.bat -Encoding ASCII", 'windows release outputs')

w = replace_once(w, "            dist/NEXO-win-x64.zip\n            dist/windows/**", "            dist/NEXO-win-x64.zip\n            dist/NEXO.exe\n            dist/NEXO-Setup.bat\n            dist/windows/**", 'artifact outputs')

native_patch = r'''

          main_activity = Path('build-mobile/android/app/src/main/kotlin/com/example/nexo/MainActivity.kt')
          main_activity.parent.mkdir(parents=True, exist_ok=True)
          main_activity.write_text(r'''package com.example.nexo

import android.content.Context
import android.hardware.input.InputManager
import android.view.InputDevice
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity(), InputManager.InputDeviceListener {
    private val channelName = "nexo/device"
    private lateinit var inputManager: InputManager
    private var channel: MethodChannel? = null

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        inputManager = getSystemService(Context.INPUT_SERVICE) as InputManager
        inputManager.registerInputDeviceListener(this, null)
        channel = MethodChannel(flutterEngine.dartExecutor.binaryMessenger, channelName)
        channel?.setMethodCallHandler { call, result ->
            if (call.method == "hasHardwareKeyboard") result.success(hasHardwareKeyboard()) else result.notImplemented()
        }
    }

    private fun hasHardwareKeyboard(): Boolean = InputDevice.getDeviceIds().any { id ->
        val device = InputDevice.getDevice(id) ?: return@any false
        !device.isVirtual &&
            device.keyboardType == InputDevice.KEYBOARD_TYPE_ALPHABETIC &&
            (device.sources and InputDevice.SOURCE_KEYBOARD) == InputDevice.SOURCE_KEYBOARD
    }

    private fun publishKeyboardState() { channel?.invokeMethod("hardwareKeyboardChanged", hasHardwareKeyboard()) }
    override fun onInputDeviceAdded(deviceId: Int) = publishKeyboardState()
    override fun onInputDeviceRemoved(deviceId: Int) = publishKeyboardState()
    override fun onInputDeviceChanged(deviceId: Int) = publishKeyboardState()
    override fun onDestroy() {
        if (::inputManager.isInitialized) inputManager.unregisterInputDeviceListener(this)
        super.onDestroy()
    }
}
''')
'''
w = replace_once(w, "          drawable = Path('build-mobile/android/app/src/main/res/drawable')", native_patch + "\n          drawable = Path('build-mobile/android/app/src/main/res/drawable')", 'android keyboard native')

# Replace Android icon with same NEXO 2x2 mark geometry used by desktop header.
# Existing vector already follows the same geometry/colors, so keep source and add adaptive-style background consistency.

w = w.replace('{"version":"1.0.0-preview"', '{"version":"1.1.0-preview"')
w = w.replace('NEXO v1.0: centered landscape fit, forced profile switching, haptics and long press, collapsible landscape navigation, independent scale/pan locks, tile reorder, reorganized properties and device settings', 'NEXO v1.1: tablet mode with scalable remote keyboard and physical-keyboard detection, unified startup animation/icon, stability pass, standalone EXE and BAT installer')
w = replace_once(w, "            artifacts/windows/NEXO-win-x64.zip \\\n            artifacts/android/NEXO-android.apk \\", "            artifacts/windows/NEXO-win-x64.zip \\\n            artifacts/windows/NEXO.exe \\\n            artifacts/windows/NEXO-Setup.bat \\\n            artifacts/android/NEXO-android.apk \\", 'preview uploads')
workflow.write_text(w, encoding='utf-8')

print('NEXO v1.1 patch applied')
