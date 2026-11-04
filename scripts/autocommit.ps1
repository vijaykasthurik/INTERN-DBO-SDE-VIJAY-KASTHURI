param([int]$Interval = 1800)

$ErrorActionPreference = "Stop"
while ($true) {
    Start-Sleep -Seconds $Interval
    $branch = (git branch --show-current).Trim()
    if ($branch -ne "main") {
        Write-Warning "[autocommit] Refusing to commit outside main."
        continue
    }
    git add -A
    if (-not (git diff --cached --quiet)) {
        $paths = git diff --cached --name-only
        $forbidden = $paths | Where-Object { $_ -match '(^|/)(\.env($|\.)|node_modules/|\.venv/|venv/|dist/|build/)' -or $_ -match '^(data|backend/data|frontend/data)/' }
        $staged = git diff --cached --no-ext-diff --unified=0
        $secretPattern = '(?i)(sk-[a-z0-9]{32,}|ghp_[a-z0-9]{36}|AIzaSy[a-z0-9_-]{33}|-----BEGIN [A-Z ]*PRIVATE KEY-----)'
        if ($forbidden -or $staged -match $secretPattern) {
            Write-Warning "[autocommit] Refusing checkpoint: protected paths or secret-like content detected."
            continue
        }
        $timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        git commit -m "chore(auto): checkpoint $timestamp"
        if ($LASTEXITCODE -eq 0) { git push origin main }
    }
}
