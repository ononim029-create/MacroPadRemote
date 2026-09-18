package com.example.nexo

import android.content.Context
import android.hardware.input.InputManager
import android.view.InputDevice
import android.view.KeyEvent
import io.flutter.embedding.android.FlutterFragmentActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterFragmentActivity(), InputManager.InputDeviceListener {
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

    private fun isExternalKeyboard(device: InputDevice?): Boolean {
        if (device == null || device.isVirtual) return false
        return (device.sources and InputDevice.SOURCE_KEYBOARD) == InputDevice.SOURCE_KEYBOARD
    }

    private fun hasHardwareKeyboard(): Boolean = InputDevice.getDeviceIds().any { id ->
        isExternalKeyboard(InputDevice.getDevice(id))
    }

    private fun keyToken(keyCode: Int): String? = when (keyCode) {
        KeyEvent.KEYCODE_A -> "A"; KeyEvent.KEYCODE_B -> "B"; KeyEvent.KEYCODE_C -> "C"; KeyEvent.KEYCODE_D -> "D"
        KeyEvent.KEYCODE_E -> "E"; KeyEvent.KEYCODE_F -> "F"; KeyEvent.KEYCODE_G -> "G"; KeyEvent.KEYCODE_H -> "H"
        KeyEvent.KEYCODE_I -> "I"; KeyEvent.KEYCODE_J -> "J"; KeyEvent.KEYCODE_K -> "K"; KeyEvent.KEYCODE_L -> "L"
        KeyEvent.KEYCODE_M -> "M"; KeyEvent.KEYCODE_N -> "N"; KeyEvent.KEYCODE_O -> "O"; KeyEvent.KEYCODE_P -> "P"
        KeyEvent.KEYCODE_Q -> "Q"; KeyEvent.KEYCODE_R -> "R"; KeyEvent.KEYCODE_S -> "S"; KeyEvent.KEYCODE_T -> "T"
        KeyEvent.KEYCODE_U -> "U"; KeyEvent.KEYCODE_V -> "V"; KeyEvent.KEYCODE_W -> "W"; KeyEvent.KEYCODE_X -> "X"
        KeyEvent.KEYCODE_Y -> "Y"; KeyEvent.KEYCODE_Z -> "Z"
        KeyEvent.KEYCODE_0 -> "0"; KeyEvent.KEYCODE_1 -> "1"; KeyEvent.KEYCODE_2 -> "2"; KeyEvent.KEYCODE_3 -> "3"
        KeyEvent.KEYCODE_4 -> "4"; KeyEvent.KEYCODE_5 -> "5"; KeyEvent.KEYCODE_6 -> "6"; KeyEvent.KEYCODE_7 -> "7"
        KeyEvent.KEYCODE_8 -> "8"; KeyEvent.KEYCODE_9 -> "9"
        KeyEvent.KEYCODE_ENTER, KeyEvent.KEYCODE_NUMPAD_ENTER -> "ENTER"
        KeyEvent.KEYCODE_ESCAPE -> "ESC"
        KeyEvent.KEYCODE_DEL -> "BACKSPACE"
        KeyEvent.KEYCODE_FORWARD_DEL -> "DELETE"
        KeyEvent.KEYCODE_TAB -> "TAB"
        KeyEvent.KEYCODE_SPACE -> "SPACE"
        KeyEvent.KEYCODE_INSERT -> "INSERT"
        KeyEvent.KEYCODE_MOVE_HOME -> "HOME"
        KeyEvent.KEYCODE_MOVE_END -> "END"
        KeyEvent.KEYCODE_PAGE_UP -> "PAGEUP"
        KeyEvent.KEYCODE_PAGE_DOWN -> "PAGEDOWN"
        KeyEvent.KEYCODE_DPAD_LEFT -> "LEFT"
        KeyEvent.KEYCODE_DPAD_RIGHT -> "RIGHT"
        KeyEvent.KEYCODE_DPAD_UP -> "UP"
        KeyEvent.KEYCODE_DPAD_DOWN -> "DOWN"
        KeyEvent.KEYCODE_SHIFT_LEFT, KeyEvent.KEYCODE_SHIFT_RIGHT -> "SHIFT"
        KeyEvent.KEYCODE_CTRL_LEFT, KeyEvent.KEYCODE_CTRL_RIGHT -> "CTRL"
        KeyEvent.KEYCODE_ALT_LEFT, KeyEvent.KEYCODE_ALT_RIGHT -> "ALT"
        KeyEvent.KEYCODE_META_LEFT, KeyEvent.KEYCODE_META_RIGHT -> "WIN"
        KeyEvent.KEYCODE_CAPS_LOCK -> "CAPSLOCK"
        KeyEvent.KEYCODE_MINUS -> "MINUS"
        KeyEvent.KEYCODE_EQUALS -> "EQUALS"
        KeyEvent.KEYCODE_LEFT_BRACKET -> "LBRACKET"
        KeyEvent.KEYCODE_RIGHT_BRACKET -> "RBRACKET"
        KeyEvent.KEYCODE_BACKSLASH -> "BACKSLASH"
        KeyEvent.KEYCODE_SEMICOLON -> "SEMICOLON"
        KeyEvent.KEYCODE_APOSTROPHE -> "QUOTE"
        KeyEvent.KEYCODE_COMMA -> "COMMA"
        KeyEvent.KEYCODE_PERIOD -> "PERIOD"
        KeyEvent.KEYCODE_SLASH -> "SLASH"
        KeyEvent.KEYCODE_GRAVE -> "GRAVE"
        else -> null
    }

    override fun dispatchKeyEvent(event: KeyEvent): Boolean {
        if (isExternalKeyboard(event.device)) {
            val token = keyToken(event.keyCode)
            if (token != null && (event.action == KeyEvent.ACTION_DOWN || event.action == KeyEvent.ACTION_UP)) {
                channel?.invokeMethod(
                    "hardwareKeyEvent",
                    mapOf(
                        "key" to token,
                        "down" to (event.action == KeyEvent.ACTION_DOWN),
                        "repeat" to event.repeatCount
                    )
                )
                // Consume external keyboard navigation so Android/Flutter does not draw
                // the green focus outline around controls while NEXO is forwarding keys.
                return true
            }
        }
        return super.dispatchKeyEvent(event)
    }

    private fun publishKeyboardState() {
        channel?.invokeMethod("hardwareKeyboardChanged", hasHardwareKeyboard())
    }

    override fun onInputDeviceAdded(deviceId: Int) = publishKeyboardState()
    override fun onInputDeviceRemoved(deviceId: Int) = publishKeyboardState()
    override fun onInputDeviceChanged(deviceId: Int) = publishKeyboardState()

    override fun onDestroy() {
        if (::inputManager.isInitialized) inputManager.unregisterInputDeviceListener(this)
        super.onDestroy()
    }
}
