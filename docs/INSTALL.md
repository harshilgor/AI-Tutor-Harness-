# Installing Forma Desktop

Select **Download Open Learn** in the [project README](../README.md), or open the [GitHub Releases page](https://github.com/harshilgor/Open-Learn/releases). Choose the newest published release that includes installers, then download the file for your operating system. Beta versions may be marked **Pre-release**. Installer downloads will appear after the first signed release is published.

## Windows

Download the signed Windows x64 installer, run it, and launch Forma from the Start menu. The app starts its local learning service automatically. Verify the installer hash against the release's `SHA256SUMS` file before installation.

## macOS

Download the signed and notarized installer for Apple Silicon or Intel, open it, and drag Forma to Applications. Verify the installer hash against the release's `SHA256SUMS` file before installation.

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
