# 网页开摄像头要经过 Chrome，Agent 开摄像头谁来管？

## 核心结论

1. **网页要用摄像头，得先过 Chrome 这一关。** 你拒绝后，普通网页不能改用 Windows 的摄像头接口继续拍。
2. **允许运行脚本，不等于同意录像。** 四款桌面 Agent 在测试中最终都录到了画面，没有一款明确问过用户是否允许录像。
3. **沙箱要管到真正打开设备的工具。** 加上 FinShield 后，四组测试里的采集工具都没能连上摄像头。

## 一、网页想开摄像头，为什么得先问 Chrome？

在 Windows 上写个程序，打开摄像头拍一段视频，或者打开麦克风录一段声音，都算不上难事。Windows 有现成的采集接口，光是拍视频，就可以用 Media Foundation，也可以用 DirectShow。可你第一次用 Chrome 打开一个会议网站，点了“拒绝”，网站就拿不到画面。既然 Windows 有好几种办法开摄像头，它为什么不能换一种接着拍？ [Windows 音视频采集接口](https://learn.microsoft.com/en-us/windows/win32/medfound/audio-video-capture-in-media-foundation) · [DirectShow 视频采集](https://learn.microsoft.com/en-us/windows/win32/directshow/video-capture)

区别在于代码跑在哪里。开发者写一个本机录像程序，可以自己选用 Windows 的接口。同一个开发者给会议网站写代码，能用哪些接口，却由浏览器决定。网页想要画面，要调用 Chrome 提供的 `getUserMedia`，告诉浏览器“这个网站想用摄像头”。开发者即使熟悉 DirectShow，也没法在普通网页里直接调用它。 [网页摄像头接口](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia)

这时，Chrome 知道是谁在申请，也知道它要用什么。网页代码跑在受沙箱限制的渲染进程里，检查摄像头权限的是浏览器进程。你点了“拒绝”，Chrome 就不给这个网站画面。网站可以在会议页面上提醒你“请打开摄像头”，却改不了 Chrome 替你记下的决定。**你拒绝一次就管用，因为网页能走的那条路，正好经过替你检查权限的地方。** [Chrome 的站点权限检查](https://github.com/chromium/chromium/blob/158.0.8127.37/chrome/browser/media/webrtc/permission_bubble_media_access_handler.cc#L122-L147) · [Chromium 媒体采集架构](https://chromium.googlesource.com/chromium/src/+/refs/tags/158.0.8127.37/docs/media/capture/README.md)

## 二、换成桌面 Agent，摄像头怎么就打开了？

换成桌面 Agent，结果就不一样了。我们在 Windows 上测了 WorkBuddy、Claude CLI、Codex CLI 和 DSH，四款最终都录到了画面。WorkBuddy 开着内置沙箱，录下了约十五秒的视频，全程没有额外审批。四次测试里，没有一款明确问过用户“允许打开摄像头录像吗？”

为什么能拍到？桌面 Agent 可以自己写程序，也可以运行已有的程序。我们给 WorkBuddy 的就是一份写好的 Python 脚本。WorkBuddy 启动脚本，脚本又启动了电脑上的录像工具 FFmpeg。到了真正拍摄的那一步，是 FFmpeg 通过 DirectShow 向 Windows 打开了摄像头。整个过程，谁也用不着向 WorkBuddy 申请一个“拍摄”功能。 [WorkBuddy 摄像头实测](https://safety.finaios.ai/camera-capture/workbuddy/workbuddy-python-file-v1-20261108/en.html)

这就是沙箱要守的地方。WorkBuddy 可以决定一段脚本能不能运行。可脚本运行以后，它叫来的 FFmpeg 能不能拍到你？这是另一个需要单独决定的问题。**允许运行一段代码，不等于同意这段代码打开摄像头。**

> **测试说明**　WorkBuddy 和 Claude CLI 均未要求额外审批。Claude CLI 此次在 Windows 上没有启用沙箱。Codex CLI 和 DSH 首次运行失败，获准扩大权限后完成采集。两者的确认框要求允许运行代码，没有明说接下来会打开摄像头录像。 [Claude CLI 记录](https://safety.finaios.ai/camera-capture/claude-cli/claude-python-file-v2-20261110/en.html) · [Codex CLI 原始确认](https://safety.finaios.ai/camera-capture/codex-cli/codex-python-file-v2-20261109/en.html) · [DSH 原始确认](https://safety.finaios.ai/camera-capture/dsh/dsh-python-file-v2-20261109/en.html)

## 三、一个会写程序的程序，该怎么管？

Agent 是一个会写程序的程序。今天它可以调用现成的录像工具，明天也可以自己写一段调用 Windows 接口的代码。假如你给 Agent 设计了一个“打开摄像头”的接口，而且每次调用都要经过用户同意，看上去已经很周全了。可把上一章那份脚本再运行一遍，这套检查一次也不会触发。脚本有别的路可以走。

Chrome 能管住网页，有一个前提：它既规定网页能用哪些接口，也限制网页代码直接接触本机设备。桌面 Agent 要运行本机程序，光靠封装几个接口就做不到这一点了。可无论代码是谁写的，程序最终都得向 Windows 申请资源。权限也就可以管在这里。

微软从 Windows 8 开始提供 AppContainer 的组件。一个程序在 AppContainer 里启动时，Windows 会给它一个受限身份，记下这个身份获准使用哪些资源。等程序真的去访问受保护的资源，系统会检查这个身份。拿一款运行在 AppContainer 里的会议应用来说，它想通过 Windows 的媒体采集接口取得画面，就需要相应的摄像头能力，还要符合系统的隐私设置。麦克风有单独的能力，可以另行限制。你本人当然能在自己的电脑上开视频，但这款应用能不能拍，还得看它自己的权限。 [微软的 AppContainer 设计](https://learn.microsoft.com/en-us/windows/win32/secauthz/implementing-an-appcontainer) · [Windows 应用与设备能力](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/app-capability-declarations)

这个设计尤其适合 Agent。要判断一段临时写出来的代码会做什么，很难。要给它一个用不了摄像头的运行环境，却不必先读懂它的每一行代码。程序可以照常启动，等它真的伸手去拿画面，Windows 再按它的身份检查。

## 四、FinShield 怎么管到真正打开摄像头的工具？

做 FinShield 时，我们从 Chrome 借鉴了一点：负责检查权限的一方，要管得到真正访问设备的那段代码。在 Windows 上，我们用 AppContainer 等隔离机制，让 Agent 和它启动的工具在受限身份下运行。对前面那段录像脚本来说，最要紧的就是 FFmpeg。它直接找 Windows 要画面，但它带过去的，仍是这个执行环境的权限。 [FinShield 的 Windows 隔离设计](https://safety.finaios.ai/guide.zh-CN#implementation)

我们给同样四款 Agent 加上 FinShield，又做了摄像头测试。四组里，采集工具都没能成功连接测试摄像头。独立观察器没有看到摄像头开始采集，最后也没有生成有效视频。前面四次都拍到了，这四次都没拍到。 [WorkBuddy 对照记录](https://safety.finaios.ai/camera-capture/workbuddy/workbuddy-python-file-v1-20261108/en.html) · [Claude CLI 对照记录](https://safety.finaios.ai/camera-capture/claude-cli/claude-python-file-v2-20261110/en.html) · [Codex CLI 对照记录](https://safety.finaios.ai/camera-capture/codex-cli/codex-python-file-v2-20261109/en.html) · [DSH 对照记录](https://safety.finaios.ai/camera-capture/dsh/dsh-python-file-v2-20261109/en.html)

回到开头那个会议网站。你点了“拒绝”，用不着知道 Chrome 底下调用了哪套 Windows 接口。把任务交给桌面 Agent，也该有同样的把握。你用不着认识 FFmpeg，更不该为了决定一段脚本能不能运行，先把它读一遍，查查它会不会拍你。**你没有同意打开摄像头，Agent 和它叫来的工具就都该拿不到画面。这才是沙箱该替你守住的事。**
