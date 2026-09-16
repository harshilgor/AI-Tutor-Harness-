# Installing Forma Desktop

The desktop installer is published from the repository's GitHub Releases page. Download the installer for your operating system from the release marked **Latest** and read the matching entry in [the changelog](../CHANGELOG.md).

## Windows

Download the Windows installer, run it, and launch Forma from the Start menu. The app starts its local learning service automatically. Until code signing is configured, Windows may show a publisher warning; only install an installer downloaded from this repository's GitHub Release.

## macOS

Download the installer for Apple Silicon or Intel, open it, and drag Forma to Applications. macOS signing and notarization are required before public macOS releases are published.

## Development install

Contributors can run the existing local services and desktop shell from a checkout:

```powershell
./start-local.ps1
cd desktop
npm install
npm run dev
```

The development shell uses the local API on `127.0.0.1:8000` and the web interface on `127.0.0.1:3000`. User-facing releases will bundle both services and will not require Python, Node, Git, or a terminal.

## Local data

Learner data is stored in the operating system's Forma application-data directory. Provider keys are stored using the operating system's encrypted credential facility. Open **Your workspace** in the desktop sidebar to configure providers, opt in to review reminders, export a JSON archive, or delete local learner data. Review reminders are off until you enable them.

## Troubleshooting

If Forma cannot start, close any development server already using the configured ports and restart the application. The local service is loopback-only and retries an unexpected sidecar exit automatically. Development logs are stored in `work/local-runtime`; packaged builds show a startup error dialog with the recovery message.
