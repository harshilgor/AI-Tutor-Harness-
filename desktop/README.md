# Forma Desktop

This is the desktop shell for the existing Forma web interface and FastAPI learning service. It starts the local API sidecar, serves the built web UI through a loopback server, and runs the renderer with Electron isolation enabled.

## Development

From the repository root, start the web interface first:

```powershell
./start-local.ps1
```

Then, from `desktop/`, install the desktop dependencies and run:

```powershell
npm install
npm run dev
```

The shell uses the existing API on `127.0.0.1:8000` and opens the web interface on `127.0.0.1:3000`. Set `FORMA_WEB_URL` or `FORMA_API_PORT` when using different local ports.

GitHub Actions builds unsigned Windows and macOS artifacts for pull requests. The `v0.1.0-beta` release workflow builds signed Windows x64, macOS Intel, and macOS Apple Silicon artifacts only after all signing and notarization secrets are available. See [the release runbook](../docs/RELEASING.md) before creating that tag.

To build the sidecar locally after installing the backend requirements:

```powershell
python -m pip install -r ../backend/requirements.txt
npm run build:backend
```

The generated `backend/dist/forma-api/` directory is platform-specific and must be built on the target operating system. GitHub Actions performs this matrix build for releases.

Validate the bundled Windows sidecar against a fresh application-data directory, then restart it against the same directory:

```powershell
./scripts/smoke-local-runtime.ps1
```

The smoke test deliberately keeps the installation directory and application-data directory separate. An uninstall is expected to remove the application while preserving learner data for a later reinstall; users can delete that data from **Your workspace**.

The desktop sidebar's **Your workspace** panel configures provider keys through the OS credential store and exposes local data export/deletion. The application menu includes the same local-data settings entry.
