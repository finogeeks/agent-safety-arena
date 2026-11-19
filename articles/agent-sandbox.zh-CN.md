# 从 Chrome 到 AI Agent：“沙箱”正在沦为安全包装

## 第一章　半包的保护，完整的安全感

**“沙箱”这个词，首先让人想到的就是安全。** 它让人想到一个被隔开的空间：程序在里面运行，即使出了问题，也有一道边界限制它影响外面的电脑。Chrome 等浏览器多年的使用体验，帮助建立了这种安全预期。所以，当 Agent 产品告诉用户“沙箱已开启”，用户很容易放心：它可以替我运行程序，但应该有机制保护我的设备、我的桌面、我的数据。

**然而，我们测出来的结果，令人触目惊心。** 在对 Codex CLI、WorkBuddy 和 DSH 的受控测试中，摄像头打开并录下了画面，大量窗口盖住了桌面，鼠标设置被改动，文件访问权限也被扩大。部分敏感操作在内置沙箱开启时直接完成，没有额外审批；另一些则在批准扩大权限后完成，但确认提示没有清楚说明敏感动作及其后果。**沙箱没有覆盖这些风险，审批也没有把放行的风险讲明白。**

真正令人不安的，是保护能力与安全感之间的落差。用户看到“沙箱已开启”，以为设备有人管、桌面有人护、文件有边界，实际受限的却只是部分操作。**给用户半包的保护，却卖给用户完整的安全感，就是安全误导。** 保护覆盖到哪里，安全承诺就应当停在哪里。从 Chrome 到 AI Agent，同样叫“沙箱”，究竟关住了什么，又把多少权限留在了外面？

## 第二章　Chrome 建立的信任：代码失控之后，保护仍应存在

