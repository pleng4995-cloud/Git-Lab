@echo off
setlocal

powershell -NoProfile -ExecutionPolicy Bypass -Command "$p=@(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -like '*bjt_bias.app*' }); if ($p.Count -eq 0) { Write-Host 'Nothing to stop.' } else { $p | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; Write-Host ('Stopped ' + $p.Count + ' server process(es).') }"

endlocal
