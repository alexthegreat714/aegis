# Identify critical files that need to be copied from Users to Engineering
$usrPath = "C:\Users\blyth\aegis"
$engPath = "C:\Users\blyth\Desktop\Engineering\aegis"

# Critical file patterns to copy (exclude .venv, RAG, __pycache__, .git)
$criticalPatterns = @(
    'src\*.py',
    'src\**\*.py',
    'tests\*.py',
    'tests\**\*.py',
    'config\*.yaml',
    'config\*.json',
    'config\.owui_token.example',
    'data\.gitignore',
    '*.bat',
    '*.md',
    'sandbox\**',
    'requirements.txt',
    '.gitignore'
)

$excludePatterns = @(
    '.venv',
    'RAG',
    '__pycache__',
    '.git',
    '.pytest_cache',
    '*.db',
    '.bak',
    '_local_',
    '_users_',
    '_tree_',
    '_hash_',
    '_check_',
    '_merge_',
    '_origin_',
    '.claude'
)

Write-Output "=== IDENTIFYING CRITICAL FILES TO COPY ==="

# Get all files from Users that match critical patterns
$filesToCopy = Get-ChildItem -Path $usrPath -Recurse -File |
    Where-Object {
        $file = $_
        $relativePath = $file.FullName.Replace($usrPath + '\', '')

        # Check if matches any exclude pattern
        $excluded = $false
        foreach($pattern in $excludePatterns) {
            if($relativePath -match $pattern) {
                $excluded = $true
                break
            }
        }

        -not $excluded
    }

Write-Output "Total files in Users (filtered): $($filesToCopy.Count)"

# Check which don't exist in Engineering
$needsCopy = New-Object System.Collections.ArrayList

foreach($file in $filesToCopy) {
    $relativePath = $file.FullName.Replace($usrPath + '\', '')
    $engFile = Join-Path $engPath $relativePath

    if(-not (Test-Path $engFile)) {
        [void]$needsCopy.Add($relativePath)
    }
}

Write-Output "Files needing copy: $($needsCopy.Count)"
Write-Output "`n=== FILES TO COPY FROM USERS → ENGINEERING ===" | Out-File -FilePath "$engPath\_files_to_copy.txt" -Encoding utf8
$needsCopy | Sort-Object | Out-File -FilePath "$engPath\_files_to_copy.txt" -Append -Encoding utf8

Write-Output "`nList saved to _files_to_copy.txt"
