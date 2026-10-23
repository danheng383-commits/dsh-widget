#requires -Version 5.1
<#
    install-autostart.ps1 - start the 大肥鱼 desktop widget at every login.

    Creates a shortcut in the current user's Startup folder:
      %APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\大肥鱼桌面挂件.lnk
    pointing at desktop\launch-widget.vbs (silent launcher, no console window).

    Run with -Uninstall to remove it. No administrator rights are required.
#>
param([switch]$Uninstall)

$ErrorActionPreference = 'Stop'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$launcher = Join-Path $scriptDir 'launch-widget.vbs'
$startup = [Environment]::GetFolderPath('Startup')
$shortcutPath = Join-Path $startup 'FatFishDesktop.lnk'

if ($Uninstall) {
    if (Test-Path -LiteralPath $shortcutPath) {
        Remove-Item -LiteralPath $shortcutPath -Force
        Write-Output "removed: $shortcutPath"
    } else {
        Write-Output "not installed: $shortcutPath"
    }
    exit 0
}

if (-not (Test-Path -LiteralPath $launcher)) {
    throw "launcher not found: $launcher"
}
if (-not (Test-Path -LiteralPath $startup)) {
    New-Item -ItemType Directory -Path $startup -Force | Out-Null
}

$wsh = New-Object -ComObject WScript.Shell
$link = $wsh.CreateShortcut($shortcutPath)
$link.TargetPath = Join-Path $env:SystemRoot 'System32\wscript.exe'
$link.Arguments = '"' + $launcher + '"'
$link.WorkingDirectory = $scriptDir
$link.Description = 'Fat fish desktop progress widget'
$link.Save()
Write-Output "installed: $shortcutPath"
Write-Output 'The widget will start automatically at the next login. Start it now with launch-widget.vbs.'
