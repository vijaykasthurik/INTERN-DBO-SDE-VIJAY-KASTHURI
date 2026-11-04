# Autocommit daemon for Lumen (PowerShell / Windows)
param(
    [int]$Interval = 1800
)

Write-Host "Starting Lumen autocommit loop (interval: ${Interval}s)..."

while ($true) {
    Start-Sleep -Seconds $Interval

    $status = git status --porcelain
    if ($status) {
        # Secret scan check
        $diff = git diff HEAD
        if ($diff -match '(sk-[a-zA-Z0-9]{32,}|ghp_[a-zA-Z0-9]{36}|AIzaSy[a-zA-Z0-9_-]{33})') {
            Write-Warning "[autocommit] Potential API secret pattern detected in git diff! Commit cancelled."
            continue
        }

        $timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        Write-Host "[autocommit] [$timestamp] Committing checkpoint..."
        git add -A
        git commit -m "chore(auto): checkpoint $timestamp"
        git push origin main
    } else {
        $timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        Write-Host "[autocommit] [$timestamp] No changes detected."
    }
}
