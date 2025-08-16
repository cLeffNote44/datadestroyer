Param(
  [string]$CertPath = "./nginx/certs",
  [string]$CN = "localhost"
)

New-Item -ItemType Directory -Force -Path $CertPath | Out-Null
$crt = Join-Path $CertPath "dev.crt"
$key = Join-Path $CertPath "dev.key"

if (Get-Command openssl -ErrorAction SilentlyContinue) {
  openssl req -x509 -nodes -newkey rsa:2048 -days 365 `
    -keyout $key -out $crt `
    -subj "/C=US/ST=NA/L=Local/O=Dev/OU=Dev/CN=$CN"
  Write-Host "Generated self-signed cert at $crt and key at $key"
} else {
  Write-Error "OpenSSL not found. Please install OpenSSL or generate a certificate manually."
}
