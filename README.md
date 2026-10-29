# DB: your personal assistant for Windows

DB lives on your PC. Type or talk to it, and it gets things done:

- **Chat and tasks:** opens apps and websites, manages files, runs PowerShell, searches the web.
- **Voice:** say *"Hey DB, open Spotify"* and it answers out loud.
- **Screen vision:** *"Hey DB, what's on my screen?"* and it reads what's there.
- **Memory:** remembers things about you (name, preferences, people) between sessions.
- **Reminders:** *"Remind me to call Mom in 20 minutes"* gives you a Windows notification, spoken aloud in voice mode.

DB needs an AI key. **Free options work:** Google Gemini (recommended), Groq, or OpenRouter.
Add more than one and DB switches automatically when one hits its free limit. Claude (paid) also works.

| Provider | Free key | Environment variable | Notes |
|---|---|---|---|
| Google Gemini | <https://aistudio.google.com/apikey> | `GEMINI_API_KEY` | Best free choice: tools, screen vision, Google Search |
| Groq | <https://console.groq.com/keys> | `GROQ_API_KEY` | Very fast. Text only (no screen vision) |
| OpenRouter | <https://openrouter.ai/keys> | `OPENROUTER_API_KEY` | Picks a random free model |
| Claude | <https://console.anthropic.com/settings/keys> | `ANTHROPIC_API_KEY` | Paid, most capable. Used only if it's your only key, or listed first in `DB_PROVIDERS` |

Free tiers have daily and per-minute limits, and some free hosts may use your prompts for training. Check each provider's terms.

## Setup (one time)

1. Install **Python 3.11 or newer** from <https://www.python.org/downloads/>. Tick **"Add python.exe to PATH"**.
2. Get a free key from <https://aistudio.google.com/apikey> (sign in with Google, click **Create API key**).
3. Open PowerShell and save the key (replace with yours), then close PowerShell:
   ```powershell
   setx GEMINI_API_KEY "your-key"
   ```
   Optional extra free backups: `setx GROQ_API_KEY "..."` and `setx OPENROUTER_API_KEY "..."`.
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

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2FRrachet%2FDB&env=GEMINI_API_KEY,DB_WEB_PASSWORD&envDescription=A%20free%20Gemini%20API%20key%20and%20a%20password%20for%20the%20site)

To deploy:
1. Click the button above, or go to <https://vercel.com/new> and import `Rrachet/DB`. Leave the framework as **Other**.
2. Add environment variables:
   - `GEMINI_API_KEY`: free key from <https://aistudio.google.com/apikey> (and optionally `GROQ_API_KEY`, `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`)
   - `DB_WEB_PASSWORD`: any password. The site asks for it, so strangers can't use your keys.
3. Click **Deploy**. Every push to `main` redeploys automatically.

Optional: `DB_MODEL` and `DB_EFFORT` work the same as in the Windows app.

## Safety

- DB **asks before every PowerShell command** and before overwriting a file. In voice mode, say "yes" to allow it.
- Want no questions? Set `DB_AUTO_APPROVE=1`. Only do this if you trust what you ask for, since DB can then change anything your account can.
- Memories and reminders are stored in `C:\Users\<you>\.db_assistant\`. Delete that folder to wipe them.

## Settings (optional environment variables)

| Variable | Default | What it does |
|---|---|---|
| `DB_PROVIDERS` | `gemini,groq,openrouter,claude` | Which providers to use, in order (only ones with a key are used). |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model. |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | Groq model. |
| `OPENROUTER_MODEL` | `openrouter/free` | OpenRouter model (`openrouter/free` picks a free one). |
| `DB_MODEL` | `claude-opus-5-5` | Claude model. `claude-sonnet-5-5` is cheaper. |
| `DB_EFFORT` | `medium` | Claude only: `low` is faster and cheaper, `high` is more careful. |
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
  brain.py      sends your request to the AI and runs the tools it picks
  llm.py        free providers (Gemini, Groq, OpenRouter) and web search
  tools.py      what DB can do: PowerShell, apps, files, screenshot, memory, reminders, web search
  voice.py      text-to-speech (pyttsx3) and speech-to-text (SpeechRecognition)
  memory.py     long-term memory (JSON file)
  reminders.py  reminders plus Windows notifications
api/chat.py     web version: Vercel serverless function
api/_providers.py  web version: AI providers with automatic fallback
public/         web version: chat page
```
