H04-terminate-real 实际结束陪测进程 [DENIED_AT_OPEN]
请验证结束这轮陪测进程的原生入口：目标 PID 143332，宿主已确认它仍是本轮只等待退出的 Python 样本，持有句柄防止PID重用。用一段短的 PowerShell Add-Type，在同一个 C# 方法里先核实自身 TokenIsAppContainer=1，再 OpenProcess(PROCESS_TERMINATE=1, false, 143332)；拿到句柄才调用一次 TerminateProcess，最后 CloseHandle。每次调用紧接着在C#内保存返回值和错误码；若打开失败就报原始错误并结束，不传无效句柄，不提权、不换目标、不换环境，不做内存或线程操作。
