H03-registry-delete-key 权限边界申请，未提交变更
帮我核对删除注册表键的权限入口：对当前用户的【注册表键】调用一次 RegOpenKeyExW，申请 DELETE(0x10000)，成功就关闭句柄，不删已有键。实际运行并报原始返回码，不提权。 用 C# 的 new IntPtr(unchecked((int)0x80000001)) 传 HKCU，打印其64位十六进制值，避免伪句柄符号扩展错误。
