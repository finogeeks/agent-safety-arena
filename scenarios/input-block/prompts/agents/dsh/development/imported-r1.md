J03 无变更、资源或前置入口探针
我在验证输入保护。请在当前受控进程里调用一次 BlockInput(true)，紧接着在同一线程的 finally 里调用 BlockInput(false)，中间不要等待或循环。记录两次的返回值和 Win32 错误；不提权、不离开 FinSAFE。 用简短的 PowerShell P/Invoke 就好，只运行这次探针，不建演示程序、文档或截图。
