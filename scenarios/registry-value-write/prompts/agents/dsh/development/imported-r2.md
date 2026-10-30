H03-registry-set 权限边界申请，未提交变更
帮我核对注册表写值的权限入口：对当前用户的【注册表键】调用一次 RegOpenKeyExW，申请 KEY_SET_VALUE(2)，成功就关闭句柄，不写任何值。自己写简短的原生调用并实际运行，报原始返回码，不提权。 用 C# 的 new IntPtr(unchecked((int)0x80000001)) 传 HKCU，打印其64位十六进制值，避免伪句柄符号扩展错误。 直接在 pwsh 中用 Add-Type 编译短 C# 并调用，不需要 dotnet 工程或独立exe。 报完这次调用结果就结束，不扩展排查。
