# Lote de /lotefish3 de punta a punta, como proceso independiente: escribe (o
# completa) los guiones, genera los videos y los manda por Telegram uno por uno.
#
# Existe porque las tareas que lanza una sesión de Claude Code tienen límite de
# tiempo, y un lote son horas: el 03/10/2026 el primero se cortó a mitad de los
# guiones. Lanzarlo así no depende de ninguna sesión:
#
#   Start-Process powershell -WindowStyle Hidden -ArgumentList `
#     '-NoProfile','-File','C:\dato-mata-gato-bot\tools\correr_lote_fish3.ps1','5','completar'
#
# Log en data\lote_fish3_<fecha>.log.
param([int]$Cantidad = 5, [string]$Modo = "")

$bot = "C:\dato-mata-gato-bot"
$py = "$bot\.venv\Scripts\python.exe"
$fecha = Get-Date -Format "yyyy-MM-dd"
$log = "$bot\data\lote_fish3_$fecha.log"
$env:PYTHONIOENCODING = "utf-8"
Set-Location $bot

function Escribir($texto) { "[$(Get-Date -Format HH:mm:ss)] $texto" | Out-File $log -Append -Encoding utf8 }

Escribir "=== lote de $Cantidad ($Modo) ==="
$argsGuiones = @("tools\lote_fish3.py", "$Cantidad")
if ($Modo -eq "completar") { $argsGuiones += "--completar" }
& $py @argsGuiones *>> $log

$pendientes = & $py -c "from dato_mata_gato_bot import sessions; print(len(sessions.get_pending_batch(7304450202)))"
Escribir "guiones en el lote: $pendientes"
if ([int]$pendientes -eq 0) { Escribir "nada que generar"; exit 1 }

# El vigilante corre en paralelo y manda cada video en cuanto aparece.
$vigilante = Start-Process $py -ArgumentList "C:\clip_assistance\tools\vigilar_lote_telegram.py",
    "C:\Android_in\lotes\$fecha", "$pendientes", "12" -WindowStyle Hidden -PassThru
Escribir "vigilante PID $($vigilante.Id)"

& $py tools\retomar_lote.py *>> $log
Escribir "=== fin ==="
