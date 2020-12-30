$GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"
$GET_PIP_PATH = "C:\get-pip.py"

function InstallPip ($python_home) {
    $pip_path = $python_home + "/Scripts/pip.exe"
    $python_path = $python_home + "/python.exe"
    if (-not (Test-Path $pip_path)) {
        Write-Host "Installing pip..."
        if (-not (Test-Path $GET_PIP_PATH)) {
            $webclient = New-Object System.Net.WebClient
            $webclient.DownloadFile($GET_PIP_URL, $GET_PIP_PATH)
        }
        Write-Host "Executing:" $python_path $GET_PIP_PATH
        Start-Process -FilePath "$python_path" -ArgumentList "$GET_PIP_PATH" -Wait
    } else {
        Write-Host "pip already installed."
    }
}

InstallPip $env:PYTHON

# Install the dev requirements (we only need some of these, but don't
# worry about that for now)
& ($env:PYTHON + "/Scripts/pip.exe") install -r dev-requirements.txt
