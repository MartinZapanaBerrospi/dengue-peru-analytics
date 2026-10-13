# Refresca todas las tablas del modelo abierto en Power BI Desktop (equivale a Inicio > Actualizar).
# Al reabrir un PBIP el modelo queda vacío: hay que refrescarlo antes de validar medidas o capturar páginas.
#
# Uso:  powershell -ExecutionPolicy Bypass -File tools\refrescar.ps1 -Puerto 54503
param([Parameter(Mandatory = $true)][int]$Puerto)

$dll = Get-ChildItem "C:\Program Files", "C:\Program Files (x86)" -Recurse -Filter "Microsoft.AnalysisServices.AdomdClient.dll" -ErrorAction SilentlyContinue |
    Select-Object -First 1 -ExpandProperty FullName
if (-not $dll) { throw "No se encontró Microsoft.AnalysisServices.AdomdClient.dll" }
try { Add-Type -Path $dll } catch { }

$conexion = New-Object Microsoft.AnalysisServices.AdomdClient.AdomdConnection("Data Source=localhost:$Puerto")
$conexion.Open()
$base = $conexion.Database
$comando = $conexion.CreateCommand()
$comando.CommandTimeout = 600
$comando.CommandText = '{"refresh":{"type":"full","objects":[{"database":"' + $base + '"}]}}'
[void]$comando.ExecuteNonQuery()
$conexion.Close()
Write-Output "Modelo refrescado ($base)"
