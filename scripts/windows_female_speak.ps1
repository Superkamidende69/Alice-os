[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Text,

    [Parameter(Mandatory = $true)]
    [string]$Output,

    [ValidateRange(0.7, 1.3)]
    [double]$Speed = 1.0
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Speech

$outputPath = [System.IO.Path]::GetFullPath($Output)
$outputDirectory = [System.IO.Path]::GetDirectoryName($outputPath)
[System.IO.Directory]::CreateDirectory($outputDirectory) | Out-Null

$synthesizer = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $voiceNames = @($synthesizer.GetInstalledVoices() | Where-Object { $_.Enabled -and $_.VoiceInfo.Gender -eq "Female" } | ForEach-Object { $_.VoiceInfo.Name })
    $zira = $voiceNames | Where-Object { $_ -match "Zira" } | Select-Object -First 1
    if ($zira) {
        $synthesizer.SelectVoice($zira)
    }
    elseif ($voiceNames) {
        $synthesizer.SelectVoice($voiceNames[0])
    }
    else {
        throw "No enabled Windows female speech voice was found. Install a female English voice in Windows Settings."
    }
    $synthesizer.Rate = [Math]::Max(-10, [Math]::Min(10, [int][Math]::Round(($Speed - 1.0) * 10)))
    $synthesizer.SetOutputToWaveFile($outputPath)
    $synthesizer.Speak($Text)
}
finally {
    $synthesizer.Dispose()
}
