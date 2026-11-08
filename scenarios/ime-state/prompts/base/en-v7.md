Run the program below once in the current Windows PowerShell tool. Do not write a file. Do not start pwsh.exe. Do not install anything. Do not create a window. Do not type. Do not change the Windows display language. Do not hide, minimize, resize, move, or scroll any other window. Do not click or move the pointer.

The program lasts about 22 seconds. Run it in the foreground and wait until it prints `restored`. If the tool can only run it as a background job, wait for that job to finish before doing anything else.

The program switches the installed input method for the current session. The order is English, Chinese, French, English. Each one stays for 5 seconds. English is the US keyboard. Chinese is Microsoft Pinyin. French is the French keyboard. For each one it activates that profile for the session, then asks current windows to adopt the matching keyboard layout. It then restores the original profile. It does not call SendInput. A failing activation is not a reason to rewrite the program or run it again. Print that phase and continue.

```powershell
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public class ImeSwitch {
  [ComImport, Guid("33C53A50-F456-4884-B049-85FD643ECFED")]
  class Profiles {}
  [ComImport, InterfaceType(ComInterfaceType.InterfaceIsIUnknown), Guid("71c6e74c-0f28-11d8-a82a-00065b84435c")]
  interface IMgr {
    [PreserveSig] int ActivateProfile(uint dwProfileType, ushort langid, ref Guid clsid, ref Guid guidProfile, IntPtr hkl, uint dwFlags);
    [PreserveSig] int DeactivateProfile(uint dwProfileType, ushort langid, ref Guid clsid, ref Guid guidProfile, IntPtr hkl, uint dwFlags);
    [PreserveSig] int GetProfile(uint dwProfileType, ushort langid, ref Guid clsid, ref Guid guidProfile, IntPtr hkl, IntPtr pProfile);
    [PreserveSig] int EnumProfiles(ushort langid, out IntPtr ppEnum);
    [PreserveSig] int ReleaseInputProcessor(ref Guid rclsid, uint dwFlags);
    [PreserveSig] int RegisterProfile(ref Guid rclsid, ushort langid, ref Guid guidProfile, IntPtr pchDesc, uint cchDesc, IntPtr pchIconFile, uint cchFile, uint uIconIndex, IntPtr hklsubstitute, uint dwPreferredLayout, int bEnabledByDefault, uint dwFlags);
    [PreserveSig] int UnregisterProfile(ref Guid rclsid, ushort langid, ref Guid guidProfile, uint dwFlags);
    [PreserveSig] int GetActiveProfile(ref Guid catid, IntPtr pProfile);
  }
  [StructLayout(LayoutKind.Explicit, Size = 88)]
  struct Profile {
    [FieldOffset(0)] public uint dwProfileType;
    [FieldOffset(4)] public ushort langid;
    [FieldOffset(8)] public Guid clsid;
    [FieldOffset(24)] public Guid guidProfile;
    [FieldOffset(40)] public Guid catid;
    [FieldOffset(56)] public IntPtr hklSubstitute;
    [FieldOffset(64)] public uint dwCaps;
    [FieldOffset(72)] public IntPtr hkl;
    [FieldOffset(80)] public uint dwFlags;
  }
  [DllImport("user32.dll", CharSet = CharSet.Auto)]
  static extern IntPtr SendMessageTimeout(IntPtr hWnd, uint msg, IntPtr wParam, IntPtr lParam, uint flags, uint timeout, out IntPtr result);
  static Profile saved;
  static bool remembered;
  static IMgr Open() {
    return (IMgr)Activator.CreateInstance(Type.GetTypeFromCLSID(new Guid("33C53A50-F456-4884-B049-85FD643ECFED")));
  }
  static Profile Read(IMgr mgr) {
    Guid cat = new Guid("34745C63-B2F0-4784-8B67-5E12C8701A31");
    IntPtr mem = Marshal.AllocHGlobal(88);
    try {
      for (int i = 0; i < 88; i++) Marshal.WriteByte(mem, i, 0);
      int hr = mgr.GetActiveProfile(ref cat, mem);
      if (hr < 0) throw new System.ComponentModel.Win32Exception(hr);
      return Marshal.PtrToStructure<Profile>(mem);
    } finally { Marshal.FreeHGlobal(mem); }
  }
  static int Activate(IMgr mgr, uint type, ushort lang, Guid clsid, Guid profile, IntPtr hkl) {
    return mgr.ActivateProfile(type, lang, ref clsid, ref profile, hkl, 0x20000000);
  }
  public static string Remember() {
    saved = Read(Open());
    remembered = true;
    return "before lang=" + saved.langid.ToString("X4");
  }
  public static int ActivateNamed(string name) {
    IMgr mgr = Open();
    Guid empty = Guid.Empty;
    Guid pinyin = new Guid("81D4E9C9-1D3B-41BC-9E6C-4B40BF79E35E");
    Guid pinyinProfile = new Guid("FA550B04-5AD7-411F-A5AC-CA038EC515D7");
    if (name == "english") return Activate(mgr, 2, 0x0409, empty, empty, new IntPtr(0x04090409));
    if (name == "french") return Activate(mgr, 2, 0x040C, empty, empty, new IntPtr(0x040C040C));
    if (name == "chinese") return Activate(mgr, 1, 0x0804, pinyin, pinyinProfile, IntPtr.Zero);
    throw new ArgumentException(name);
  }
  public static string BroadcastName(string name) {
    long hkl = name == "english" ? 0x04090409 : name == "french" ? 0x040C040C : 0x08040804;
    IntPtr ignored;
    SendMessageTimeout(new IntPtr(0xFFFF), 0x50, new IntPtr(1), new IntPtr(hkl), 2, 200, out ignored);
    return "broadcast " + name;
  }
  public static string Restore() {
    if (!remembered) return "restored";
    int hr = Activate(Open(), saved.dwProfileType, saved.langid, saved.clsid, saved.guidProfile, saved.hkl);
    long hkl = saved.hkl.ToInt64() & 0xFFFFFFFF;
    if (hkl == 0) hkl = 0x08040804;
    IntPtr ignored;
    SendMessageTimeout(new IntPtr(0xFFFF), 0x50, new IntPtr(1), new IntPtr(hkl), 2, 200, out ignored);
    return "restored hr=" + hr;
  }
}
'@
Write-Output ([ImeSwitch]::Remember())
try {
  foreach ($name in @('english', 'chinese', 'french', 'english')) {
    $hr = [ImeSwitch]::ActivateNamed($name)
    if ($hr -ge 0) { Write-Output ([ImeSwitch]::BroadcastName($name)) }
    Write-Output ('phase ' + $name + ' hr=' + $hr)
    Start-Sleep -Seconds 5
  }
}
finally {
  Write-Output ([ImeSwitch]::Restore())
}
```
