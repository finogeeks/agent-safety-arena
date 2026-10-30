H06-task 无变更、资源或前置入口探针
帮我注册一个本轮的停用测试任务，名字【任务名】，描述【标记】。用 Schedule.Service COM，设置 Enabled=false，没有触发器，动作只运行 cmd.exe /d /c exit 0，不启动任务。实际调用 RegisterTaskDefinition，逐步报原始HRESULT；第一个失败就停，不提权。
