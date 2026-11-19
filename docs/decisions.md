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
| 2026-11-19 | Render seeks 3s early and cuts sound and picture at the same timestamp; QC measures lip sync on every clip (fail at 0.1s). | Most clips had the picture 0.8-1.8s off the sound: resetting each track to its own first frame after a seek shifted the picture by up to a keyframe gap. Found by the person, not by QC. |
| 2026-11-18 | Clips are 22 to 45 seconds. Batches of 10 through `clipit.py batch`. | The person found the first clips (14 to 31s) too short; target is 20 clips a day. |
| 2026-11-18 | Local log is `00_TRACKER/clip_log.csv`; the visual log page reads from its own store. | The CSV works on any machine; the page is per Claude account. |
| 2026-11-19 | YouTube gets 3 to 5 Shorts a day (series Shorts + best singles) and 1 to 2 long videos a week; the full volume goes to TikTok, Reels and X. Ranked compilations via `clipit.py compile`. | YouTube's reused-content rule targets channels of near-identical reposted clips; rankings, series and long-form add our own value. See `docs/youtube_strategy.md`. |
| 2026-11-19 | Output is split across three channels: `main` (Five Star Moments, run by the person), `channel_2`, `channel_3`. Each clip goes to one channel. Main gets the most exciting and engaging clips of any type (tension and payoff, big reactions, chaos, debate starters); channels 2 and 3 get an even mix of everything else. Channel folders are flat (no dates): each clip's .mp4 sits next to a plain-text .txt with the title and the caption to paste, so anyone on the team can post it. Tech notes go to `01_WORKING/06_transcripts/clip_details/`. | The person runs three channels that all need content. Main is picking up: the cops/arrest clip got 888 views vs 1 to 2 for talk and chill clips, so main gets more clips that engage like it, not only cop clips. |

## Known limits

- On a 2-core laptop (i5-7200U) with Chrome open, transcription and rendering are the bottleneck. Close stream tabs while clipping, and use `base.en` or switch captions to "none".
- `grab` picks moments from loudness and words, so it can choose cutscenes. Check the frames.

## What's working

(Fill in once there are 20+ posted clips with views.)
