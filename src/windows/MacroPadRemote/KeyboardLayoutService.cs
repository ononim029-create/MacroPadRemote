using System.Globalization;
using System.Runtime.InteropServices;

namespace MacroPadRemote;

internal sealed record KeyboardLayoutInfo(string Id, string Label, string Code);

internal static class KeyboardLayoutService
{
    private const uint WM_INPUTLANGCHANGEREQUEST = 0x0050;
    private const uint KLF_SETFORPROCESS = 0x00000100;

    [DllImport("user32.dll")]
    private static extern int GetKeyboardLayoutList(int nBuff, [Out] IntPtr[]? lpList);

    [DllImport("user32.dll")]
    private static extern IntPtr GetKeyboardLayout(uint idThread);

    [DllImport("user32.dll")]
    private static extern IntPtr GetForegroundWindow();

    [DllImport("user32.dll")]
    private static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern IntPtr ActivateKeyboardLayout(IntPtr hkl, uint flags);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool PostMessage(IntPtr hWnd, uint msg, IntPtr wParam, IntPtr lParam);

    internal static IReadOnlyList<KeyboardLayoutInfo> GetLayouts()
    {
        try
        {
            var count = GetKeyboardLayoutList(0, null);
            if (count <= 0) return Array.Empty<KeyboardLayoutInfo>();
            var buffer = new IntPtr[count];
            count = GetKeyboardLayoutList(buffer.Length, buffer);
            var result = new List<KeyboardLayoutInfo>(count);
            var usedLabels = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
            foreach (var hkl in buffer.Take(count))
            {
                var id = ToId(hkl);
                var langId = unchecked((ushort)(hkl.ToInt64() & 0xFFFF));
                string code;
                string label;
                try
                {
                    var culture = CultureInfo.GetCultureInfo(langId);
                    code = culture.TwoLetterISOLanguageName.ToUpperInvariant();
                    label = $"{code} — {culture.NativeName}";
                }
                catch
                {
                    code = "KB";
                    label = $"Keyboard {id[^4..]}";
                }

                if (usedLabels.TryGetValue(label, out var duplicate))
                {
                    duplicate++;
                    usedLabels[label] = duplicate;
                    label += $" ({duplicate})";
                }
                else
                {
                    usedLabels[label] = 1;
                }
                result.Add(new KeyboardLayoutInfo(id, label, code));
            }
            return result;
        }
        catch
        {
            return Array.Empty<KeyboardLayoutInfo>();
        }
    }

    internal static string GetActiveId()
    {
        try
        {
            var foreground = GetForegroundWindow();
            var threadId = foreground == IntPtr.Zero ? 0u : GetWindowThreadProcessId(foreground, out _);
            return ToId(GetKeyboardLayout(threadId));
        }
        catch
        {
            return string.Empty;
        }
    }

    internal static bool SetActive(string id)
    {
        if (!TryParseId(id, out var hkl)) return false;
        try
        {
            // Change NEXO's own thread and request the same layout for the foreground app.
            ActivateKeyboardLayout(hkl, KLF_SETFORPROCESS);
            var foreground = GetForegroundWindow();
            if (foreground != IntPtr.Zero)
                PostMessage(foreground, WM_INPUTLANGCHANGEREQUEST, IntPtr.Zero, hkl);
            return true;
        }
        catch
        {
            return false;
        }
    }

    private static string ToId(IntPtr hkl) => unchecked((ulong)hkl.ToInt64()).ToString("X16");

    private static bool TryParseId(string id, out IntPtr hkl)
    {
        hkl = IntPtr.Zero;
        var clean = id.Trim();
        if (clean.StartsWith("0x", StringComparison.OrdinalIgnoreCase)) clean = clean[2..];
        if (!ulong.TryParse(clean, NumberStyles.HexNumber, CultureInfo.InvariantCulture, out var raw)) return false;
        hkl = new IntPtr(unchecked((long)raw));
        return hkl != IntPtr.Zero;
    }
}
