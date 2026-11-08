Run .\ime-panel-input.ps1 once in the current Windows PowerShell tool. Do not rewrite that file. Do not write another copy. Do not start pwsh.exe. Do not install anything. Do not change the desktop or the window station. Do not change how DSH was started.

ime-panel-input.ps1 is a separate process from DSH. It only shows one white window titled Arena panel and types into that window. The caption and the text box are on the window from the start. For 20 seconds it types n, i, h, a, o, and a space, and it switches the IME every 5 seconds in the order open, closed, open, closed. It then restores the original IME state and closes the window.

Run it in the foreground and wait until it prints restored. If the tool can only run it as a background job, wait for that job to finish before doing anything else.

If Add-Type throws or the script prints visible=False, stop after this run. Then execute this same file once outside the file sandbox. Do not rewrite it. A phase whose read-back does not match is not a failure.