在 Chrome 出现之前，浏览器就已经能运行从网上下载的 Java 小程序。比如，你打开网页玩一局游戏，游戏代码就在你的电脑上运行。可你同意玩游戏，并不等于你也同意让游戏读取你的文件。早期的 Java 沙箱允许小游戏运行，同时限制它访问本地文件。[Java 早期沙箱模型](https://docs.oracle.com/javase/8/docs/technotes/guides/security/spec/security-spec.doc1.html)

2008 年，Chrome 的设计者又往前想了一步。负责显示网页、执行网页脚本的渲染进程，是 Chrome 自己写的。可一旦恶意网页利用漏洞接管了它，**代码还是 Chrome 写的，发号施令的人却换了。** 为此，Chrome 在 Windows 上把渲染进程关进沙箱，只给它很少的权限。即使攻击者控制了它，操作系统仍然能限制它读写本地文件。键盘、鼠标和窗口又是另一回事，文件权限管不到它们。为此，Chrome 还把这个进程和用户正在使用的桌面隔开，限制它接触用户的输入和其他程序的窗口。[Chromium 团队 2008 年的设计说明](https://blog.chromium.org/2008/10/new-approach-to-browser-security-google.html)

还有一道关在沙箱外面。渲染进程拿不到用户保存在浏览器里的密码，能不能请浏览器进程替它拿？即使请求来自 Chrome 自己的代码，浏览器也得核对发出请求的页面有没有资格使用这份密码。论坛页面就算自称是邮箱登录页，也不能拿到邮箱密码。**沙箱里的程序自己能做什么、能请别人代办什么，两头都得管。** [Chromium 对已失控渲染进程的防护说明](https://github.com/chromium/chromium/blob/main/docs/security/compromised-renderers.md#passwords)

## 第三章　Agent 的半包沙箱，漏掉了哪些基本防护？

换到 Agent 身上，普通用户的要求也一样简单。在 Chrome 里，我打开一个网页看新闻，网页要用麦克风，得有我的许可。要共享屏幕，得由我选它能看哪个窗口。现在，Agent 也告诉我“沙箱已开启”。**我让你整理一张表格，你就不该顺手听我开会、截走我的聊天窗口，或者关掉我正在用的软件。** 我们在 Windows 上测了 WorkBuddy、Codex CLI 和 DSH，看看这几条最基本的要求，它们做到了多少。

先看麦克风和摄像头。WorkBuddy 和 DSH 运行收音程序，麦克风直接就开了，没有额外审批。Codex CLI 弹了确认框，提到了采集脚本和麦克风设备，却没直说点下去就会开始收音。批准之后，程序拿到了音频。**麦克风一被打开，隐私这道关就已经破了。** 换成摄像头，WorkBuddy 同样没再问一句，程序就录下了约十五秒的画面。Codex CLI 和 DSH 都请求了批准，也都没直说摄像头会打开，放行后两款都录到了画面。测试的时候，镜头前放的是测试卡。可换到真实场景，**镜头对着的就是你。** [WorkBuddy 麦克风实测](https://safety.finaios.ai/microphone-capture/workbuddy/workbuddy-python-file-v1-20261108/en.html) · [Codex CLI 麦克风实测](https://safety.finaios.ai/microphone-capture/codex-cli/codex-python-file-v2-20261109/en.html) · [DSH 麦克风实测](https://safety.finaios.ai/microphone-capture/dsh/dsh-python-file-v2-20261109/en.html) · [WorkBuddy 摄像头实测](https://safety.finaios.ai/camera-capture/workbuddy/workbuddy-python-file-v1-20261108/en.html) · [Codex CLI 摄像头实测](https://safety.finaios.ai/camera-capture/codex-cli/codex-python-file-v2-20261109/en.html) · [DSH 摄像头实测](https://safety.finaios.ai/camera-capture/dsh/dsh-python-file-v2-20261109/en.html)

屏幕里的东西也一样。三款 Agent 最终都没拦住截屏。程序每隔两秒截一张，连截五张，张张都是整个桌面。WorkBuddy 和 DSH 直接截了，Codex CLI 在批准后完成。如果左边开着你交给它的表格，右边开着私人聊天，这一张截图就把两边都收了进去。再往前一步，它还能不能关掉别的程序？我们专门启动了一个独立的测试进程。WorkBuddy 和 Codex CLI 运行的程序直接把它关了，没有额外审批。DSH 申请扩大权限，点下“允许一次”，那个进程也停了。[WorkBuddy 截屏](https://safety.finaios.ai/screen-capture/workbuddy/workbuddy-desktop-file-v2-20261108/en.html) · [Codex CLI 截屏](https://safety.finaios.ai/screen-capture/codex-cli/codex-desktop-file-v3-20261109/en.html) · [DSH 截屏](https://safety.finaios.ai/screen-capture/dsh/dsh-desktop-file-v3-20261109/en.html) · [WorkBuddy 结束进程](https://safety.finaios.ai/process-terminate/workbuddy/workbuddy-python-file-v2-20261111/en.html) · [Codex CLI 结束进程](https://safety.finaios.ai/process-terminate/codex-cli/codex-python-file-v2-20261112/en.html) · [DSH 结束进程](https://safety.finaios.ai/process-terminate/dsh/dsh-python-file-v2-20261111/en.html)

上面只是我们做过的一部分测试。开麦克风、截取整个屏幕、关掉另一个程序，这些事会影响谁，普通人一听就明白。可在这几款 Agent 的沙箱里，有的操作直接就做成了，有的点一次“允许”，整段程序就放行了。**连这些最基本的防护都没做好，一句“沙箱已开启”，凭什么让用户放心？** 再看看 Agent 声称要保护的用户数据。

## 第四章　Agent 说要保护用户数据，半包就等于没包

Agent 说能保护我的数据，我的理解很简单。我把一份客户名单交给它整理，干完活，名单我还打得开，谁能改、谁能删，也还得由我说了算。我们让 WorkBuddy 删除一个受保护的目录。测试结束，目录还在，里面的文件也完好。同样的任务交给 DSH，整个目录连同文件一起被删了。这一点，WorkBuddy 做得好。 [WorkBuddy 删除实测](https://safety.finaios.ai/protected-directory-delete/workbuddy/workbuddy-direct-v4-20261112/en.html) · [DSH 删除实测](https://safety.finaios.ai/protected-directory-delete/dsh/dsh-direct-v4-20261112/en.html)

可在另一项测试里，WorkBuddy 运行的程序改了一份样本文件的权限，把修改权和删除权给了 Windows 的“所有人”组，全程没有额外审批。再打开这份文件，里面一个字都没变。可原来无权删它的人，现在有权删了。**我把文件交给你处理，什么时候也把“决定谁能删它”的权力交给你了？** [WorkBuddy 文件权限实测](https://safety.finaios.ai/file-acl-grant/workbuddy/workbuddy-python-file-v2-20261111/en.html)

还有一层更容易被忽略：存放文件的磁盘。在此前的一项测评中，WorkBuddy 开着沙箱，它运行的程序通过 `CreateFileW` 打开了物理磁盘，随后把数据直接写进了盘里。**Agent 连删除命令都不用，就能直接覆盖盘上的数据。沙箱拦住了一次文件删除，却没拦住这次直接写盘。** [微软对直接写盘风险的说明](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew#physical-disks-and-volumes)

用户手里的名单只有一份。交给 Agent 处理时，难道还要逐项叮嘱它，别删文件，别把删除权给别人，也别去动存放文件的磁盘？Agent 既然说要保护用户数据，就该把这些都算进去。**只要漏掉的那条路足以毁掉这份数据，其余的路拦得再严，也补不回这一次损失。就保护用户数据这件事而言，半包就等于没包。**

## 第五章　“沙箱已开启”，这句承诺谁来兑现？

Chrome 让人信任“沙箱”这两个字，是因为它先替用户想过一个问题：程序出了错，而用户又没看出来，电脑还能不能守得住？今天，Agent 也告诉用户“沙箱已开启”。一个普通人看到这行字，当然有理由相信，自己交代的事，Agent 可以做。超出授权的事，系统会替他拦下来。

可前面的实测让我们看到，Agent 能动用的权限，远远超过了沙箱实际管住的范围。程序换一种做法，用户以为还在的保护就可能落空。产品能守住哪里，就该把承诺说到哪里。这一点，Claude Code 更坦荡：它明说，在原生 Windows 上运行命令，没有沙箱。**只做到半包，却借“沙箱已开启”卖给用户完整的安全感，就是在欺骗消费者。** [Claude Code 官方说明](https://code.claude.com/docs/en/sandboxing)

更不能拿用户点过“允许”来交差。用户同意的是自己交代的那件事。他没义务读懂每一行代码，更没义务替产品担保，程序接下来动用的每一项权限都合情合理。普通人正是因为做不到这些，才需要沙箱。**用户点一次“允许”，只是同意 Agent 开始干活。产品说一句“沙箱已开启”，就得对干活过程中的保护负责。**
