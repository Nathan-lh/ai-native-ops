# 从文件读取 token，避免复制粘贴带入换行
$rawToken = @"
在这里粘贴你的完整token
"@

# 去掉所有换行、回车、空格、制表符
$token = $rawToken -replace '\s', ''

Write-Host "Token长度: $($token.Length)" -ForegroundColor Yellow

$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type"  = "application/json"
}
$body = '{"deviceId":1,"description":"test"}'

Write-Host "===== 测试 GET /api/auth/me =====" -ForegroundColor Cyan
try {
    $r = Invoke-RestMethod -Method Get -Uri "http://localhost:8080/api/auth/me" -Headers $headers
    $r | ConvertTo-Json
} catch {
    Write-Host "错误: $_" -ForegroundColor Red
}

Write-Host "`n===== 测试 POST /api/orders =====" -ForegroundColor Cyan
try {
    $r = Invoke-RestMethod -Method Post -Uri "http://localhost:8080/api/orders" -Headers $headers -Body $body
    $r | ConvertTo-Json
} catch {
    Write-Host "错误: $_" -ForegroundColor Red
}