# Stribe

Audio to text, entirely on your machine.

Stribe is a desktop app that turns a recording into a transcript using OpenAI
Whisper running locally. The mark is a five-pointed star whose lower-left leg
is a fountain pen nib — star for Starget, nib for the scribe. Pick a file, press **Transcribe**, then copy the text
or save it as a `.txt`. Nothing is uploaded and no API key is needed.

Built on the **Stargit Solutions** design system: a four-tier dark surface
stack, the electric blue → indigo → cyan accent gradient, Space Grotesk for
display and Inter for body copy.

## Install

```powershell
powershell -ExecutionPolicy Bypass -File install.ps1          # installs to %LOCALAPPDATA%
powershell -ExecutionPolicy Bypass -File install.ps1 -InPlace # runs from this folder (development)
```

The default install copies the app to `%LOCALAPPDATA%\Programs\Stribe`, creates
Desktop and Start menu shortcuts, and registers Stribe in Windows **Installed
apps** so it uninstalls the normal way. `-InPlace` skips the copy and points the
shortcuts at this working copy instead - use that while developing.

Requires Python 3.9+ on `PATH`; the installer offers to install it via winget
if it is missing.

## Sharing it

```powershell
python build_bundle.py
```

Produces `dist/Stribe-<version>-windows.zip` (~32 MB) containing the app, its
assets and fonts, the bundled ffmpeg, and a double-clickable
`Install Stribe.bat`. Send that zip to anyone on Windows; they extract it and
run the installer. `README-bundle.md` ships inside as their `README.md`.

The bundle deliberately leaves out the design concepts, asset build scripts and
the sample recording.

## Use

1. Launch **Stribe**.
2. Click the card and choose an audio file.
3. Pick a model — `base` is a good default — and a language if you know it.
4. Press **Transcribe**. The status line reports progress.
5. **Copy** puts the transcript on the clipboard; **Save .txt** writes it
   wherever you choose. The transcript is editable, so you can fix a name
   before saving.

Accepts mp3, wav, m4a, ogg/opus, flac, aac, wma and video files (mp4, mkv,
mov, avi, webm) — audio is extracted automatically by the bundled ffmpeg.

## Models

| Model | Speed | Notes |
|-------|-------|-------|
| `tiny` | fastest | Good for a quick gist |
| `base` | fast | Accurate enough for most recordings — the default |
| `small` | slower | Noticeably sharper on accents and names |
| `medium` | slow | Very accurate; worth it for long interviews |
| `large` | slowest | Best quality; downloads ~3 GB on first use |

Models are cached in `~/.cache/whisper` after the first download and kept in
memory for the rest of the session, so re-running is fast.

A transcription cannot be cancelled once it starts — Whisper has no interrupt
point — so start with a smaller model if you are unsure.

## Project layout

| Path | Purpose |
|------|---------|
| `app.py` | The application: layout, state and the transcription worker |
| `theme.py` | Stargit design tokens, DPI scaling, brand font loading |
| `widgets.py` | Dark UI toolkit — rounded cards, gradient buttons, shimmer bar |
| `build_assets.py` | Turns the generated art into `logo.png`, `hero.png`, `stribe.ico` |
| `build_fonts.py` | Cuts static weights from the variable brand fonts |
| `install.ps1` | Installer: copies files, shortcuts, Installed-apps entry |
| `uninstall.ps1` | Removes all of the above, keeps downloaded models |
| `build_bundle.py` | Packages the shareable zip into `dist/` |
| `Stribe.bat` | Launches the app directly, no shortcut needed |
| `transcribe.py` | The original command-line version |
| `assets/` | Icon, logo, backdrop and the bundled fonts |
| `assets/concepts/` | Logo exploration; not shipped in the bundle |
| `ffmpeg.exe` | Bundled decoder; the app puts it on `PATH` at startup |

The app is a plain Tk application, so it has no rounded corners or gradients of
its own — every surface in `widgets.py` is rendered with Pillow at 4× and
downsampled onto the known parent colour, which is what keeps the edges smooth.

## Command line

The original script still works:

```powershell
python transcribe.py --input audio.mp3 --output audio.txt --model base
```

## Credits

Space Grotesk and Inter are used under the SIL Open Font License; the licences
are in `assets/fonts/`. The logo mark and header backdrop were generated for
this project.
