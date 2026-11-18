# Clipping playbook

The working rules for this studio, in the order you need them.

## 1. Two lanes

| Lane | When | Goal | Time from moment to finished file |
|---|---|---|---|
| **Fast lane** | While the stream is live | Be first with the moment | 10 to 15 min |
| **Polish lane** | After the stream | The best 2 to 3 moments, edited properly (sound effects, zooms, story structure) | 30 to 60 min each |
| **Weekly compilation** | Once a week | "Best of the week" long video for YouTube | Reuses the best clips |

Most clips come from the fast lane. Many solid clips beat one perfect one, because many clipping campaigns cap pay per clip (example: about $1.13 per 1,000 views, with nothing extra past 50,000 views on one clip). Always check the campaign's own rules.

## 2. What makes a clip work

1. **The hook is on screen from the first frame.** Make it a question or an unfinished claim. Max about 8 words.
2. **Cold open on the peak.** Start at or just before the reaction, never at the setup.
3. **7 to 30 seconds.** Cut dead air at the start and end on the payoff.
4. **Something changes every 2 to 3 seconds:** a cut, a zoom, a caption, a reaction.
5. **Captions always.** Most people scroll muted.
6. **End on a line that loops back** to the opening when possible, so people rewatch.
7. **Exaggerate, never fabricate.** The hook can be dramatic, but it must be true to what the clip shows.

Best moment types for GTA 6, roughly in order: big streamer reactions (shock, laughing, rage), chaos and fails, NPC and physics weirdness, useful tips ("lose the cops on a jet ski"), first looks at the map and graphics, then-and-now nostalgia.

## 3. Not looking like AI

What gives a clip away as AI-made, and the rule for each:

| Giveaway | Rule |
|---|---|
| Generic word-pop captions (same font, yellow highlight, emoji after every line) | Use our caption style only. Keep the streamer's slang and misspellings. Fix only Whisper's real mistakes. |
| Titles like "unleashed", "insane moment", "you won't believe", em dashes, polished grammar | Write the way chat talks. Short. Lowercase is fine. |
| AI voiceover, AI b-roll, AI faces in thumbnails | Never. Real frames only. The only voice is the streamer's. |
| Machine-regular editing (a zoom every exact 2.0s, the same whoosh every time) | Put effects on real reactions, not on a timer. Rotate 3 to 4 sound effects. |

## 4. Credit, permission and safety (fan page clips)

1. Public streams and posts only. Skip anything deleted, private or taken down.
2. Credit every clip on screen ("Clip: kick.com/creator") and in the caption ("Clip: @creator on Kick").
3. Credit is not permission. When a creator is easy to reach, the person asks before reposting. Prefer creators who allow clipping.
4. Transform every clip: hook text, captions and our own framing. A plain re-upload gets buried. Instagram demotes unoriginal reposts, and YouTube's reused-content rule applies even with permission.
5. Take down any clip the same day if anyone asks. Log it in `01_WORKING/08_notes/takedowns.md`.
6. Never post leaks, datamined content, pirated copies or "play early" tricks.
7. Never imply we are Rockstar. Rockstar's footage policy covers non-commercial use, so the person reads it before monetizing.
8. No story spoilers in hooks, titles or thumbnails. Label story clips "SPOILER" in the caption.
9. Skip nudity frames entirely. The game is M-rated.
10. Brand safety: some streamers are chaotic. Watch the whole clip for slurs or anything that could get the account struck.

## 5. Specs

| Platform | Format | Length | Notes |
|---|---|---|---|
| TikTok | 9:16, 1080x1920 | 7 to 30s default | A few relevant hashtags |
| YouTube Shorts | 9:16, 1080x1920 | Up to 3 min, 7 to 30s default | Short caption + hashtags |
| Instagram Reels | 9:16, 1080x1920 | Under 3 min | Hook line, 1 to 2 sentences, credit, 3 to 5 hashtags |
| X | 9:16 or 16:9, 1080p | Up to 140s (non-Premium) | No hashtags |

Export: MP4, H.264, AAC, loudness around -14 LUFS. `clipit.py render` does all of this.

## 6. Writing hooks

- Say why to keep watching, not what happens. "He needed guns. Then he saw the old man" beats "Streamer finds old man in GTA 6".
- Name the streamer when they're big (xQc, Kai Cenat, Speed). Their name is the hook.
- Tips start with the payoff: "GTA 6 tip: lose the cops on a jet ski".
- Never reveal story beats.
- Write 3 options, pick the one that's most specific to this clip.
- Run every hook, title and caption past the "not looking like AI" rules above.

## 7. Learning loop

The person logs views after posting. Once there are 20 or more posted clips, look at what worked (by creator, hook style, length, moment type) and write one-line rules into `docs/decisions.md` under "What's working".
