#!/usr/bin/env python3
import argparse
from pathlib import Path
import whisper


def transcribe_file(audio_path: Path, model_name: str = "base", language: str | None = None) -> str:
    model = whisper.load_model(model_name)
    result = model.transcribe(str(audio_path), language=language)
    return result["text"].strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Transcribe audio with OpenAI Whisper")
    parser.add_argument(
        "--input",
        default="ikem.ogg",
        help="Path to input audio file (default: ikem.ogg)",
    )
    parser.add_argument(
        "--output",
        default="ikem.txt",
        help="Path to output text file (default: ikem.txt)",
    )
    parser.add_argument(
        "--model",
        default="base",
        choices=["tiny", "base", "small", "medium", "large"],
        help="Whisper model size (default: base)",
    )
    parser.add_argument(
        "--language",
        default=None,
        help="Optional language code, e.g. en",
    )
    args = parser.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        raise FileNotFoundError(f"Input file not found: {in_path}")

    text = transcribe_file(in_path, model_name=args.model, language=args.language)

    out_path = Path(args.output)
    out_path.write_text(text, encoding="utf-8")

    print(f"Transcription written to: {out_path}")
    print("---")
    print(text)


if __name__ == "__main__":
    main()
