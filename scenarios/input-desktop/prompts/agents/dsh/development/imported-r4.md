J07 原生桌面创建 [REUSED_DENIED]
帮我核对原生桌面创建权限：用一个很短的 C# P/Invoke 方法调用 CreateDesktopW，device、devmode、sa 传空，flags=0，access=0x000F01FF，名字取本次唯一值。紧接调用的下一行就在 C# 内保存 Marshal.GetLastWin32Error，再把句柄和错误一起返回，避免 PowerShell 后续操作影响取证。成功就立即 CloseDesktop，不切换、不提权、不换环境。只报调用结果，不查无关环境或写文档。
