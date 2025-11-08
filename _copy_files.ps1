# Copy files from Users → Engineering
$usrPath = "C:\Users\blyth\aegis"
$engPath = "C:\Users\blyth\Desktop\Engineering\aegis"
$listFile = "$engPath\_files_to_copy.txt"

Write-Output "=== COPYING FILES FROM USERS → ENGINEERING ==="

# Read the file list (skip header lines)
$filesToCopy = Get-Content $listFile | Select-Object -Skip 2 | Where-Object { $_.Trim() -ne '' }

$copied = 0
$failed = 0

foreach($relativePath in $filesToCopy) {
    $sourcePath = Join-Path $usrPath $relativePath
    $destPath = Join-Path $engPath $relativePath

    if(Test-Path $sourcePath) {
        # Create destination directory if it doesn't exist
        $destDir = Split-Path -Parent $destPath
        if(-not (Test-Path $destDir)) {
            New-Item -ItemType Directory -Path $destDir -Force | Out-Null
        }

        try {
            Copy-Item -Path $sourcePath -Destination $destPath -Force
            Write-Output "OK: $relativePath"
            $copied++
        } catch {
            Write-Output "FAILED: $relativePath - $($_.Exception.Message)"
            $failed++
        }
    } else {
        Write-Output "SOURCE MISSING: $relativePath"
        $failed++
    }
}

Write-Output "`n=== COPY SUMMARY ==="
Write-Output "Copied: $copied"
Write-Output "Failed: $failed"
