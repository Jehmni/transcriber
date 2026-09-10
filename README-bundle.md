# Stribe

**Audio to text, entirely on your machine.**

Stribe turns a recording into a transcript. Pick an audio file, press
Transcribe, then copy the text or save it as a `.txt`.

Your audio never leaves your computer. There is no account, no API key and no
internet connection needed once it is set up.

---

## Install

1. Extract this folder somewhere — your Desktop or Downloads is fine.
2. Double-click **`Install Stribe.bat`**.
3. Follow the prompts, then wait. The first install downloads about 1 GB of
   speech-recognition libraries and takes a few minutes.

When it finishes you'll have **Stribe** on your Desktop and in the Start menu.

You can delete the extracted folder afterwards — Stribe copies itself to
`%LOCALAPPDATA%\Programs\Stribe` during installation.

### If you don't have Python

Stribe needs Python 3.9 or newer. If it isn't found, the installer offers to
install it for you automatically. Say yes and it handles the rest.

If that doesn't work, install Python manually from
<https://www.python.org/downloads/> — **tick "Add python.exe to PATH"** on the
first screen of the setup — then run `Install Stribe.bat` again.

### If Windows warns you

SmartScreen may say "Windows protected your PC" because this installer isn't
code-signed. Click **More info → Run anyway**. Everything here is plain text
you can read: `install.ps1` is the whole installer.

---

## Using it

1. Open **Stribe**.
2. Click the big card and choose an audio file.
3. Pick a model — **base** is a good starting point — and set the language if
   you know it (slightly faster and more accurate than auto-detect).
4. Press **Transcribe**.
5. **Copy** puts the text on your clipboard. **Save .txt** writes it wherever
   you choose.

The transcript is editable before you save, so you can correct a name or a
technical term first.

**Accepted files:** mp3, wav, m4a, ogg, opus, flac, aac, wma, and video files
(mp4, mkv, mov, avi, webm) — the audio is extracted automatically.

---

## Choosing a model

| Model | Speed | Best for |
|-------|-------|----------|
| **tiny** | Fastest | A quick gist |
| **base** | Fast | Most recordings — the default |
| **small** | Slower | Accents, names, technical terms |
| **medium** | Slow | Long interviews where accuracy matters |
| **large** | Slowest | Best possible quality |

The first time you use a model it downloads once (base is ~150 MB, large is
~3 GB) and is reused after that.

**A transcription can't be cancelled once it starts.** If you're unsure, try a
smaller model first.

---

## Notes

- **Speed depends on your computer.** Roughly, a 10-minute recording takes a
  few minutes on `base`. There's no GPU requirement.
- **It works offline.** Only the one-time setup and model downloads need the
  internet.
- **Nothing is uploaded, ever.** The transcription runs locally.

## Uninstalling

Either use **Settings → Apps → Installed apps → Stribe → Uninstall**, or run
`Uninstall Stribe.bat`.

Downloaded speech models are kept in `%USERPROFILE%\.cache\whisper` so you
don't have to fetch them again. Delete that folder to reclaim the space.

---

## Command line

For batch work, the app ships with a command-line version:

```
python transcribe.py --input audio.mp3 --output audio.txt --model base
```

---

Stribe is built by **Stargit Solutions**. Speech recognition by OpenAI Whisper,
running locally. Space Grotesk and Inter are used under the SIL Open Font
License (see `assets/fonts/`).
