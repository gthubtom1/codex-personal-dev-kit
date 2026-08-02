function Merge-CodexNativeAgentDefaults {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyString()]
        [string]$Content,
        [switch]$RemoveLegacyLunaDefault
    )

    $newline = if ($Content.Contains("`r`n")) { "`r`n" } else { "`n" }
    $lines = New-Object System.Collections.Generic.List[string]
    foreach ($line in ($Content -split "`r?`n")) {
        [void]$lines.Add($line)
    }
    while ($lines.Count -gt 0 -and [string]::IsNullOrWhiteSpace($lines[$lines.Count - 1])) {
        $lines.RemoveAt($lines.Count - 1)
    }

    $defaults = [ordered]@{
        "enabled" = "true"
        "max_concurrent_threads_per_session" = "6"
        "interrupt_message" = "true"
        "default_subagent_reasoning_effort" = '"max"'
    }

    $agentsStart = -1
    for ($index = 0; $index -lt $lines.Count; $index++) {
        if ($lines[$index] -match '^\s*\[agents\]\s*$') {
            $agentsStart = $index
            break
        }
    }

    if ($agentsStart -lt 0) {
        if ($lines.Count -gt 0) { [void]$lines.Add("") }
        [void]$lines.Add("[agents]")
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

    if ($RemoveLegacyLunaDefault) {
        $legacyPattern = '^\s*default_subagent_model\s*=\s*["'']gpt-5\.6-luna["'']\s*(?:#.*)?$'
        for ($index = $agentsEnd - 1; $index -gt $agentsStart; $index--) {
            if ($lines[$index] -match $legacyPattern) {
                $lines.RemoveAt($index)
                $agentsEnd--
            }
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

function Test-CodexLegacyLunaDefault {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyString()]
        [string]$Content
    )

    return [bool]($Content -match '(?m)^\s*default_subagent_model\s*=\s*["'']gpt-5\.6-luna["'']\s*(?:#.*)?$')
}
