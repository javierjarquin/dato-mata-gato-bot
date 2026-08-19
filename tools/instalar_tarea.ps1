<#
.SYNOPSIS
    Registra dato-mata-gato-bot para que arranque solo al iniciar sesion de
    Windows, via un acceso directo en la carpeta de Inicio (no requiere
    permisos de administrador).

.EXAMPLE
    .\tools\instalar_tarea.ps1
#>

$ErrorActionPreference = 'Stop'

$ProjectRoot = 'C:\dato-mata-gato-bot'
$PythonwExe  = Join-Path $ProjectRoot '.venv\Scripts\pythonw.exe'

if (-not (Test-Path $PythonwExe)) {
    Write-Error "No existe $PythonwExe -- corre 'python -m venv .venv' e instala las dependencias primero."
    exit 1
}

$startup = [Environment]::GetFolderPath('Startup')
$shortcutPath = Join-Path $startup 'DatoMataGatoBot.lnk'

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $PythonwExe
$shortcut.Arguments = '-m dato_mata_gato_bot.bot'
$shortcut.WorkingDirectory = $ProjectRoot
$shortcut.Description = 'Bot de Telegram para el pipeline de Dato Mata Gato'
$shortcut.Save()

Write-Output "Acceso directo creado en: $shortcutPath"
Write-Output "Arrancará solo la próxima vez que inicies sesión en Windows."
Write-Output "Para arrancarlo ahora sin reiniciar sesión:"
Write-Output "  Start-Process -FilePath '$PythonwExe' -ArgumentList '-m dato_mata_gato_bot.bot' -WorkingDirectory '$ProjectRoot'"
