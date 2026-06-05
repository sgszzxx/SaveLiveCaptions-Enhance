# SaveLiveCaptions Enhanced

An enhanced Windows tool for saving Windows Live Captions text.

This project is based on [LiveCaptionsHelper/SaveLiveCaptions](https://github.com/LiveCaptionsHelper/SaveLiveCaptions) and follows the original MIT License.

## Features

* Cleaner and more modern UI
* Light and dark theme support
* Minimize to system tray
* Normal exit button
* Window position memory
* Auto-start save flow
* Custom application icon
* Single-file Windows executable build

## Download

Go to the **Releases** page and download:

```text
SaveLiveCaptions-v1.0.0-windows.exe
```

## How to use

1. Open Windows Live Captions first.
2. Run `SaveLiveCaptions-v1.0.0-windows.exe`.
3. Choose a save location.
4. The app will start saving captions automatically.
5. Use the tray icon to restore or exit the app.

## Build from source

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Run from source:

```powershell
python src\main.py
```

Build single-file Windows executable:

```powershell
pyinstaller --noconfirm --clean --windowed --onefile --name SaveLiveCaptions --icon ass
```
