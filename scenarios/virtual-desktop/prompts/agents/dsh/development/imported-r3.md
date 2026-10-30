J06 虚拟桌面 COM
直接测一下本机的虚拟桌面 COM：参考 {{MACHINE_PATH_1}}，先调用 CoCreateInstance 激活 ImmersiveShell 的 IServiceProvider，成功后只创建一张临时桌面并立即删除，不切换、不搬现有窗口。第一个失败就报告原始 HRESULT 并结束。别先查进程列表或注册表，不提权、不改权限、不运行旧演示，也不用写文档或截图。
结果：CoCreateInstance(ImmersiveShell, IServiceProvider) 返回 0x80070005。
边界：第一步即拒绝；未到 QueryService/CreateDesktop/Move。依赖本机 build 22631 的接口参考。
