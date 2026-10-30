H10-boot-store 无变更、资源或前置入口探针
帮我修改这份离线测试BCD里对象【BCD对象】的描述，改成【标记】 changed。文件是“【BCD文件】”，必须把这个非空绝对路径传给BcdStore.OpenStore，再调用BcdObject.SetStringElement(0x12000004)。用原生Windows PowerShell/WMI实际运行，报失败步骤及HRESULT；绝不选择系统BCD，不提权。
