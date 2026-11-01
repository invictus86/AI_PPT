param(
    [Parameter(Mandatory=$true)][string]$InputDocx,
    [Parameter(Mandatory=$true)][string]$OutputPdf,
    [Parameter(Mandatory=$true)][string]$EvidenceJson,
    [ValidateSet('wps','word')][string]$Renderer = 'wps',
    [Parameter(Mandatory=$true)][string]$ExpectedExecutable
)
$ErrorActionPreference = 'Stop'
$app = $null
$doc = $null
$owned = $false
$documents = $null
# Support registered Office PIAs with ByRef arguments as well as IDispatch.
function Invoke-ComMethod($Target, [string]$Name, [object[]]$Arguments) {
    $Target.GetType().InvokeMember($Name, [Reflection.BindingFlags]::InvokeMethod, $null, $Target, $Arguments)
}
function Assert-Hidden($Application) {
    if ($Application.Visible) { throw 'Unexpected visible document application.' }
    foreach ($window in $Application.Windows) {
        if ($window.Visible) { throw 'Unexpected visible document window.' }
    }
}
try {
    $progid = if ($Renderer -eq 'wps') { 'KWPS.Application' } else { 'Word.Application' }
    $app = New-Object -ComObject $progid
    $expectedName = if ($Renderer -eq 'wps') { 'wps.exe' } else { 'winword.exe' }
    if (-not (Test-Path -LiteralPath $ExpectedExecutable -PathType Leaf) -or
        [IO.Path]::GetFileName($ExpectedExecutable) -ine $expectedName -or
        [IO.Path]::GetFullPath($app.Path).TrimEnd('\') -ine [IO.Path]::GetDirectoryName([IO.Path]::GetFullPath($ExpectedExecutable)).TrimEnd('\')) {
        throw 'COM application does not match the selected renderer; refusing aliases.'
    }
    if ($app.Visible -or $app.Documents.Count -ne 0) { throw 'Shared or visible document instance; refusing to alter user documents.' }
    $owned = $true
    $app.DisplayAlerts = 0
    $app.AutomationSecurity = 3
    $missing = [Type]::Missing
    $documents = $app.Documents
    # ReadOnly=true, AddToRecentFiles=false, Visible=false, NoEncodingDialog=true.
    $doc = Invoke-ComMethod $documents 'Open' @($InputDocx, $false, $true, $false, $missing, $missing, $false, $missing, $missing, $missing, $missing, $false, $false, $missing, $true, $missing)
    Assert-Hidden $app
    if (-not $doc.ReadOnly) { throw 'Document was not opened read-only.' }
    Invoke-ComMethod $doc 'Repaginate' @()
    $pages = Invoke-ComMethod $doc 'ComputeStatistics' @(2)
    Invoke-ComMethod $doc 'ExportAsFixedFormat' @($OutputPdf, 17, $false)
    Assert-Hidden $app
    if (-not (Test-Path -LiteralPath $OutputPdf -PathType Leaf)) { throw 'Renderer did not export a PDF.' }
    @{ visible = $false; read_only = [bool]$doc.ReadOnly; document_pages = [int]$pages;
       application_path = $app.Path; application_version = $app.Version; application_executable = $ExpectedExecutable;
       renderer_provider = $Renderer; com_progid = $progid; open_after_export = $false } |
       ConvertTo-Json | Set-Content -LiteralPath $EvidenceJson -Encoding UTF8
} finally {
    try {
        if ($null -ne $doc) {
            try { Invoke-ComMethod $doc 'Close' @(0) }
            finally { [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($doc) }
        }
    } finally {
        if ($null -ne $documents) { [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($documents) }
        if ($null -ne $app) {
            try { if ($owned -and $app.Documents.Count -eq 0) { Invoke-ComMethod $app 'Quit' @(0) } }
            finally { [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($app) }
        }
    }
}
