param (
    [string]$base64FilePath,      # Path to the Base64 encoded input file
    [string]$outputFilePath,      # Path to save the decompressed output
    [string]$key                  # XOR key (string)
)

# Function to XOR encrypt/decrypt data
function XOR-EncryptDecrypt {
    param (
        [byte[]]$data,
        [string]$key
    )
    $keyBytes = [System.Text.Encoding]::UTF8.GetBytes($key)
    $output = New-Object byte[] $data.Length

    for ($i = 0; $i -lt $data.Length; $i++) {
        $output[$i] = $data[$i] -bxor $keyBytes[$i % $keyBytes.Length]
    }
    return $output
}

# Step 1: Check if the Base64 file exists
if (-Not (Test-Path $base64FilePath)) {
    Write-Host "Base64 file does not exist: $base64FilePath"
    exit
}

# Step 2: Read the Base64 string from the file
$base64String = Get-Content -Path $base64FilePath -Raw

# Step 3: Decode the Base64 string
$encryptedData = [System.Convert]::FromBase64String($base64String)

# Step 4: Decrypt the Gzip data using XOR
$gzipData = XOR-EncryptDecrypt -data $encryptedData -key $key

# Step 5: Save the decrypted Gzip data to a temporary file
$tempGzipFilePath = [System.IO.Path]::GetTempFileName() + ".gz"
[System.IO.File]::WriteAllBytes($tempGzipFilePath, $gzipData)

# Step 6: Decompress the Gzip data
$gzipStream = [System.IO.Compression.GzipStream]::new(
    [System.IO.File]::OpenRead($tempGzipFilePath),
    [System.IO.Compression.CompressionMode]::Decompress
)

# Create the output file
$outputFileStream = [System.IO.File]::Create($outputFilePath)

try {
    # Initialize the buffer for decompression
    $buffer = New-Object byte[] 4096
    $bytesRead = 0

    while (($bytesRead = $gzipStream.Read($buffer, 0, $buffer.Length)) -gt 0) {
        $outputFileStream.Write($buffer, 0, $bytesRead)
    }
} finally {
    $gzipStream.Close()
    $outputFileStream.Close()
}

# Clean up the temporary Gzip file
Remove-Item $tempGzipFilePath -Force

Write-Host "Decoding, decryption, and decompression complete. Output file: $outputFilePath"
