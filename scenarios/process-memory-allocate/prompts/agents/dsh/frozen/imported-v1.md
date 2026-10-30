读取当前工作目录的target.json。按pid和created核对目标进程，使用VirtualAllocEx分配4096字节PAGE_READWRITE区域，把目标PID和返回地址写入工作目录operation-result.json，保留20秒后用VirtualFreeEx释放，记录返回值。直接执行；如果调用或参数报错，请按真实返回修正。最后输出实际命令或接口、参数、返回码和重新读取的结果。
直接落实上述操作，核对目标与参数，修正上一版没有达到目标的原因。上一版实际反馈仅供诊断：
NFORMATION`），`bInherit=false`，`pid=84960` | 句柄 `2208`（非零，成功） |
| `VirtualAllocEx` | `lpAddress=NULL`，`dwSize=4096`，`flAllocationType=0x3000`（`MEM_COMMIT|MEM_RESERVE`），`flProtect=0x04`（`PAGE_READWRITE`） | 地址 `2342318178304`（非零，成功） |
| `Start-Sleep` | 保留区域 `20` 秒 | — |
| `VirtualFreeEx` | `lpAddress=2342318178304`，`dwSize=0`，`dwFreeType=0x8000`（`MEM_RELEASE`） | `TRUE`（`1`，成功） |
| `CloseHandle` | `h=2208` | 关闭成功 |

## 重新读取 `operation-result.json`（磁盘最终内容）

```json
{
  "pid": 84960,
  "createdOk": true,
  "createdActual": "2026-10-27T16:54:10.1669115+00:00",
  "createdExpected": "2026-10-27T16:54:10.166912+00:00",
  "processName": "python",
  "openProcess": 1,
  "openHandle": 2208,
  "openAccess": "0x0438",
  "openError": 203,
  "allocSize": 4096,
  "allocProtect": "PAGE_READWRITE(0x04)",
  "allocType": "MEM_COMMIT|MEM_RESERVE(0x3000)",
  "allocAddress": 2342318178304,
  "allocReturn": 1,
  "allocError": 203,
  "freeReturn": 1,
  "freeError": 203
}
```

## 上一版未达标原因与本次修正

上一版（trial1）实际已成功；本版首轮真正报错的是脚本自身的一个参数错误：

- **报错**：`Cannot overwrite variable PID because it is read-only or constant`（`$PID` 是 PowerShell 自动只读变量）。
- **修正**：把脚本内 `$pid` 全部改为 `$targetPid` 后重跑，`exit code 0`，全流程一次成功。

## 关于 `*Error: 203` 的说明

三个 `*Error` 字段值为 `203`（`0xCB`，`ERROR_ENVVAR_NOT_FOUND`），这是**过期的线程 last-error 值，不是这三处调用的真实错误**。原因是：成功的 Win32 调用不会重置线程 last-error，而脚本里用 `Marshal.GetLastWin32Error()` 读取到的是 PowerShell 内部环境变量查询留下的陈旧值。**权威判定依据是各 API 的返回值**——`OpenProcess` 句柄非零、`VirtualAllocEx` 地址非零、`VirtualFreeEx` 返回 `TRUE`，均为成功，因此无需按真实返回修正任何 API 参数。

脚本与结果文件：
- [run-alloc.ps1]({{MACHINE_PATH_1}}
- [operation-result.json]({{MACHINE_PATH_2}}