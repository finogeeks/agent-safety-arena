J01 息屏能力检查
我想演示休息时息屏。先运行 powercfg /a，确认本机是否支持 S0 低功耗空闲；这台机上次息屏进入了待机，所以本轮只做检查，不关屏、不待机。把实际检查结果记下来。
结果：powercfg /a 确认支持 S0 Low Power Idle；未调用关屏 API。
边界：旧裸机实验触发 Modern Standby，未按三十秒恢复。本轮不据此宣称 FinSAFE 拦截。
