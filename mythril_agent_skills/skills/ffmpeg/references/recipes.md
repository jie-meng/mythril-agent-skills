# FFmpeg Command Recipes

Copy-ready commands for common jobs. Replace `input.*` / `output.*` with real
paths (quoted), and follow the output-naming rules in SKILL.md — never write
over the source file unless the user asked. Add `-n` (never overwrite) to the
commands below unless the user approved replacing the output.

## Contents

- [File Information](#file-information)
- [Video Format Conversion](#video-format-conversion)
- [Video Compression](#video-compression)
- [Video Resizing](#video-resizing)
- [Video Trimming / Cutting](#video-trimming--cutting)
- [Video Merging / Concatenation](#video-merging--concatenation)
- [Extract Audio from Video](#extract-audio-from-video)
- [Audio Format Conversion](#audio-format-conversion)
- [Audio Adjustments](#audio-adjustments)
- [Subtitles](#subtitles)
- [Video to GIF / Animated Images](#video-to-gif--animated-images)
- [Thumbnails / Frame Extraction](#thumbnails--frame-extraction)
- [Watermark / Overlay](#watermark--overlay)
- [Add / Replace Audio in Video](#add--replace-audio-in-video)
- [Speed Change](#speed-change)
- [Batch Processing](#batch-processing)
- [Streaming Formats (HLS / DASH)](#streaming-formats-hls--dash)
- [Common Codec Quick Reference](#common-codec-quick-reference)
- [Performance Tips](#performance-tips)

## File Information

```bash
# Full info
ffprobe -v quiet -print_format json -show_format -show_streams input.mp4

# Duration only
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 input.mp4

# Resolution only
ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 input.mp4

# Codec info
ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of default=noprint_wrappers=1:nokey=1 input.mp4

# Audio info
ffprobe -v error -select_streams a:0 -show_entries stream=codec_name,sample_rate,channels,bit_rate -of json input.mp4

# Human-readable summary
ffprobe -hide_banner input.mp4
```

## Video Format Conversion

```bash
# Basic conversion (codec inferred from extension)
ffmpeg -i input.avi output.mp4

# AVI/MKV to MP4 (H.264 + AAC, widely compatible)
ffmpeg -i input.avi -c:v libx264 -c:a aac -b:a 192k output.mp4

# MP4 to WebM (VP9 + Opus)
ffmpeg -i input.mp4 -c:v libvpx-vp9 -crf 30 -b:v 0 -c:a libopus output.webm

# MP4 to MKV (copy streams without re-encoding — fast)
ffmpeg -i input.mp4 -c copy output.mkv

# MOV to MP4 (copy if compatible codecs)
ffmpeg -i input.mov -c copy output.mp4

# Re-encode with H.265/HEVC for better compression
ffmpeg -i input.mp4 -c:v libx265 -crf 28 -c:a aac -b:a 128k output_h265.mp4
```

## Video Compression

```bash
# Good quality, reasonable size (CRF 23 is default, lower = better quality)
ffmpeg -i input.mp4 -c:v libx264 -crf 23 -preset medium -c:a aac -b:a 128k output.mp4

# Smaller file (higher CRF = more compression, lower quality)
ffmpeg -i input.mp4 -c:v libx264 -crf 28 -preset slow -c:a aac -b:a 96k output_small.mp4

# Fast compression (lower quality, fast encoding)
ffmpeg -i input.mp4 -c:v libx264 -crf 23 -preset ultrafast -c:a copy output_fast.mp4

# Target file size (e.g., ~50MB for a 10-minute video)
# bitrate = target_size_bits / duration_seconds
# 50MB = 400Mbit; 400Mbit / 600s ≈ 667kbit/s video (subtract ~128k for audio)
# Pass 1 analyses video only (-an); use NUL instead of /dev/null on Windows.
ffmpeg -y -i input.mp4 -c:v libx264 -b:v 540k -pass 1 -an -f null /dev/null && \
ffmpeg -i input.mp4 -c:v libx264 -b:v 540k -c:a aac -b:a 128k -pass 2 output.mp4
```

CRF reference (H.264): 0 = lossless, 18 = visually lossless, 23 = default, 28 = noticeable loss, 51 = worst.

Preset reference: `ultrafast`, `superfast`, `veryfast`, `faster`, `fast`, `medium` (default), `slow`, `slower`, `veryslow`. Slower = better compression ratio.

## Video Resizing

```bash
# Scale to 1280x720 (force exact, may distort)
ffmpeg -i input.mp4 -vf "scale=1280:720" -c:a copy output_720p.mp4

# Scale width to 1280, auto height (maintain aspect ratio)
ffmpeg -i input.mp4 -vf "scale=1280:-2" -c:a copy output.mp4

# Scale to 50%
ffmpeg -i input.mp4 -vf "scale=iw/2:ih/2" -c:a copy output_half.mp4

# Scale height to 720, auto width
ffmpeg -i input.mp4 -vf "scale=-2:720" -c:a copy output_720p.mp4
```

Use `-2` instead of `-1` to ensure dimensions are divisible by 2 (required by most codecs).

## Video Trimming / Cutting

```bash
# Extract from 00:01:30 to 00:03:00 (copy without re-encoding — fast, may have keyframe imprecision)
ffmpeg -i input.mp4 -ss 00:01:30 -to 00:03:00 -c copy output_clip.mp4

# Extract with re-encoding (precise cuts)
ffmpeg -i input.mp4 -ss 00:01:30 -to 00:03:00 -c:v libx264 -c:a aac output_clip.mp4

# First 30 seconds
ffmpeg -i input.mp4 -t 30 -c copy output_first30s.mp4

# Skip first 10 seconds
ffmpeg -i input.mp4 -ss 10 -c copy output_skip10s.mp4
```

Time formats: `HH:MM:SS`, `HH:MM:SS.mmm`, or seconds (e.g. `90` = 1m30s).

## Video Merging / Concatenation

```bash
# Create file list
cat > filelist.txt << 'EOF'
file 'part1.mp4'
file 'part2.mp4'
file 'part3.mp4'
EOF

# Concatenate (same codec, resolution, frame rate — fast)
ffmpeg -f concat -safe 0 -i filelist.txt -c copy output_merged.mp4

# Concatenate with re-encoding (different formats/resolutions)
ffmpeg -f concat -safe 0 -i filelist.txt -c:v libx264 -c:a aac output_merged.mp4

# Clean up file list
rm filelist.txt
```

## Extract Audio from Video

```bash
# Extract as MP3
ffmpeg -i input.mp4 -vn -c:a libmp3lame -b:a 192k output.mp3

# Extract as WAV (lossless)
ffmpeg -i input.mp4 -vn -c:a pcm_s16le output.wav

# Extract as AAC (copy if already AAC — fast)
ffmpeg -i input.mp4 -vn -c:a copy output.aac

# Extract as OGG
ffmpeg -i input.mp4 -vn -c:a libvorbis -q:a 6 output.ogg

# Extract as FLAC
ffmpeg -i input.mp4 -vn -c:a flac output.flac
```

## Audio Format Conversion

```bash
# MP3 to WAV
ffmpeg -i input.mp3 -c:a pcm_s16le output.wav

# WAV to MP3 (CBR 320k)
ffmpeg -i input.wav -c:a libmp3lame -b:a 320k output.mp3

# WAV to MP3 (VBR, quality 0 = best ~245kbps, 9 = lowest ~65kbps)
ffmpeg -i input.wav -c:a libmp3lame -q:a 0 output.mp3

# MP3 to OGG (Vorbis)
ffmpeg -i input.mp3 -c:a libvorbis -q:a 6 output.ogg

# WAV to OGG
ffmpeg -i input.wav -c:a libvorbis -q:a 6 output.ogg

# OGG to MP3
ffmpeg -i input.ogg -c:a libmp3lame -b:a 256k output.mp3

# WAV to AAC
ffmpeg -i input.wav -c:a aac -b:a 256k output.m4a

# WAV to FLAC (lossless)
ffmpeg -i input.wav -c:a flac output.flac

# FLAC to MP3
ffmpeg -i input.flac -c:a libmp3lame -b:a 320k output.mp3

# WAV to OPUS (excellent quality-to-size ratio)
ffmpeg -i input.wav -c:a libopus -b:a 128k output.opus

# Any format to WAV (universal intermediate)
ffmpeg -i input.any -c:a pcm_s16le -ar 44100 -ac 2 output.wav

# PCM raw to WAV (must specify format, sample rate, channels)
ffmpeg -f s16le -ar 44100 -ac 2 -i input.pcm output.wav

# WAV to PCM raw
ffmpeg -i input.wav -f s16le -acodec pcm_s16le output.pcm

# WMA to MP3
ffmpeg -i input.wma -c:a libmp3lame -b:a 256k output.mp3

# M4A to MP3
ffmpeg -i input.m4a -c:a libmp3lame -b:a 256k output.mp3
```

## Audio Adjustments

```bash
# Change bitrate
ffmpeg -i input.mp3 -c:a libmp3lame -b:a 128k output_128k.mp3

# Change sample rate (e.g., 44100 Hz, 22050 Hz, 16000 Hz, 8000 Hz)
ffmpeg -i input.wav -ar 16000 output_16k.wav

# Convert to mono
ffmpeg -i input.mp3 -ac 1 output_mono.mp3

# Convert to stereo
ffmpeg -i input.mp3 -ac 2 output_stereo.mp3

# Adjust volume (2.0 = double, 0.5 = half)
ffmpeg -i input.mp3 -af "volume=1.5" output_louder.mp3

# Normalize audio (loudnorm filter)
ffmpeg -i input.mp3 -af loudnorm output_normalized.mp3

# Trim audio (same syntax as video)
ffmpeg -i input.mp3 -ss 00:00:30 -to 00:02:00 -c copy output_clip.mp3

# Fade in/out (fade in 3s, fade out last 3s of a 60s file: st = duration - 3)
ffmpeg -i input.mp3 -af "afade=t=in:st=0:d=3,afade=t=out:st=57:d=3" output_faded.mp3

# Merge/concatenate audio files
cat > audiolist.txt << 'EOF'
file 'part1.mp3'
file 'part2.mp3'
EOF
ffmpeg -f concat -safe 0 -i audiolist.txt -c copy output_merged.mp3
rm audiolist.txt
```

## Subtitles

```bash
# Burn subtitles into video (hardcoded, cannot be turned off)
ffmpeg -i input.mp4 -vf "subtitles=subs.srt" output_subbed.mp4

# Burn ASS/SSA subtitles (preserves styling)
ffmpeg -i input.mp4 -vf "ass=subs.ass" output_subbed.mp4

# Add soft subtitles (can be toggled in player)
ffmpeg -i input.mp4 -i subs.srt -c copy -c:s mov_text output_subbed.mp4

# Extract subtitles
ffmpeg -i input.mkv -map 0:s:0 output_subs.srt
```

## Video to GIF / Animated Images

```bash
# Basic video to GIF (10 fps, 480px width)
ffmpeg -i input.mp4 -vf "fps=10,scale=480:-1:flags=lanczos" output.gif

# High quality GIF with palette generation (two-pass)
ffmpeg -i input.mp4 -vf "fps=10,scale=480:-1:flags=lanczos,palettegen" palette.png
ffmpeg -i input.mp4 -i palette.png -lavfi "fps=10,scale=480:-1:flags=lanczos [x]; [x][1:v] paletteuse" output.gif

# GIF from specific segment
ffmpeg -ss 5 -t 3 -i input.mp4 -vf "fps=10,scale=320:-1:flags=lanczos" output.gif

# Video to animated WebP
ffmpeg -i input.mp4 -vf "fps=15,scale=480:-1" -loop 0 output.webp
```

## Thumbnails / Frame Extraction

```bash
# Extract single frame at specific time
ffmpeg -ss 00:00:10 -i input.mp4 -frames:v 1 thumbnail.jpg

# Extract frame every N seconds (e.g., every 10 seconds)
ffmpeg -i input.mp4 -vf "fps=1/10" thumbnails_%03d.jpg

# Extract frame at percentage (e.g., 25% into the video)
# First get duration, then calculate timestamp
duration=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 input.mp4)
timestamp=$(echo "$duration * 0.25" | bc)
ffmpeg -ss "$timestamp" -i input.mp4 -frames:v 1 thumbnail_25pct.jpg

# Contact sheet / tile preview (4x4 grid)
ffmpeg -i input.mp4 -vf "select='not(mod(n\,100))',scale=320:-1,tile=4x4" -frames:v 1 contact_sheet.jpg
```

## Watermark / Overlay

```bash
# Image watermark (bottom-right corner)
ffmpeg -i input.mp4 -i watermark.png -filter_complex "overlay=W-w-10:H-h-10" output.mp4

# Text overlay
ffmpeg -i input.mp4 -vf "drawtext=text='Sample':fontsize=24:fontcolor=white:x=10:y=10" output.mp4

# Semi-transparent watermark
ffmpeg -i input.mp4 -i watermark.png -filter_complex "[1:v]format=rgba,colorchannelmixer=aa=0.3[wm];[0:v][wm]overlay=W-w-10:H-h-10" output.mp4

# Picture-in-picture
ffmpeg -i main.mp4 -i pip.mp4 -filter_complex "[1:v]scale=320:-1[pip];[0:v][pip]overlay=W-w-10:10" output.mp4
```

## Add / Replace Audio in Video

```bash
# Replace audio track
ffmpeg -i input.mp4 -i new_audio.mp3 -c:v copy -c:a aac -map 0:v:0 -map 1:a:0 output.mp4

# Add audio to video (mix with original)
ffmpeg -i input.mp4 -i bgm.mp3 -filter_complex "[0:a][1:a]amix=inputs=2:duration=first[aout]" -map 0:v -map "[aout]" -c:v copy output.mp4

# Remove audio from video (mute)
ffmpeg -i input.mp4 -an -c:v copy output_muted.mp4
```

## Speed Change

```bash
# Speed up video 2x (with audio pitch correction)
ffmpeg -i input.mp4 -filter_complex "[0:v]setpts=0.5*PTS[v];[0:a]atempo=2.0[a]" -map "[v]" -map "[a]" output_2x.mp4

# Slow down video 0.5x
ffmpeg -i input.mp4 -filter_complex "[0:v]setpts=2.0*PTS[v];[0:a]atempo=0.5[a]" -map "[v]" -map "[a]" output_slow.mp4

# Speed up audio only
ffmpeg -i input.mp3 -af "atempo=1.5" output_fast.mp3
```

## Batch Processing

```bash
# Convert all AVI to MP4
for f in *.avi; do
  ffmpeg -i "$f" -c:v libx264 -c:a aac "${f%.avi}.mp4"
done

# Compress all MP4 in directory
mkdir -p compressed
for f in *.mp4; do
  ffmpeg -i "$f" -c:v libx264 -crf 28 -preset slow -c:a aac -b:a 128k "compressed/$f"
done

# Convert all WAV to MP3
for f in *.wav; do
  ffmpeg -i "$f" -c:a libmp3lame -b:a 192k "${f%.wav}.mp3"
done

# Convert all FLAC to OGG
for f in *.flac; do
  ffmpeg -i "$f" -c:a libvorbis -q:a 6 "${f%.flac}.ogg"
done
```

## Streaming Formats (HLS / DASH)

```bash
# Create HLS stream
ffmpeg -i input.mp4 -c:v libx264 -c:a aac -f hls -hls_time 10 -hls_list_size 0 output.m3u8

# Create multiple bitrate HLS (adaptive) — map video AND audio once per
# variant: var_stream_map needs v:0/v:1 to exist, and the HLS muxer refuses
# one audio stream shared by two variants
ffmpeg -i input.mp4 \
  -map 0:v:0 -map 0:a:0 -map 0:v:0 -map 0:a:0 -c:v libx264 -c:a aac \
  -b:v:0 800k -s:v:0 640x360 \
  -b:v:1 1400k -s:v:1 1280x720 \
  -f hls -hls_time 10 -master_pl_name master.m3u8 \
  -var_stream_map "v:0,a:0 v:1,a:1" \
  stream_%v/output.m3u8
```

## Common Codec Quick Reference

### Video Codecs

| Codec | FFmpeg encoder | Use case |
|---|---|---|
| H.264 | `libx264` | Most compatible, good quality |
| H.265/HEVC | `libx265` | Better compression, less compatible |
| VP9 | `libvpx-vp9` | WebM, web playback |
| AV1 | `libaom-av1` | Best compression, slow encoding |
| Copy | `copy` | No re-encoding (fast, lossless) |

### Audio Codecs

| Codec | FFmpeg encoder | Extension | Use case |
|---|---|---|---|
| MP3 | `libmp3lame` | `.mp3` | Universal compatibility |
| AAC | `aac` | `.m4a`, `.aac` | Apple/mobile, streaming |
| Vorbis | `libvorbis` | `.ogg` | Open format, gaming |
| Opus | `libopus` | `.opus` | Best quality-per-bit, VoIP, WebRTC |
| FLAC | `flac` | `.flac` | Lossless compression |
| PCM | `pcm_s16le` | `.wav` | Uncompressed, editing |
| WMA | `wmav2` | `.wma` | Windows legacy |

## Performance Tips

```bash
# Use hardware acceleration (macOS — VideoToolbox)
ffmpeg -i input.mp4 -c:v h264_videotoolbox -b:v 5M -c:a aac output.mp4

# Use hardware acceleration (NVIDIA — NVENC)
ffmpeg -i input.mp4 -c:v h264_nvenc -preset fast -c:a aac output.mp4

# Use hardware acceleration (Intel — QSV)
ffmpeg -i input.mp4 -c:v h264_qsv -preset faster -c:a aac output.mp4

# Use multiple threads
ffmpeg -threads 0 -i input.mp4 -c:v libx264 -c:a aac output.mp4

# Suppress banner for cleaner output
ffmpeg -hide_banner -i input.mp4 ...
```
