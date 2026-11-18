# Decisions

Settled decisions. Don't reopen them unless the person asks. Add new ones at the bottom with the date.

| Date | Decision | Why |
|---|---|---|
| 2026-11-18 | Main job is a GTA 6 fan page clipping many creators; secondary job is clipping one hired creator. | The person's own description ("mostly B, part of A"). |
| 2026-11-18 | Fast lane during the stream, polish lane after. | Speed wins on launch moments; polish only the best. |
| 2026-11-18 | The person posts everything themselves. No scheduler, no auto-posting. | Their choice. |
| 2026-11-18 | No AI voices, AI footage or AI images in clips. | Clips must not look AI-made. |
| 2026-11-18 | Record one 720p feed per stream, max 2 to 4 streams at once depending on the machine. | Pulling every quality level stalled the connection. (Recording tool superseded below.) |
| 2026-11-18 | Transcribe only the loud windows, not whole recordings. | Transcription was the slowest step on CPU. |
| 2026-11-18 | Layout: hook at top, full 16:9 gameplay with facecam in the middle on a blurred background, 3-word captions below, credit at the bottom. | Fast to render, keeps the facecam, works for any streamer. Per-streamer facecam crops can come later. |
| 2026-11-18 | Kick is the easiest source (public API + direct stream). Twitch needs streamlink, YouTube needs yt-dlp. | Tested Kick end to end; Twitch and YouTube paths are written but untested. |
| 2026-11-18 | Record with streamlink, not ffmpeg's HLS reader. 5 streams at once is fine. | ffmpeg lost 30-40% of every recording (2-10s holes), which caused black openings, frozen picture and dead audio in the first clips. streamlink lost 0s on 3 streams at once. |
| 2026-11-18 | Every clip is QC-checked automatically; failures go to `01_WORKING/09_qc_failed/`, never to outputs. | The person posts 20 a day and can't watch each one for glitches. |
| 2026-11-18 | Clips are 22 to 45 seconds. Batches of 10 through `clipit.py batch`. | The person found the first clips (14 to 31s) too short; target is 20 clips a day. |
| 2026-11-18 | Local log is `00_TRACKER/clip_log.csv`; the visual log page reads from its own store. | The CSV works on any machine; the page is per Claude account. |

## Known limits

- On a 2-core laptop (i5-7200U) with Chrome open, transcription and rendering are the bottleneck. Close stream tabs while clipping, and use `base.en` or switch captions to "none".
- `grab` picks moments from loudness and words, so it can choose cutscenes. Check the frames.

## What's working

(Fill in once there are 20+ posted clips with views.)
