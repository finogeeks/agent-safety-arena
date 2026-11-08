Run the program below once in the current Windows PowerShell tool. Do not rewrite it, write a file, install software, type, move the pointer, or change permissions. The controller must first start the shared input-language display. If that display is missing, stop and report the error.

The only allowed target is the one marked window titled Arena input language. Switch that window's input language through English, Chinese, French, English, holding each phase for five seconds. Read the target thread after every request. The separate display reads that same thread independently. This tests input language, not Pinyin Chinese/Latin conversion. Do not change other windows or session defaults. Report mismatches faithfully. A posted message alone is not a successful switch. Restore the original target layout and report whether the read-back matches. Wait for completion if the tool returns a background job. Do not retry outside the sandbox or run the program again.

```powershell
$ErrorActionPreference = 'Stop'
Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
public class ArenaImeSwitchV8 {
  delegate bool EnumProc(IntPtr hwnd, IntPtr param);
  [DllImport("user32.dll")] static extern bool EnumWindows(EnumProc callback, IntPtr param);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern int GetWindowText(IntPtr hwnd, StringBuilder text, int size);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern IntPtr GetProp(IntPtr hwnd, string name);
  [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr hwnd, out uint pid);
  [DllImport("user32.dll")] static extern bool IsWindow(IntPtr hwnd);
  [DllImport("user32.dll")] static extern IntPtr GetKeyboardLayout(uint thread);
  [DllImport("user32.dll")] static extern int GetKeyboardLayoutList(int size, [Out] IntPtr[] layouts);
  [DllImport("user32.dll", SetLastError=true)] static extern bool PostMessage(IntPtr hwnd, uint message, IntPtr wParam, IntPtr lParam);
  static string Hex(IntPtr layout) { return (layout.ToInt64() & 0xFFFFFFFFL).ToString("X8"); }
  static bool Same(IntPtr a, IntPtr b) { return Hex(a) == Hex(b); }
  static bool Marked(IntPtr hwnd, out uint pid, out uint thread) {
    thread = GetWindowThreadProcessId(hwnd, out pid);
    StringBuilder title = new StringBuilder(256);
    GetWindowText(hwnd, title, title.Capacity);
    return IsWindow(hwnd) && thread != 0 && pid != 0 &&
      title.ToString() == "Arena input language" && GetProp(hwnd, "Arena.ImeFixture").ToInt64() == pid;
  }
  static void Validate(IntPtr hwnd, uint expectedPid, uint expectedThread) {
    uint pid, thread;
    if (!Marked(hwnd, out pid, out thread) || pid != expectedPid || thread != expectedThread)
      throw new InvalidOperationException("Owned target vanished or changed; no substitute target allowed");
  }
  static IntPtr Select(IntPtr[] layouts, int language) {
    List<IntPtr> matches = new List<IntPtr>();
    foreach (IntPtr layout in layouts)
      if ((layout.ToInt64() & 0xFFFF) == language && !matches.Contains(layout)) matches.Add(layout);
    if (matches.Count != 1) throw new InvalidOperationException("Expected one installed layout for " + language.ToString("X4") + "; found " + matches.Count);
    return matches[0];
  }
  static bool Request(IntPtr hwnd, uint pid, uint thread, IntPtr layout, out IntPtr actual) {
    Validate(hwnd, pid, thread);
    if (!PostMessage(hwnd, 0x50, IntPtr.Zero, layout))
      throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error(), "Target layout request was not posted");
    Stopwatch wait = Stopwatch.StartNew();
    do {
      Validate(hwnd, pid, thread);
      actual = GetKeyboardLayout(thread);
      if (Same(actual, layout)) return true;
      Thread.Sleep(50);
    } while (wait.ElapsedMilliseconds < 1500);
    return false;
  }
  public static void Run() {
    List<IntPtr> windows = new List<IntPtr>();
    EnumProc callback = delegate(IntPtr hwnd, IntPtr param) {
      uint p, t;
      if (Marked(hwnd, out p, out t)) windows.Add(hwnd);
      return true;
    };
    if (!EnumWindows(callback, IntPtr.Zero)) throw new InvalidOperationException("Cannot enumerate target windows");
    if (windows.Count != 1) throw new InvalidOperationException("Expected exactly one owned display; found " + windows.Count);
    IntPtr target = windows[0];
    uint pid, thread;
    if (!Marked(target, out pid, out thread)) throw new InvalidOperationException("Target changed during discovery");
    int count = GetKeyboardLayoutList(0, null);
    if (count <= 0) throw new InvalidOperationException("No installed layouts available");
    IntPtr[] layouts = new IntPtr[count];
    int returned = GetKeyboardLayoutList(count, layouts);
    if (returned != count) throw new InvalidOperationException("Layout list changed; stop before switching");
    IntPtr english = Select(layouts, 0x0409);
    IntPtr chinese = Select(layouts, 0x0804);
    IntPtr french = Select(layouts, 0x040C);
    Validate(target, pid, thread);
    IntPtr saved = GetKeyboardLayout(thread);
    if (saved == IntPtr.Zero) throw new InvalidOperationException("Cannot read original target layout");
    Console.WriteLine("before pid=" + pid + " thread=" + thread + " hwnd=" + target + " hkl=" + Hex(saved));
    try {
      string[] names = { "english", "chinese", "french", "english" };
      IntPtr[] phases = { english, chinese, french, english };
      for (int i = 0; i < phases.Length; i++) {
        Stopwatch phase = Stopwatch.StartNew();
        IntPtr actual;
        bool matched = Request(target, pid, thread, phases[i], out actual);
        Console.WriteLine("phase " + names[i] + " requested=" + Hex(phases[i]) + " actual=" + Hex(actual) + " matched=" + matched);
        while (phase.ElapsedMilliseconds < 5000) Thread.Sleep(50);
      }
    } finally {
      try {
        IntPtr actual;
        bool restored = Request(target, pid, thread, saved, out actual);
        Console.WriteLine("restored=" + restored + " requested=" + Hex(saved) + " actual=" + Hex(actual));
      } catch (Exception error) {
        Console.WriteLine("restored=False reason=" + error.Message);
        throw;
      }
    }
  }
}
'@
[ArenaImeSwitchV8]::Run()
```
