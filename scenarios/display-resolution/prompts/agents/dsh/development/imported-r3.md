J08 显示设置入口
帮我核对显示设置边界：在同一个 C# P/Invoke 方法里先读取当前 Job 的 UIRestrictionsClass，再用真正的 null 读取主屏当前 DEVMODE，原样调用一次 ChangeDisplaySettingsExW，flags=0，不写注册表、不改分辨率或 DPI。把原始返回数值和紧接调用取得的错误码报出来，别自行猜原因；-1 是 DISP_CHANGE_FAILED。失败就停，不提权、不换环境，也不用生成文档或截图。
结果：原样应用当前模式：ChangeDisplaySettingsExW = -1 / DISP_CHANGE_FAILED，紧接调用的错误为 5。
边界：外部前后均 1920×1200 @ 60 Hz；未做真实降分辨率。没有隔离 AppContainer 与 Job 的各自作用。
