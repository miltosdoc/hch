Write-Output "--- Pulsus (port 8080) ---"
try { 
    $r = Invoke-WebRequest -Uri http://localhost:8080 -TimeoutSec 3 -UseBasicParsing
    Write-Output "UP - Status $($r.StatusCode)"
} catch { 
    Write-Output "DOWN" 
}
Write-Output ""
Write-Output "--- Integrationsportalen (port 5000) ---"
try { 
    $r = Invoke-WebRequest -Uri http://localhost:5000 -TimeoutSec 3 -UseBasicParsing
    Write-Output "UP - Status $($r.StatusCode)"
} catch { 
    Write-Output "DOWN" 
}
