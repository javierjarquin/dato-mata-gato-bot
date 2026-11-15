<#
.SYNOPSIS
    Arranca el bot si no está corriendo. Idempotente: si ya está vivo, no hace
    nada. Pensado para que una tarea programada lo llame cada pocos minutos.

.DESCRIPTION
    Por qué una tarea y no un servicio de Windows (12/11/2026): un servicio
    corre en la sesión 0, y Docker Desktop -- donde vive VoiceStudio, que hace
    la voz -- corre entero en la sesión interactiva del usuario (su
    com.docker.service está detenido). Un bot en sesión 0 contestaría Telegram
    pero no podría generar un solo video. Las credenciales de Claude Code están
    en el perfil del usuario, con el mismo problema.

.PARAMETER Perfil
    El canal. Vacío = Dato Mata Gato (.env); "papasia" = el canal de papás
    primerizos (.env.papasia). Cada bot tiene sus comandos, su estado y su log
    (data\ y data\papasia\): ver src\dato_mata_gato_bot\canal.py.

.EXAMPLE
    .\tools\supervisar_bot.ps1 -Perfil papasia
#>

param([string]$Perfil = '')

$ErrorActionPreference = 'Stop'

$ProjectRoot = 'C:\dato-mata-gato-bot'
$PythonwExe = Join-Path $ProjectRoot '.venv\Scripts\pythonw.exe'
$Modulo = '-m dato_mata_gato_bot.bot'
$Argumentos = if ($Perfil) { "$Modulo --perfil $Perfil" } else { $Modulo }

if (-not (Test-Path $PythonwExe)) {
    Write-Error "No existe $PythonwExe"
    exit 1
}

# Los dos bots corren el MISMO módulo: lo que los distingue es --perfil. Sin
# mirar eso, el supervisor de papasia daría por vivo al bot de Dato Mata Gato
# (o al revés) y el canal se quedaría caído sin que nadie se entere.
$vivos = @(Get-CimInstance Win32_Process -Filter "Name like '%python%'" |
    Where-Object { $_.CommandLine -and $_.CommandLine -like '*dato_mata_gato_bot.bot*' } |
    Where-Object {
        if ($Perfil) { $_.CommandLine -like "*--perfil $Perfil*" }
        else { $_.CommandLine -notlike '*--perfil*' }
    })

$quien = if ($Perfil) { $Perfil } else { 'dato-mata-gato' }
if ($vivos.Count -gt 0) {
    Write-Output "$(Get-Date -Format 'u') [$quien] ya está vivo (PID $($vivos[0].ProcessId))"
    exit 0
}

Start-Process -FilePath $PythonwExe -ArgumentList $Argumentos `
    -WorkingDirectory $ProjectRoot -WindowStyle Hidden
Write-Output "$(Get-Date -Format 'u') [$quien] estaba caído: relanzado"
