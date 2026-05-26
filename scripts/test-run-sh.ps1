# 在 Windows 上粗测 run.sh（需已安装 Git Bash 或 WSL）
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

if (Get-Command bash -ErrorAction SilentlyContinue) {
  Write-Host "使用 Git Bash / WSL 执行 run.sh --help 语法检查..."
  bash -n run.sh
  if ($LASTEXITCODE -eq 0) { Write-Host "run.sh 语法 OK" }
  exit $LASTEXITCODE
}

Write-Host "未找到 bash。请安装 Git for Windows，或在 WSL 中执行: bash run.sh"
exit 1
