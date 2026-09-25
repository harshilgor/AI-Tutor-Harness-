# Install Open Learn

Open Learn does not currently include a ready-to-install desktop package. You can run it locally from the source code.

## Windows

Install [Git](https://git-scm.com/download/win), [Node.js 22.13 or newer](https://nodejs.org/), and [Python 3.12 or newer](https://www.python.org/downloads/). During Python setup, enable **Add Python to PATH**.

Open PowerShell and run:

```powershell
git clone https://github.com/harshilgor/Open-Learn.git
cd Open-Learn
.\install-local.ps1
```

The first run installs the required packages and starts the app. Later runs reuse them. Open [http://127.0.0.1:3000](http://127.0.0.1:3000). Press `Ctrl+C` in PowerShell to stop.

## macOS and Linux

Install Git, Node.js 22.13 or newer, and Python 3.12 or newer. Open two terminal windows in the cloned project.

In the first terminal, install and start the local service:

```bash
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements.txt
backend/.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

In the second terminal, start the web app:

```bash
cd web
npm ci
npm run dev -- --hostname 127.0.0.1 --port 3000
```

Then open [http://127.0.0.1:3000](http://127.0.0.1:3000). Keep both terminal windows open while using Open Learn.

## AI provider (optional)

The built-in tutor works without an API key. To use a model provider, start Open Learn, open **Settings → API keys**, and add your provider key. It is stored locally and is not committed or sent to the web app.

## Troubleshooting

- If setup says Python or Node is too old, install the required version and open a new PowerShell window.
- If the app says a port is already in use, close the other app using port `3000` or `8000`, then try again.
- If setup fails, run `install-local.ps1` again after fixing the reported issue; it will reuse dependencies that are already installed.
