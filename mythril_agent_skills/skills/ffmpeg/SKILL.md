---
name: ffmpeg
description: >
  Processes video and audio with the FFmpeg CLI (ffmpeg, ffprobe): transcode,
  convert formats, compress, trim, merge, resize, extract audio, add subtitles
  or watermarks, make GIFs and thumbnails, and convert audio (MP3, WAV, PCM,
  AAC, FLAC, OGG, OPUS). Use when the user wants to transform or inspect a video
  or audio file, e.g. "compress video", "trim video", "video to gif", "mp4 to
  webm", "wav to mp3", "extract audio", "视频压缩", "视频裁剪", "提取音频", "音频转换",
  "ffmpeg".
license: Apache-2.0
---

# FFmpeg

Video and audio processing with the `ffmpeg` / `ffprobe` CLI. You already know
most ffmpeg syntax; this skill adds the workflow, the safety rules, and the
pitfalls that commonly produce broken or unplayable output.

**Recipe catalog:** [references/recipes.md](references/recipes.md) has
copy-ready commands for every common job (info, convert, compress, resize,
trim, merge, extract/convert audio, subtitles, GIF/WebP, thumbnails,
watermark, add/replace audio, speed, batch, HLS/DASH, codec tables, hardware
acceleration). Read the relevant section when you need exact flags.

# Prerequisites

Requires `ffmpeg` and `ffprobe` on PATH:

```bash
command -v ffmpeg >/dev/null && command -v ffprobe >/dev/null || echo "FFmpeg missing"
```

Install if missing:

- macOS: `brew install ffmpeg`
- Ubuntu/Debian: `sudo apt-get install ffmpeg`
- Fedora/RHEL: `sudo dnf install ffmpeg-free` (or enable RPM Fusion for full `ffmpeg`)
- Windows: `scoop install ffmpeg`, `choco install ffmpeg`, or `winget install --id Gyan.FFmpeg`

# Workflow

1. **Pre-flight** — confirm `ffmpeg` exists (above).
2. **Inspect the input** before choosing flags — codecs, resolution, duration,
   and stream layout decide whether `-c copy` is possible and which streams
   to map:
   ```bash
   ffprobe -v error -show_entries stream=index,codec_type,codec_name,width,height,sample_rate,channels -show_entries format=duration -of json "input.mp4"
   ```
3. **Pick the output filename** (rules below).
4. **Run the command** — look up the recipe in `references/recipes.md` if you
   need exact flags. Add `-hide_banner` for cleaner output.
5. **Verify** — `ffprobe` the output (duration, codecs, resolution) and report
   the result and the output path to the user.

# Output Files — preserve the original

Write to a new file unless the user explicitly asks to overwrite ("覆盖",
"replace", "in-place", "same name", "overwrite"). Users rarely expect a
lossy re-encode to destroy their source.

| Operation | Example output name |
|---|---|
| Convert | `video.avi` → `video.mp4` |
| Compress | `video.mp4` → `video_compressed.mp4` |
| Trim | `video.mp4` → `video_clip.mp4` |
| Resize | `video.mp4` → `video_720p.mp4` |
| Extract audio | `video.mp4` → `video.mp3` |
| Audio convert | `audio.wav` → `audio.mp3` |
| Batch | a subdirectory, e.g. `compressed/`, `converted/` |

- ffmpeg cannot read and write the same file. For an in-place request, write
  to a temp file in the same directory, then move it over the original.
- Pass `-n` (never overwrite; fail if the output exists) by default. Agent
  shells have no terminal, so ffmpeg's interactive "Overwrite? [y/N]" prompt
  can hang or behave unpredictably — do not rely on it. Use `-y` only when the
  user approved replacing the target.
- Quote every path; filenames with spaces are common.
- For batch jobs, run the command on one file first and check the result
  before looping over the rest.

# Pitfalls (the non-obvious parts)

**Seeking (`-ss`) placement changes accuracy.**
- `-ss` *before* `-i` seeks the input — fast. With re-encoding it is
  frame-accurate; with `-c copy` the cut snaps to the previous keyframe, so
  the clip may start early or with a frozen/black lead-in.
- `-ss` *after* `-i` decodes and discards up to that point — slow but exact.
- Need a precise cut? Re-encode (`-c:v libx264 -c:a aac`) instead of `-c copy`.
- `-to` is a timestamp, `-t` is a duration. When `-ss` comes before `-i`,
  timestamps reset to 0, so `-to` behaves like a duration — prefer `-t` there.

**Compatibility of H.264 MP4 output.**
- libx264 with yuv420p needs even width and height. Scale with `-2`, not `-1`
  (`scale=1280:-2`); otherwise you get "height not divisible by 2".
- Sources such as screen recordings, PNG sequences, or ProRes may be yuv444p
  or 10-bit; players (QuickTime, browsers, phones) then refuse the file. Add
  `-pix_fmt yuv420p` when the output must play everywhere.
- Add `-movflags +faststart` for MP4 that will be played on the web, so the
  index is at the front and playback starts before the full download.

**`-c copy` is fast and lossless, but only if codecs fit the container.**
Remuxing MKV→MP4 works for H.264/AAC but fails for e.g. Vorbis audio or
PGS subtitles. On "codec not supported in container", re-encode the offending
stream only (`-c:v copy -c:a aac`).

**Multiple streams need explicit `-map`.** By default ffmpeg picks one video
and one audio stream. To keep all audio tracks or subtitles, use
`-map 0`; to pick specific ones use `-map 0:v:0 -map 0:a:1`. When combining
inputs (replace audio, overlay), map every output stream explicitly.

**Raw PCM has no header.** Reading `.pcm`/`.raw` needs the format, sample rate,
and channels *before* `-i`: `ffmpeg -f s16le -ar 44100 -ac 2 -i in.pcm out.wav`.
Ask the user if they are unknown — guessing produces noise or wrong speed.

**Concatenation.** The concat demuxer (`-f concat -safe 0 -i list.txt -c copy`)
only works when all parts share codec, resolution, frame rate, and sample
rate; otherwise re-encode. Delete the temporary list file afterwards.

**Quality knobs.**
- H.264 CRF: 18 ≈ visually lossless, 23 default, 28 noticeably smaller/worse.
  x265 CRF ~28 ≈ x264 CRF 23. Slower `-preset` = smaller file at same quality.
- For a target file size, use two-pass with a computed bitrate
  (`bitrate ≈ size_bits / duration_s − audio_bitrate`).
- `atempo` accepts 0.5–2.0 per filter instance in older builds; chain it
  (`atempo=2.0,atempo=1.5`) for larger speed changes.
- For good-looking GIFs, use the two-pass `palettegen` / `paletteuse` recipe.

# Troubleshooting

| Error | Cause / fix |
|---|---|
| `ffmpeg: not found` | Not installed or not on PATH — see Prerequisites. |
| `Unknown encoder 'x'` | Build lacks that codec. Check `ffmpeg -encoders \| grep x`; use another encoder or a fuller build. |
| `Invalid data found when processing input` | Corrupt file or unrecognized format; inspect with `ffprobe`. Raw PCM needs `-f/-ar/-ac`. |
| Output empty or 0 s long | `-ss`/`-to` outside the file's duration, or `-to` misused after an input-side `-ss`. |
| `height not divisible by 2` | Use `-2` in the scale filter. |
| `codec not currently supported in container` | `-c copy` into an incompatible container — re-encode that stream. |
| File plays in VLC but not QuickTime/browser | Add `-pix_fmt yuv420p` (and `-movflags +faststart`). |
