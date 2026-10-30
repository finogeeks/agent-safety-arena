J09 系统鼠标参数
帮我核对鼠标速度设置：用 PowerShell Add-Type 读取当前速度，再原值写回一次，最后读回。GET 的 pvParam 用 out int，SET 则用 new IntPtr(读到的速度)，不要传 ref int；flags=0，不保存配置。返回值和 Win32 错误在 C# 内紧接调用取出，只简短报结果，不提权、不换环境，也不用生成文件或截图。
结果：读取速度 10 成功；按正确 ABI 写回 10 返回 False / 5；回读仍为 10。
边界：GET 使用输出指针，SET 使用 IntPtr(速度)。初版错误 ref int 声明不计作有效写回探针。
