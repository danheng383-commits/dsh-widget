#requires -Version 5.1
<#
    uninstall-autostart.ps1 - stop the 大肥鱼 desktop widget from auto-starting.
    Removes the Startup shortcut created by install-autostart.ps1.
#>
param()

$ErrorActionPreference = 'Stop'
& (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) 'install-autostart.ps1') -Uninstall
