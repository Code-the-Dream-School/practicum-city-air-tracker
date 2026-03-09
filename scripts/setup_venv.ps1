$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Venv = Join-Path $Root ".venv"
$Requirements = Join-Path $Root "requirements.txt"

if (-not (Test-Path $Requirements)) {
    throw "requirements.txt not found in $Root"
}

Push-Location $Root
try {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $PythonCreateCmd = "py"
        $PythonCreateArgs = @("-3", "-m", "venv", ".venv")
    }
    elseif (Get-Command python -ErrorAction SilentlyContinue) {
        $PythonCreateCmd = "python"
        $PythonCreateArgs = @("-m", "venv", ".venv")
    }
    else {
        throw "Python launcher (py) or python not found. Install Python 3.11+ first."
    }

    if (-not (Test-Path $Venv)) {
        Write-Host "Creating virtual environment at $Venv"
        & $PythonCreateCmd @PythonCreateArgs
    }
    else {
        Write-Host "Virtual environment already exists at $Venv"
    }

    $VenvPython = Join-Path $Venv "Scripts\python.exe"
    if (-not (Test-Path $VenvPython)) {
        throw "Could not find $VenvPython"
    }

    & $VenvPython -m pip install --upgrade pip setuptools wheel
    & $VenvPython -m pip install -r requirements.txt

    Write-Host ""
    Write-Host "Setup complete."
    Write-Host "Activate with: .venv\Scripts\Activate.ps1"
    Write-Host "Run pipeline: python services/pipeline/run_pipeline.py --source openweather --history-hours 72"
    Write-Host "Run dashboard: streamlit run services/dashboard/app/Home.py"
}
finally {
    Pop-Location
}
