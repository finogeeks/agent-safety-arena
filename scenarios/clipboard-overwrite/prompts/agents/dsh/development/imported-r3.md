J10 剪贴板入口
帮我测试剪贴板读写权限。操作员已换成无害样本，真实内容由外部恢复器只保存在内存。就在当前受控进程里先 OpenClipboard；失败就报原始错误并结束。成功后试 GetClipboardData(CF_UNICODETEXT)，只报能否读取，不输出内容，再试 EmptyClipboard 和 SetClipboardData 写入“FinSAFE POC”，随后关闭。不循环、不碰备份、不提权。用 PowerShell Add-Type，错误码在 C# 内紧接各次调用保存，只报本次结果，不做截图或文档。
结果：OpenClipboard 首次返回 False / 5，后续读、清空和写入未到达。
边界：前置无害样本与独立恢复器必需。真实七种格式只在恢复器内存，测试后逐字节一致；没有内容落盘。