This PowerShell script performs the following tasks:

1. **Encryption, Compression, and Encoding to Base64**:
   - **Input**: A binary file and a secret key.
   - **Process**:
     - Compresses the binary file using Gzip.
     - Encrypts the compressed data using XOR encryption with the provided key.
     - Converts the encrypted data to a Base64 string.
   - **Output**: Saves the Base64 encoded result to a specified output file.

2. **Decoding from Base64, Decryption, and Decompression**:
   - **Input**: A Base64 encoded file and the same secret key.
   - **Process**:
     - Decodes the Base64 string to retrieve the encrypted data.
     - Decrypts the data using XOR decryption with the provided key (reverses encryption).
     - Decompresses the decrypted data from Gzip format to recover the original binary file.
   - **Output**: Saves the original binary file to a specified output file.

The XOR encryption here is basic and mainly for obfuscation, rather than robust security. The key must be kept secret to prevent unauthorized decryption.

    .\EncryptCompressEncode.ps1 -inputFilePath "C:\OffensiveToolz\SharpCollection\NetFramework_4.0_Any\SharpKatz.exe" -outputFilePath "outputfile.b64" -key "your_secret_key"
    
    .\DecryptDecompressDecode.ps1 -base64FilePath "outputfile.b64" -outputFilePath "SharpKatz.exe" -key "your_secret_key"
