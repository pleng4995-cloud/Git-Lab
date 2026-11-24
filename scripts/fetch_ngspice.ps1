# Fetch and unpack a portable ngspice-47 build into C:\Tools\ngspice-47.
#
# Writes nothing inside the repository: the archive, the optional 7zr helper
# and the extraction staging area all live under %TEMP%.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\fetch_ngspice.ps1
#
# Exit codes:
#   0  ngspice.exe is installed (or was already present)
#   1  download or extraction failed

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$InstallRoot  = 'C:\Tools\ngspice-47'
$Version      = '47'
$ArchiveName  = "ngspice-$Version" + '_64.7z'
$ArchiveUrls  = @(
    # Direct mirror path: serves the archive itself, no SourceForge HTML interstitial.
    "https://downloads.sourceforge.net/project/ngspice/ng-spice-rework/$Version/$ArchiveName",
    "https://sourceforge.net/projects/ngspice/files/ng-spice-rework/$Version/$ArchiveName/download"
)
$SevenZiprUrl = 'https://www.7-zip.org/a/7zr.exe'
$WorkDir      = Join-Path $env:TEMP 'opencode\ngspice-fetch'
$ArchivePath  = Join-Path $WorkDir $ArchiveName
$SevenZiprPath = Join-Path $WorkDir '7zr.exe'
$ExtractDir   = Join-Path $WorkDir 'extract'

function Find-NgspiceExe {
    param([string]$Root)
    if (-not (Test-Path $Root)) { return $null }
    return Get-ChildItem -Path $Root -Recurse -Filter 'ngspice.exe' -File -ErrorAction SilentlyContinue |
        Select-Object -First 1
}

function Test-SevenZipSignature {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return $false }
    $stream = [System.IO.File]::OpenRead($Path)
    try {
        $buffer = New-Object byte[] 6
        $read = $stream.Read($buffer, 0, 6)
    } finally {
        $stream.Dispose()
    }
    if ($read -lt 6) { return $false }
    # 7z magic: 37 7A BC AF 27 1C
    return ($buffer[0] -eq 0x37 -and $buffer[1] -eq 0x7A -and $buffer[2] -eq 0xBC -and
            $buffer[3] -eq 0xAF -and $buffer[4] -eq 0x27 -and $buffer[5] -eq 0x1C)
}

function Save-UrlToFile {
    param([string]$Url, [string]$Destination)
    $curl = Get-Command curl.exe -ErrorAction SilentlyContinue
    if ($curl) {
        & $curl.Source -L --fail --max-time 600 -o $Destination $Url
        if ($LASTEXITCODE -eq 0 -and (Test-Path $Destination)) { return $true }
        Write-Warning "curl exited with code $LASTEXITCODE for $Url"
        return $false
    }
    Invoke-WebRequest -Uri $Url -OutFile $Destination -UseBasicParsing -MaximumRedirection 10
    return $true
}

function Get-Archive {
    param([string]$Destination)
    New-Item -ItemType Directory -Force -Path (Split-Path $Destination) | Out-Null
    foreach ($url in $ArchiveUrls) {
        try {
            Write-Host "Downloading $url"
            if (Test-Path $Destination) { Remove-Item -Force $Destination }
            if (-not (Save-UrlToFile -Url $url -Destination $Destination)) { continue }
            if (Test-SevenZipSignature -Path $Destination) {
                Write-Host ("Archive size: {0:N0} bytes" -f (Get-Item $Destination).Length)
                return $true
            }
            Write-Warning "Downloaded file is not a 7z archive (SourceForge interstitial page?); trying next URL."
        } catch {
            Write-Warning "Download failed for ${url}: $($_.Exception.Message)"
        }
    }
    return $false
}

function Expand-Archive7z {
    param([string]$Archive, [string]$Destination)
    if (Test-Path $Destination) { Remove-Item -Recurse -Force $Destination }
    New-Item -ItemType Directory -Force -Path $Destination | Out-Null

    $tar = Get-Command tar -ErrorAction SilentlyContinue
    if ($tar) {
        try {
            Write-Host 'Extracting with tar (bsdtar/libarchive)...'
            & $tar.Source -xf $Archive -C $Destination
            if ($LASTEXITCODE -eq 0) {
                $found = Find-NgspiceExe -Root $Destination
                if ($found) { return $found }
            }
            Write-Warning "tar exited with code $LASTEXITCODE and produced no ngspice.exe; falling back to 7zr."
        } catch {
            Write-Warning "tar extraction failed: $($_.Exception.Message)"
        }
    }

    if (-not (Test-Path $SevenZiprPath)) {
        Write-Host "Downloading 7zr helper from $SevenZiprUrl"
        Invoke-WebRequest -Uri $SevenZiprUrl -OutFile $SevenZiprPath -UseBasicParsing
    }
    Write-Host 'Extracting with 7zr...'
    & $SevenZiprPath x $Archive "-o$Destination" -y | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "7zr extraction failed with exit code $LASTEXITCODE" }

    $found = Find-NgspiceExe -Root $Destination
    if (-not $found) { throw "ngspice.exe was not found under $Destination" }
    return $found
}

# --- already installed? -----------------------------------------------------
$installedExe = Find-NgspiceExe -Root $InstallRoot
if ($installedExe) {
    Write-Host "ngspice path: $($installedExe.FullName)"
    Write-Host 'Already installed; nothing to do.'
    exit 0
}

# --- download ---------------------------------------------------------------
New-Item -ItemType Directory -Force -Path $WorkDir | Out-Null
if (-not (Get-Archive -Destination $ArchivePath)) {
    throw "Could not download a valid $ArchiveName from SourceForge."
}
$hash = (Get-FileHash -Path $ArchivePath -Algorithm SHA256).Hash
Write-Host "Archive SHA256: $hash"

# --- extract ----------------------------------------------------------------
$exe = Expand-Archive7z -Archive $ArchivePath -Destination $ExtractDir
Write-Host "Extracted ngspice.exe: $($exe.FullName)"

# The archive keeps its own top-level directory; install that directory's
# contents at $InstallRoot so the layout stays self-contained.
$sourceRoot = if ($exe.Directory.Name -eq 'bin') { $exe.Directory.Parent.FullName } else { $exe.Directory.FullName }
Write-Host "Installing from: $sourceRoot"

New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null
Copy-Item -Path (Join-Path $sourceRoot '*') -Destination $InstallRoot -Recurse -Force

$finalExe = Find-NgspiceExe -Root $InstallRoot
if (-not $finalExe) { throw "Installation failed: ngspice.exe not present under $InstallRoot" }

Write-Host "ngspice path: $($finalExe.FullName)"
Write-Host "Set NGSPICE_BIN to that path, or leave it unset (the app also probes $InstallRoot)."
exit 0
