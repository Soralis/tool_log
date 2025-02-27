# Define the network range to scan
$network = "10.0.36"
$startIP = 1
$endIP = 254
$port = 22
$timeout = 100

Write-Host "Scanning network $network.0/24 for Raspberry Pis with open SSH port..."
Write-Host "This may take a few minutes..."

# Create array to store results
$results = @()

# Scan IP range
foreach ($i in $startIP..$endIP) {
    $ip = "$network.$i"
    
    # Try to connect to SSH port
    $tcpClient = New-Object System.Net.Sockets.TcpClient
    $asyncResult = $tcpClient.BeginConnect($ip, $port, $null, $null)
    $wait = $asyncResult.AsyncWaitHandle.WaitOne($timeout)

    if ($wait) {
        try {
            $tcpClient.EndConnect($asyncResult)
            $results += $ip
            Write-Host "Found potential Raspberry Pi at $ip" -ForegroundColor Green
        } catch {}
        $tcpClient.Close()
    }
}

if ($results.Count -eq 0) {
    Write-Host "No devices with open SSH port found." -ForegroundColor Yellow
} else {
    Write-Host "`nFound $($results.Count) device(s) with open SSH port:"
    $results | ForEach-Object { Write-Host $_ }
}

Read-Host -Prompt "Press Enter to exit"
