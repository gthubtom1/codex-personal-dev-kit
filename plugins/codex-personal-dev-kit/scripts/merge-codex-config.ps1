function Merge-CodexProjectDefaults {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyString()]
        [string]$Content
    )

    $newline = if ($Content.Contains("`r`n")) { "`r`n" } else { "`n" }
    $lines = New-Object System.Collections.Generic.List[string]
    foreach ($line in ($Content -split "`r?`n")) {
        [void]$lines.Add($line)
    }
    while ($lines.Count -gt 0 -and [string]::IsNullOrWhiteSpace($lines[$lines.Count - 1])) {
        $lines.RemoveAt($lines.Count - 1)
    }

    $defaults = [ordered]@{ "goals" = "true" }

    $agentsStart = -1
    for ($index = 0; $index -lt $lines.Count; $index++) {
        if ($lines[$index] -match '^\s*\[features\]\s*$') {
            $agentsStart = $index
            break
        }
    }

    if ($agentsStart -lt 0) {
        if ($lines.Count -gt 0) { [void]$lines.Add("") }
        [void]$lines.Add("[features]")
        foreach ($entry in $defaults.GetEnumerator()) {
            [void]$lines.Add("$($entry.Key) = $($entry.Value)")
        }
        return (($lines -join $newline) + $newline)
    }

    $agentsEnd = $lines.Count
    for ($index = $agentsStart + 1; $index -lt $lines.Count; $index++) {
        if ($lines[$index] -match '^\s*\[[^\]]+\]\s*$') {
            $agentsEnd = $index
            break
        }
    }

    foreach ($entry in $defaults.GetEnumerator()) {
        $keyPattern = '^\s*' + [regex]::Escape($entry.Key) + '\s*='
        $found = $false
        for ($index = $agentsStart + 1; $index -lt $agentsEnd; $index++) {
            if ($lines[$index] -match $keyPattern) {
                $found = $true
            }
        }
        if (-not $found) {
            $lines.Insert($agentsEnd, "$($entry.Key) = $($entry.Value)")
            $agentsEnd++
        }
    }

    return (($lines -join $newline) + $newline)
}
