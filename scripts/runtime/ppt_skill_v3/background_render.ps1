param(
    [Parameter(Mandatory=$true)][string]$InputPptx,
    [Parameter(Mandatory=$true)][string]$OutputDir,
    [Parameter(Mandatory=$true)][string]$FontsJson,
    [Parameter(Mandatory=$true)][string]$EvidenceJson
)
$ErrorActionPreference = 'Stop'
# One shared desktop renderer; callers never manipulate the user's foreground.
$mutex = New-Object System.Threading.Mutex($false, 'Local\PptSkillBackgroundRenderer')
$locked = $false
$app = $null
$presentation = $null
$registered = @()
$priorCount = 0
$priorAlerts = $null
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class PptBackgroundFonts {
    [DllImport("gdi32.dll", CharSet=CharSet.Unicode)]
    public static extern int AddFontResourceEx(string path, uint flags, IntPtr reserved);
    [DllImport("gdi32.dll", CharSet=CharSet.Unicode)]
    public static extern bool RemoveFontResourceEx(string path, uint flags, IntPtr reserved);
}
'@
try {
    try { $locked = $mutex.WaitOne(120000) } catch [System.Threading.AbandonedMutexException] { $locked = $true }
    if (-not $locked) { throw 'Background renderer is busy; no foreground fallback.' }
    $InputPptx = [System.IO.Path]::GetFullPath($InputPptx)
    $OutputDir = [System.IO.Path]::GetFullPath($OutputDir)
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
    foreach ($font in @(Get-Content -LiteralPath $FontsJson -Raw -Encoding UTF8 | ConvertFrom-Json)) {
        if ([PptBackgroundFonts]::AddFontResourceEx($font, 0, [IntPtr]::Zero) -le 0) { throw 'Temporary embedded font registration failed.' }
        $registered += $font
    }
    $app = New-Object -ComObject PowerPoint.Application
    if ($app.Path -notlike '*Microsoft Office*') { throw 'Unexpected COM application. WPS aliases and foreground fallback are prohibited.' }
    $priorCount = $app.Presentations.Count
    $priorWindows = $app.Windows.Count
    $priorAlerts = $app.DisplayAlerts
    $app.DisplayAlerts = 1
    # WithWindow=msoFalse. Never set Visible, activate, run, minimize or focus.
    $presentation = $app.Presentations.Open($InputPptx, -1, 0, 0)
    if ($app.Windows.Count -ne $priorWindows) { throw 'Renderer opened an unexpected document window; aborting.' }
    $height = [int][Math]::Round(1600 * $presentation.PageSetup.SlideHeight / $presentation.PageSetup.SlideWidth)
    $exported = 0
    foreach ($slide in $presentation.Slides) {
        $path = Join-Path $OutputDir ('slide_{0:D3}.png' -f [int]$slide.SlideIndex)
        $slide.Export($path, 'PNG', 1600, $height)
        $exported++
    }
    if ($app.Windows.Count -ne $priorWindows) { throw 'Document window count changed while rendering; aborting.' }
    @{ with_window = $false; windows_before = $priorWindows; windows_during = $app.Windows.Count;
       slides_exported = $exported; application_path = $app.Path; application_version = $app.Version } |
        ConvertTo-Json | Set-Content -LiteralPath $EvidenceJson -Encoding UTF8
} finally {
    try {
        try {
            if ($null -ne $presentation) {
                try { $presentation.Close() }
                finally { [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($presentation) }
            }
        } finally {
            if ($null -ne $app) {
                try {
                    if ($null -ne $priorAlerts) { $app.DisplayAlerts = $priorAlerts }
                    if ($priorCount -eq 0 -and $app.Presentations.Count -eq 0) { $app.Quit() }
                } finally { [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($app) }
            }
        }
    } finally {
        try {
            foreach ($font in $registered) { [void][PptBackgroundFonts]::RemoveFontResourceEx($font, 0, [IntPtr]::Zero) }
        } finally {
            if ($locked) { $mutex.ReleaseMutex() }
            $mutex.Dispose()
        }
    }
}
