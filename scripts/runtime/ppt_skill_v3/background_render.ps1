param(
    [Parameter(Mandatory=$true)][string]$InputPptx,
    [Parameter(Mandatory=$true)][string]$OutputDir,
    [Parameter(Mandatory=$true)][string]$FontsJson,
    [Parameter(Mandatory=$true)][string]$EvidenceJson,
    [Parameter(Mandatory=$true)][string]$ExpectedExecutable
)
$ErrorActionPreference = 'Stop'
$mutex = New-Object System.Threading.Mutex($false, 'Local\PptSkillBackgroundRenderer')
$locked = $false
$app = $null
$presentation = $null
$registered = New-Object 'System.Collections.Generic.List[string]'
$priorCount = -1
$owned = $false
$priorAlerts = $null
$priorSecurity = $null
$failure = $null
$cleanupErrors = New-Object 'System.Collections.Generic.List[string]'
$proof = @{ status = 'failed'; renderer_provider = 'wps'; com_progid = 'KWPP.Application';
    with_window = $false; read_only = $false; cleanup_complete = $false; fonts_registered = 0; fonts_unloaded = 0 }
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class PptBackgroundFonts {
    [DllImport("gdi32.dll", EntryPoint="AddFontResourceExW", CharSet=CharSet.Unicode)]
    public static extern int AddFontResourceEx(string path, uint flags, IntPtr reserved);
    [DllImport("gdi32.dll", EntryPoint="RemoveFontResourceExW", CharSet=CharSet.Unicode)]
    public static extern bool RemoveFontResourceEx(string path, uint flags, IntPtr reserved);
}
'@
try {
    try { $locked = $mutex.WaitOne(120000) } catch [System.Threading.AbandonedMutexException] { $locked = $true }
    if (-not $locked) { throw 'Background renderer is busy; no foreground fallback.' }
    $InputPptx = [IO.Path]::GetFullPath($InputPptx)
    $OutputDir = [IO.Path]::GetFullPath($OutputDir)
    $ExpectedExecutable = [IO.Path]::GetFullPath($ExpectedExecutable)
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
    # An object envelope avoids Windows PowerShell 5.1 empty-array pipeline coercion.
    $payload = Get-Content -LiteralPath $FontsJson -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($null -eq $payload -or $null -eq $payload.PSObject.Properties['fonts']) { throw 'Invalid font manifest.' }
    foreach ($font in $payload.fonts) {
        if ($font -isnot [string] -or [string]::IsNullOrWhiteSpace($font) -or -not (Test-Path -LiteralPath $font -PathType Leaf)) {
            throw 'Invalid temporary embedded font path.'
        }
        $loaded = [PptBackgroundFonts]::AddFontResourceEx($font, 0, [IntPtr]::Zero)
        if ($loaded -le 0) {
            $proof.failed_font_file = [IO.Path]::GetFileName($font)
            throw ('Temporary embedded font registration failed: ' + [IO.Path]::GetFileName($font))
        }
        $registered.Add($font)
    }
    $proof.fonts_registered = $registered.Count
    $app = New-Object -ComObject KWPP.Application
    if (-not (Test-Path -LiteralPath $ExpectedExecutable -PathType Leaf) -or
        [IO.Path]::GetFileName($ExpectedExecutable) -inotmatch '^(wps|wpp)\.exe$' -or
        [IO.Path]::GetFullPath($app.Path).TrimEnd('\') -ine [IO.Path]::GetDirectoryName($ExpectedExecutable).TrimEnd('\')) {
        throw 'COM application does not match the selected native WPS renderer; refusing aliases.'
    }
    $proof.application_path = $app.Path
    $proof.application_version = [string]$app.Version
    $proof.application_executable = $ExpectedExecutable
    $proof.application_executable_sha256 = 'sha256:' + (Get-FileHash -LiteralPath $ExpectedExecutable -Algorithm SHA256).Hash.ToLowerInvariant()
    $proof.application_file_version = (Get-Item -LiteralPath $ExpectedExecutable).VersionInfo.FileVersion
    # Never close or alter settings in an existing user document instance.
    $priorCount = $app.Presentations.Count
    $priorWindows = $app.Windows.Count
    $proof.windows_before = [int]$priorWindows
    if ($priorCount -ne 0 -or $priorWindows -ne 0 -or $app.Visible) { throw 'Shared or visible WPS document instance; refusing to alter user presentations.' }
    $owned = $true
    $priorAlerts = $app.DisplayAlerts
    $priorSecurity = $app.AutomationSecurity
    $app.DisplayAlerts = 1
    $app.AutomationSecurity = 3
    # ReadOnly=msoTrue, Untitled=msoFalse, WithWindow=msoFalse. Never set Visible.
    $presentation = $app.Presentations.Open($InputPptx, -1, 0, 0)
    $proof.windows_during = [int]$app.Windows.Count
    if ($app.Windows.Count -ne $priorWindows) { throw 'Renderer opened an unexpected document window; aborting.' }
    if (-not $presentation.ReadOnly) { throw 'Presentation was not opened read-only.' }
    $proof.read_only = [bool]$presentation.ReadOnly
    $height = [int][Math]::Round(1600 * $presentation.PageSetup.SlideHeight / $presentation.PageSetup.SlideWidth)
    $exported = 0
    foreach ($slide in $presentation.Slides) {
        $path = Join-Path $OutputDir ('slide_{0:D3}.png' -f [int]$slide.SlideIndex)
        $slide.Export($path, 'PNG', 1600, $height)
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw 'Missing exported page image.' }
        $exported++
        [void][Runtime.InteropServices.Marshal]::ReleaseComObject($slide)
    }
    $proof.windows_after = [int]$app.Windows.Count
    if ($app.Windows.Count -ne $priorWindows) { throw 'Document window count changed while rendering; aborting.' }
    $proof.slides_exported = $exported
    $proof.status = 'exported'
} catch {
    $failure = $_.Exception.Message
    $proof.error = $failure
} finally {
    if ($null -ne $presentation) {
        try { $presentation.Close() } catch { $cleanupErrors.Add($_.Exception.Message) }
        finally { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($presentation) }
    }
    if ($null -ne $app) {
        try {
            if ($null -ne $priorAlerts) { $app.DisplayAlerts = $priorAlerts }
            if ($null -ne $priorSecurity) { $app.AutomationSecurity = $priorSecurity }
            if ($owned -and $app.Presentations.Count -eq 0) { $app.Quit() }
        } catch { $cleanupErrors.Add($_.Exception.Message) }
        finally { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($app) }
    }
    $unloaded = 0
    foreach ($font in $registered) {
        if ([PptBackgroundFonts]::RemoveFontResourceEx($font, 0, [IntPtr]::Zero)) { $unloaded++ }
        else { $cleanupErrors.Add('Temporary font unload failed: ' + [IO.Path]::GetFileName($font)) }
    }
    $proof.fonts_registered = $registered.Count
    $proof.fonts_unloaded = $unloaded
    $proof.cleanup_errors = @($cleanupErrors.ToArray())
    $proof.cleanup_complete = ($cleanupErrors.Count -eq 0)
    if ($locked) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
    $proof | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $EvidenceJson -Encoding UTF8
}
if ($null -ne $failure) { throw $failure }
if ($cleanupErrors.Count -gt 0) { throw ('Background renderer cleanup failed: ' + ($cleanupErrors -join '; ')) }
