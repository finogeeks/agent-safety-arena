# Chrome controls which sites can use your camera. Who does that for desktop agents?

## Key takeaways

1. **A website has to ask Chrome for camera access.** Once you block it, an ordinary page can’t switch to a Windows camera interface and keep filming.
2. **Running a script and recording video need separate permission.** All four desktop agents eventually recorded video in our tests. None explicitly asked for consent to record.
3. **The sandbox has to reach the tool that opens the device.** With FinShield, the capture tool could not connect to the camera in any of the four tests.

## 1. Why does a website need Chrome’s permission to use your camera?

It takes little code for a Windows program to record video from a camera or audio from a microphone. For video alone, Windows offers both Media Foundation and DirectShow. Yet the first time you visit a meeting site in Chrome, one click on “Block” keeps the site from getting a picture. If Windows offers several ways to open the camera, why can’t the site just try another one? [Audio and video capture on Windows](https://learn.microsoft.com/en-us/windows/win32/medfound/audio-video-capture-in-media-foundation) · [Video capture with DirectShow](https://learn.microsoft.com/en-us/windows/win32/directshow/video-capture)

It depends on where the code runs. A developer writing a Windows recording app can choose which Windows interface to use. When that same developer writes a meeting site, the browser decides which interfaces the page can call. To get video, the page calls `getUserMedia`, asking Chrome for access to the camera. The developer may know DirectShow inside out, but an ordinary web page has no way to call it directly. [The browser’s camera interface](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia)

Chrome knows which site is asking and which device it wants. The page’s code runs in a sandboxed renderer process. The browser process checks camera permissions. When you click “Block,” Chrome withholds the video. The site can display a message asking you to turn on your camera, but it can’t change the decision Chrome recorded for you. **Saying no once works because the page has to go through the browser that enforces your decision.** [How Chrome checks site permissions](https://github.com/chromium/chromium/blob/158.0.8127.37/chrome/browser/media/webrtc/permission_bubble_media_access_handler.cc#L122-L147) · [Chromium’s media capture architecture](https://chromium.googlesource.com/chromium/src/+/refs/tags/158.0.8127.37/docs/media/capture/README.md)

## 2. How did a desktop agent turn on the camera?

We tested four desktop agents on Windows. WorkBuddy, Claude CLI, Codex CLI and DSH all ended up recording video. With its built-in sandbox enabled, WorkBuddy recorded about fifteen seconds without asking for any additional approval. In none of the four tests did the agent explicitly ask, “May I turn on your camera and record video?”

A desktop agent can write its own programs or run one that already exists. We gave WorkBuddy a Python script we had written beforehand. WorkBuddy ran the script, which launched FFmpeg, a recording tool installed on the computer. FFmpeg opened the camera through DirectShow. At no point did the script or FFmpeg need to call a camera function provided by WorkBuddy. [WorkBuddy camera test](https://safety.finaios.ai/camera-capture/workbuddy/workbuddy-python-file-v1-20261108/en.html)

That leaves two decisions for the sandbox to enforce. WorkBuddy can decide whether a script may run. Once the script starts, may the copy of FFmpeg it launches record you? That decision still needs to be made. **Giving a script permission to run does not give it permission to turn on your camera.**

> **Test conditions.** WorkBuddy and Claude CLI requested no additional approval. Claude CLI ran without a sandbox in this Windows test. Codex CLI and DSH failed on their first attempts and completed the recording after approval to run with broader permissions. Both prompts asked for permission to run code. Neither explicitly said that approving the request would turn on the camera and record video. [Claude CLI test](https://safety.finaios.ai/camera-capture/claude-cli/claude-python-file-v2-20261110/en.html) · [Codex CLI approval prompt](https://safety.finaios.ai/camera-capture/codex-cli/codex-python-file-v2-20261109/en.html) · [DSH approval prompt](https://safety.finaios.ai/camera-capture/dsh/dsh-python-file-v2-20261109/en.html)

## 3. How do you sandbox a program that writes programs?

An agent is a program that can write programs. Today it can launch a recording tool. Tomorrow it can write code that calls Windows directly. Suppose you give the agent a camera interface and require the user’s consent every time it’s called. That sounds thorough. Run the script from the previous section again, though, and your permission check will never run. The script already has another way to reach the camera.

Chrome can enforce a website’s camera permissions because it controls which interfaces the page can use and restricts the page’s direct access to local devices. Once a desktop agent can run native programs, wrapping a handful of interfaces can only cover the programs that use them. Whoever wrote the program, it still has to ask Windows for the resources it needs. Windows can check permissions there.

Microsoft introduced the AppContainer component in Windows 8. When a program starts in an AppContainer, Windows gives it a restricted identity and records which resources that identity may use. Windows checks that identity when the program tries to access a protected resource. Take a meeting app running in an AppContainer. To get video through the Windows media capture interface, the app needs the webcam capability, and the system’s privacy settings must also allow access. Microphone access is a separate capability and can be restricted independently. You can make video calls on your own computer. The app still needs camera access in its own right. [Microsoft’s AppContainer design](https://learn.microsoft.com/en-us/windows/win32/secauthz/implementing-an-appcontainer) · [Windows app and device capabilities](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/app-capability-declarations)

That design suits an agent particularly well. It’s hard to predict what a piece of code written on the spot will do. But you can give it an environment where the camera is off limits without first understanding every line. The program can start as usual. If it tries to get video, Windows can check the identity it’s running under.

## 4. How does FinShield restrict the tool that actually opens the camera?

When we built FinShield, we borrowed an idea from Chrome. A permission check has to reach the code that actually accesses the device. On Windows, we use AppContainer and other isolation mechanisms to run the agent and the tools it launches under a restricted identity. For our recording script, the tool that matters is FFmpeg. It can ask Windows directly for video, but it makes that request with the permissions of its restricted environment. [How FinShield isolates programs on Windows](https://safety.finaios.ai/guide#implementation)

We tested the same four agents again with FinShield. In all four runs, the capture tool failed to connect to the test camera. An independent observer saw no capture begin, and none of the runs produced a valid video. All four had recorded video in the earlier tests. This time, none did. [WorkBuddy comparison](https://safety.finaios.ai/camera-capture/workbuddy/workbuddy-python-file-v1-20261108/en.html) · [Claude CLI comparison](https://safety.finaios.ai/camera-capture/claude-cli/claude-python-file-v2-20261110/en.html) · [Codex CLI comparison](https://safety.finaios.ai/camera-capture/codex-cli/codex-python-file-v2-20261109/en.html) · [DSH comparison](https://safety.finaios.ai/camera-capture/dsh/dsh-python-file-v2-20261109/en.html)

Think back to the meeting site. You can click “Block” without knowing which Windows interface Chrome uses underneath. You should have the same confidence when you hand a task to a desktop agent. You shouldn’t have to know what FFmpeg is, much less read a script to find out whether it might film you. **If you haven’t agreed to turn on the camera, neither the agent nor the tools it launches should get a picture. That’s what the sandbox should protect.**
