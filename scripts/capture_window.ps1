param(
  [string]$OutDir = "docs/screenshots",
  [string]$Name = "capture.png"
)

Add-Type -AssemblyName System.Drawing

Add-Type @"
using System;
using System.Runtime.InteropServices;
public class WinCap {
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT r);
    [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr hWnd, IntPtr hdcBlt, int nFlags);
    public struct RECT { public int Left, Top, Right, Bottom; }
}
"@

$proc = Get-Process python,WorkTrackTimer -ErrorAction SilentlyContinue |
  Where-Object { $_.MainWindowTitle -eq "OneStop-Worktimer" } |
  Select-Object -First 1
if (-not $proc) {
  Write-Error "OneStop-Worktimer window not found"
  exit 1
}

$wshell = New-Object -ComObject wscript.shell
$wshell.AppActivate($proc.Id) | Out-Null
Start-Sleep -Milliseconds 600

$hwnd = $proc.MainWindowHandle
$rect = New-Object WinCap+RECT
[void][WinCap]::GetWindowRect($hwnd, [ref]$rect)
$w = $rect.Right - $rect.Left
$h = $rect.Bottom - $rect.Top
if ($w -lt 100 -or $h -lt 100) {
  Write-Error "Window too small to capture (${w}x${h})"
  exit 1
}

$bmp = New-Object System.Drawing.Bitmap $w, $h
$g = [System.Drawing.Graphics]::FromImage($bmp)
$hdc = $g.GetHdc()
[void][WinCap]::PrintWindow($hwnd, $hdc, 2)
$g.ReleaseHdc($hdc)
$g.Dispose()

$root = Split-Path $PSScriptRoot -Parent
$outPath = Join-Path $root $OutDir
New-Item -ItemType Directory -Force -Path $outPath | Out-Null
$path = Join-Path $outPath $Name
$bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
Write-Output "saved $path"
