function Invoke-SharpUp
{

    [CmdletBinding()]
    Param (
        [String]
        $Command = ""

    )

    $a=New-Object IO.MemoryStream(,[Convert]::FromBAsE64String("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"))
    $decompressed = New-Object IO.Compression.GzipStream($a,[IO.Compression.CoMPressionMode]::DEComPress)
    $output = New-Object System.IO.MemoryStream
    $decompressed.CopyTo( $output )
    [byte[]] $byteOutArray = $output.ToArray()
    $RAS = [System.Reflection.Assembly]::Load($byteOutArray)

    $OldConsoleOut = [Console]::Out
    $StringWriter = New-Object IO.StringWriter
    [Console]::SetOut($StringWriter)

    [UpSharp.Program]::main($Command.Split(" "))

    [Console]::SetOut($OldConsoleOut)
    $Results = $StringWriter.ToString()
    $Results
  
}