package com.example.nexo

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
