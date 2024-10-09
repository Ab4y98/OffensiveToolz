param (
    [string]$inputFilePath,      # Path to the binary file to encrypt, compress, and encode
    [string]$outputFilePath,     # Path to save the Base64 encoded output
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

# Step 1: Compress the binary file to Gzip
$gzipFilePath = [System.IO.Path]::GetTempFileName() + ".gz"  # Create a temporary Gzip file

$inputFileStream = [System.IO.File]::OpenRead($inputFilePath)
$gzipStream = [System.IO.Compression.GzipStream]::new(
    [System.IO.File]::Create($gzipFilePath),
    [System.IO.Compression.CompressionMode]::Compress
)

try {
    # Read input file and write to Gzip stream
    $buffer = New-Object byte[] 4096
    $bytesRead = 0

    while (($bytesRead = $inputFileStream.Read($buffer, 0, $buffer.Length)) -gt 0) {
        $gzipStream.Write($buffer, 0, $bytesRead)
    }
} finally {
    $gzipStream.Close()
    $inputFileStream.Close()
}

# Step 2: Read the Gzip file and encrypt the data using XOR
$gzipData = [System.IO.File]::ReadAllBytes($gzipFilePath)
$encryptedData = XOR-EncryptDecrypt -data $gzipData -key $key

# Step 3: Encode the encrypted data to Base64
$base64String = [System.Convert]::ToBase64String($encryptedData)

# Step 4: Save the Base64 string to the output file
try {
    [System.IO.File]::WriteAllText($outputFilePath, $base64String)
    Write-Host "Encryption, compression, and Base64 encoding complete. Output file: $outputFilePath"
} catch {
    Write-Host "Error writing output file: $_"
}

# Clean up the temporary Gzip file
Remove-Item $gzipFilePath -Force
