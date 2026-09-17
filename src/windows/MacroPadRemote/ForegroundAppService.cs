using System.Diagnostics;
using System.Runtime.InteropServices;

namespace MacroPadRemote;

internal static class ForegroundAppService
{
    [DllImport("user32.dll")]
    private static extern IntPtr GetForegroundWindow();

    [DllImport("user32.dll")]
    private static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);

    internal static string GetExecutableName()
    {
        try
        {
            var hwnd = GetForegroundWindow();
            if (hwnd == IntPtr.Zero) return string.Empty;
            _ = GetWindowThreadProcessId(hwnd, out var pid);
            if (pid == 0) return string.Empty;
            using var process = Process.GetProcessById((int)pid);
            try
            {
                var path = process.MainModule?.FileName;
                if (!string.IsNullOrWhiteSpace(path)) return Path.GetFileName(path);
            }
            catch { }
            return process.ProcessName + ".exe";
        }
        catch
        {
            return string.Empty;
        }
    }
}
