# DB: your personal assistant for Windows

DB lives on your PC. Type or talk to it, and it gets things done:

- **Chat and tasks:** opens apps and websites, manages files, runs PowerShell, searches the web.
- **Voice:** say *"Hey DB, open Spotify"* and it answers out loud.
- **Screen vision:** *"Hey DB, what's on my screen?"* and it reads what's there.
- **Memory:** remembers things about you (name, preferences, people) between sessions.
- **Reminders:** *"Remind me to call Mom in 20 minutes"* gives you a Windows notification, spoken aloud in voice mode.

DB uses Claude as its brain, so it needs an Anthropic API key. Usage is billed to that key.

## Setup (one time)

1. Install **Python 3.11 or newer** from <https://www.python.org/downloads/>. Tick **"Add python.exe to PATH"**.
2. Get an API key from <https://console.anthropic.com/settings/keys>.
3. Open PowerShell and save the key (replace with yours), then close PowerShell:
   ```powershell
   setx ANTHROPIC_API_KEY "sk-ant-..."
   ```
4. Download this repo (green **Code** button, then **Download ZIP**) and unzip it, e.g. to `C:\DB`.
5. Double-click **`install.bat`**.

## Using DB

| Want to... | Double-click |
|---|---|
| Type to DB | `start_db.bat` |
| Talk hands-free ("Hey DB ...") | `start_db_voice.bat` |
| Start DB automatically when you log in | `autostart.bat` (run `autostart.bat remove` to undo) |

In typing mode, `start_db.bat --speak` also reads replies aloud. Type `/new` for a fresh chat, `exit` to quit.
In voice mode, say *"Hey DB, goodbye"* to stop.

Things to try:
- "What's using my RAM right now?"
- "Make a folder on my Desktop called Projects and move all PDFs from Downloads into it."
- "Search the latest news on ISRO and summarize it."
- "Look at my screen and explain this error."
- "Remember that my sister's birthday is 12 March."
- "Remind me at 6:30 pm to go to the gym."

## Web version (Vercel)

This repo also has a web chat version of DB (`public/` + `api/chat.py`). It can chat and search the
web from any phone or browser. Controlling your PC (apps, files, voice, screen) still needs the Windows app.

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2FRrachet%2FDB&env=ANTHROPIC_API_KEY,DB_WEB_PASSWORD&envDescription=Your%20Anthropic%20API%20key%20and%20a%20password%20for%20the%20site)

To deploy:
1. Click the button above, or go to <https://vercel.com/new> and import `Rrachet/DB`. Leave the framework as **Other**.
2. Add two environment variables:
   - `ANTHROPIC_API_KEY`: your key from console.anthropic.com
   - `DB_WEB_PASSWORD`: any password. The site asks for it, so strangers can't use your API key.
3. Click **Deploy**. Every push to `main` redeploys automatically.

Optional: `DB_MODEL` and `DB_EFFORT` work the same as in the Windows app.

## Safety

- DB **asks before every PowerShell command** and before overwriting a file. In voice mode, say "yes" to allow it.
- Want no questions? Set `DB_AUTO_APPROVE=1`. Only do this if you trust what you ask for, since DB can then change anything your account can.
- Memories and reminders are stored in `C:\Users\<you>\.db_assistant\`. Delete that folder to wipe them.

## Settings (optional environment variables)

| Variable | Default | What it does |
|---|---|---|
| `DB_MODEL` | `claude-opus-5-5` | Which Claude model to use. `claude-sonnet-5-5` is cheaper. |
| `DB_EFFORT` | `medium` | `low` is faster and cheaper, `high` is more careful. |
| `DB_AUTO_APPROVE` | `0` | `1` = run commands without asking. |
| `DB_DATA_DIR` | `~\.db_assistant` | Where memory and reminders are saved. |

## Troubleshooting

- **PyAudio fails to install:** run `pip install pipwin` then `pipwin install pyaudio` inside `.venv`, or use typing mode.
- **"Hey DB" isn't recognized:** speech recognition sometimes hears "Hey TB" or "Hey Deebee". Those also work. Add your own in `db/config.py` (`WAKE_WORDS`).
- **Voice needs internet:** speech-to-text uses Google's free recognizer.

## How it works

```
db/
  __main__.py   typing / voice loop, asks you for approval
  brain.py      sends your request to Claude and runs the tools it picks
  tools.py      what DB can do: PowerShell, apps, files, screenshot, memory, reminders, web search
  voice.py      text-to-speech (pyttsx3) and speech-to-text (SpeechRecognition)
  memory.py     long-term memory (JSON file)
  reminders.py  reminders plus Windows notifications
api/chat.py     web version: Vercel serverless function
public/         web version: chat page
```
