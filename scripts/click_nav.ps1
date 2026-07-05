param(
  [Parameter(Mandatory=$true)][string]$View
)

$views = @{ dashboard=0; sessions=1; calendar=2; analytics=3; projects=4; settings=5 }
if (-not $views.ContainsKey($View)) { Write-Error "Unknown view: $View"; exit 1 }

Add-Type @"
using System;
using System.Runtime.InteropServices;
public class WinNav {
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT r);
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int X, int Y);
    [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint dx, uint dy, uint d, UIntPtr e);
    public struct RECT { public int Left, Top, Right, Bottom; }
    public const uint DOWN = 0x0002; public const uint UP = 0x0004;
}
"@

$proc = Get-Process python,WorkTrackTimer -ErrorAction SilentlyContinue |
  Where-Object { $_.MainWindowTitle -eq "OneStop-Worktimer" } | Select-Object -First 1
if (-not $proc) { Write-Error "Window not found"; exit 1 }

$wshell = New-Object -ComObject wscript.shell
$wshell.AppActivate($proc.Id) | Out-Null
Start-Sleep -Milliseconds 400

$rect = New-Object WinNav+RECT
[void][WinNav]::GetWindowRect($proc.MainWindowHandle, [ref]$rect)
$idx = $views[$View]
$x = $rect.Left + 37
$y = $rect.Top + 83 + ($idx * 54)
[void][WinNav]::SetCursorPos($x, $y)
Start-Sleep -Milliseconds 120
[WinNav]::mouse_event([WinNav]::DOWN, 0, 0, 0, [UIntPtr]::Zero)
Start-Sleep -Milliseconds 80
[WinNav]::mouse_event([WinNav]::UP, 0, 0, 0, [UIntPtr]::Zero)
Write-Output "clicked $View at $x,$y"
