Add-Type -AssemblyName System.Web

$pdfFolder = "\\SU323482005SA\PDF export"
$port = 8085
$htmlPath = Join-Path $PSScriptRoot "index.html"

$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add("http://localhost:$port/")

try {
    $listener.Start()
    Start-Process "http://localhost:$port"
    
    while ($listener.IsListening) {
        $context = $listener.GetContext()
        $request = $context.Request
        $response = $context.Response
        
        $path = $request.Url.LocalPath
        
        try {
            # Basic Auth Check for API routes
            if ($path -match "^/api/(files|pdf)") {
                $hasAuth = $false
                if ($request.Cookies["PulsusAuth"] -ne $null -and $request.Cookies["PulsusAuth"].Value -eq "true") {
                    $hasAuth = $true
                }
                if (-not $hasAuth) {
                    $response.StatusCode = 401
                    # Skip the rest of the block and let the finally block close the output stream
                    continue
                }
            }

            if ($path -eq "/" -or $path -eq "/index.html") {
                $content = [System.IO.File]::ReadAllBytes($htmlPath)
                $response.ContentType = "text/html; charset=utf-8"
                $response.ContentLength64 = $content.Length
                $response.OutputStream.Write($content, 0, $content.Length)
            }
            elseif ($path -match "^/(logo\.png|logo\.svg|logoofficial\.png)$") {
                $fileName = $matches[1]
                $filePath = Join-Path $PSScriptRoot $fileName
                if (Test-Path -LiteralPath $filePath) {
                    $content = [System.IO.File]::ReadAllBytes($filePath)
                    if ($fileName -match "\.png$") { $response.ContentType = "image/png" }
                    else { $response.ContentType = "image/svg+xml" }
                    $response.ContentLength64 = $content.Length
                    $response.OutputStream.Write($content, 0, $content.Length)
                } else {
                    $response.StatusCode = 404
                }
            }
            elseif ($path -eq "/api/files") {
                $files = Get-ChildItem -Path $pdfFolder -Filter "*.pdf" -ErrorAction Stop | Sort-Object LastWriteTime -Descending | ForEach-Object {
                    @{
                        name = $_.Name
                        size = $_.Length
                        modified = $_.LastWriteTime.ToString("yyyy-MM-dd HH:mm")
                    }
                }
                $json = $files | ConvertTo-Json -Compress
                if ($null -eq $json -or $json -eq "") { $json = "[]" }
                $content = [System.Text.Encoding]::UTF8.GetBytes($json)
                $response.ContentType = "application/json"
                $response.ContentLength64 = $content.Length
                $response.OutputStream.Write($content, 0, $content.Length)
            }
            elseif ($path -eq "/api/login" -and $request.HttpMethod -eq "POST") {
                $encoding = $request.ContentEncoding
                if ($null -eq $encoding) { $encoding = [System.Text.Encoding]::UTF8 }
                $reader = New-Object System.IO.StreamReader($request.InputStream, $encoding)
                $body = $reader.ReadToEnd()
                $jsonBody = $body | ConvertFrom-Json
                
                $response.ContentType = "application/json"
                
                if ($jsonBody.username -eq "admin" -and $jsonBody.password -eq "123456") {
                    $cookie = New-Object System.Net.Cookie("PulsusAuth", "true")
                    $cookie.Path = "/"
                    $response.Cookies.Add($cookie)
                    
                    $resJson = @{ success = $true } | ConvertTo-Json
                    $content = [System.Text.Encoding]::UTF8.GetBytes($resJson)
                    $response.ContentLength64 = $content.Length
                    $response.OutputStream.Write($content, 0, $content.Length)
                } else {
                    $response.StatusCode = 401
                    $resJson = @{ success = $false; message = "Invalid credentials" } | ConvertTo-Json
                    $content = [System.Text.Encoding]::UTF8.GetBytes($resJson)
                    $response.ContentLength64 = $content.Length
                    $response.OutputStream.Write($content, 0, $content.Length)
                }
            }
            elseif ($path -eq "/api/pdf") {
                # Get filename from raw URL to properly decode UTF-8 characters like ö
                $rawUrl = $request.RawUrl
                $qsIndex = $rawUrl.IndexOf("?name=")
                if ($qsIndex -ge 0) {
                    $rawName = $rawUrl.Substring($qsIndex + 6)
                    $fileName = [uri]::UnescapeDataString($rawName)
                } else {
                    $fileName = $null
                }
                
                if (-not $fileName) {
                    $response.StatusCode = 400
                    $msg = [System.Text.Encoding]::UTF8.GetBytes("Missing 'name' parameter")
                    $response.OutputStream.Write($msg, 0, $msg.Length)
                    continue
                }
                $filePath = Join-Path $pdfFolder $fileName
                
                
                
                if (Test-Path -LiteralPath $filePath) {
                    $content = [System.IO.File]::ReadAllBytes($filePath)
                    $response.ContentType = "application/pdf"
                    $response.AddHeader("Content-Disposition", "inline; filename=`"$fileName`"")
                    $response.ContentLength64 = $content.Length
                    $response.OutputStream.Write($content, 0, $content.Length)
                } else {
                    $response.StatusCode = 404
                    $msg = [System.Text.Encoding]::UTF8.GetBytes("File not found: $fileName")
                    $response.OutputStream.Write($msg, 0, $msg.Length)
                }
            }
            else {
                $response.StatusCode = 404
            }
        }
        catch {
            $response.StatusCode = 500
        }
        finally {
            $response.OutputStream.Close()
        }
    }
}
catch {
    # Server error - silently exit
}
finally {
    $listener.Stop()
}
