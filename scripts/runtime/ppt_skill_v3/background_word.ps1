param(
    [Parameter(Mandatory=$true)][string]$InputDocx,
    [Parameter(Mandatory=$true)][string]$OutputPdf,
    [Parameter(Mandatory=$true)][string]$EvidenceJson
)
$ErrorActionPreference = 'Stop'
$app = $null
$doc = $null
$owned = $false
try {
    $app = New-Object -ComObject Word.Application
    if ($app.Path -notlike '*Microsoft Office*') { throw 'Unsupported Word COM application; WPS aliases are prohibited.' }
    if ($app.Visible -or $app.Documents.Count -ne 0) { throw 'Shared or visible Word instance; refusing to alter user documents.' }
    $owned = $true
    $app.DisplayAlerts = 0
    $app.AutomationSecurity = 3
    $missing = [Type]::Missing
    # ReadOnly=true, AddToRecentFiles=false, Visible=false. Never activate a window.
    $doc = $app.Documents.Open($InputDocx, $false, $true, $false, $missing, $missing, $false, $missing, $missing, $missing, $missing, $false)
    if ($app.Visible) { throw 'Unexpected visible Word application.' }
    foreach ($window in $app.Windows) { if ($window.Visible) { throw 'Unexpected visible Word document window.' } }
    $doc.Repaginate()
    $pages = $doc.ComputeStatistics(2)
    $doc.ExportAsFixedFormat($OutputPdf, 17, $false)
    if ($app.Visible) { throw 'Word became visible while exporting.' }
    foreach ($window in $app.Windows) { if ($window.Visible) { throw 'Word document became visible while exporting.' } }
    @{ visible = $false; read_only = [bool]$doc.ReadOnly; document_pages = [int]$pages;
       application_path = $app.Path; application_version = $app.Version; open_after_export = $false } |
       ConvertTo-Json | Set-Content -LiteralPath $EvidenceJson -Encoding UTF8
} finally {
    if ($null -ne $doc) {
        try { $doc.Close(0) } finally { [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($doc) }
    }
    if ($null -ne $app) {
        try { if ($owned -and $app.Documents.Count -eq 0) { $app.Quit(0) } }
        finally { [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($app) }
    }
}
