# Full tree diff and classification script
$engPath = "C:\Users\blyth\Desktop\Engineering\aegis"
$usrPath = "C:\Users\blyth\aegis"

Write-Output "=== COLLECTING FILE TREES ==="

# Get all files from both repos (excluding .git, __pycache__, .pytest_cache)
$engFiles = Get-ChildItem -Path $engPath -Recurse -File |
    Where-Object { $_.FullName -notmatch '\\\.git\\|\\__pycache__\\|\\\.pytest_cache\\|_local_|_users_|_tree_|_hash_|_check_|_merge_|_origin_' } |
    ForEach-Object { $_.FullName.Replace($engPath + '\', '') }

$usrFiles = Get-ChildItem -Path $usrPath -Recurse -File |
    Where-Object { $_.FullName -notmatch '\\\.git\\|\\__pycache__\\|\\\.pytest_cache\\' } |
    ForEach-Object { $_.FullName.Replace($usrPath + '\', '') }

Write-Output "`nEngineering files: $($engFiles.Count)"
Write-Output "Users files: $($usrFiles.Count)"

# Convert to hash sets for comparison
$engSet = New-Object System.Collections.Generic.HashSet[string]
$usrSet = New-Object System.Collections.Generic.HashSet[string]

foreach($f in $engFiles) { [void]$engSet.Add($f) }
foreach($f in $usrFiles) { [void]$usrSet.Add($f) }

# Classify files
$onlyEng = New-Object System.Collections.ArrayList
$onlyUsr = New-Object System.Collections.ArrayList
$inBoth = New-Object System.Collections.ArrayList

foreach($f in $engSet) {
    if(-not $usrSet.Contains($f)) {
        [void]$onlyEng.Add($f)
    } else {
        [void]$inBoth.Add($f)
    }
}

foreach($f in $usrSet) {
    if(-not $engSet.Contains($f)) {
        [void]$onlyUsr.Add($f)
    }
}

Write-Output "`n=== FILE CLASSIFICATION ==="
Write-Output "A) Only in Engineering: $($onlyEng.Count)"
Write-Output "B) Only in Users: $($onlyUsr.Count)"
Write-Output "C) In both (need hash check): $($inBoth.Count)"

# Output lists
Write-Output "`n=== A) FILES ONLY IN ENGINEERING (KEEP) ===" | Out-File -FilePath "$engPath\_merge_class_A.txt" -Encoding utf8
$onlyEng | Sort-Object | Out-File -FilePath "$engPath\_merge_class_A.txt" -Append -Encoding utf8

Write-Output "`n=== B) FILES ONLY IN USERS (COPY TO ENG) ===" | Out-File -FilePath "$engPath\_merge_class_B.txt" -Encoding utf8
$onlyUsr | Sort-Object | Out-File -FilePath "$engPath\_merge_class_B.txt" -Append -Encoding utf8

Write-Output "`n=== C) FILES IN BOTH (HASH CHECK NEEDED) ===" | Out-File -FilePath "$engPath\_merge_class_C.txt" -Encoding utf8
$inBoth | Sort-Object | Out-File -FilePath "$engPath\_merge_class_C.txt" -Append -Encoding utf8

# Hash comparison for files in both
Write-Output "`n=== HASH COMPARISON FOR COMMON FILES ==="
$different = 0
$identical = 0

foreach($f in $inBoth) {
    $engFile = Join-Path $engPath $f
    $usrFile = Join-Path $usrPath $f

    if((Test-Path $engFile) -and (Test-Path $usrFile)) {
        $engHash = (Get-FileHash $engFile).Hash
        $usrHash = (Get-FileHash $usrFile).Hash

        if($engHash -ne $usrHash) {
            Write-Output "DIFF: $f" | Out-File -FilePath "$engPath\_merge_class_C_diff.txt" -Append -Encoding utf8
            $different++
        } else {
            $identical++
        }
    }
}

Write-Output "`nIdentical files: $identical"
Write-Output "Different files: $different"
Write-Output "`nResults written to _merge_class_*.txt files"
