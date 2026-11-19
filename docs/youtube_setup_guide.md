# YouTube channel setup, step by step

From "I have the account" to "first Short is live". About 45 minutes. Everything in a grey box is ready to copy and paste.
Strategy and reasons are in `docs/youtube_strategy.md`. This file is only the clicks.

Most settings live in **YouTube Studio**: studio.youtube.com (or your profile picture on YouTube, then **YouTube Studio**).

---

## Step 1. Lock the account down (5 min)

Gaming channels get hacked a lot (fake sponsor emails with a "game file" attached).

- [ ] Turn on **2-Step Verification** on the Google account: myaccount.google.com > Security > 2-Step Verification. Use the authenticator app or a passkey, not just SMS.
- [ ] Never open a "sponsorship" attachment or download a "game demo" someone emails you.

## Step 2. Check it's a Brand Account (2 min)

A Brand Account channel can have managers added later and can be moved to another Google account. A channel created under your own name can't do either.

- [ ] In Studio, go to **Settings > Permissions**. If you can invite people there, it's a Brand Account and you're fine.
- [ ] If not, and the channel is brand new and empty, it's easiest to create a new channel now: youtube.com > profile picture > **Settings > Add or manage your channel(s) > Create a channel**. That makes a Brand Account.

## Step 3. Verify the phone (2 min)

Without this: no custom thumbnails, no videos longer than 15 minutes, no live.

- [ ] Go to **youtube.com/verify** and verify with a phone number.
- [ ] Then **Settings > Channel > Feature eligibility** should show "Intermediate features: Enabled".

## Step 4. Name and handle (5 min)

Studio > **Customization > Profile**.

Chosen name (2026-11-19): **Stream Highlights Hub**. Other options are in `docs/youtube_strategy.md` section 7.

- [x] **Name:** `Stream Highlights Hub`
- [ ] **Handle:** try these in order until one is free: `@StreamHighlightsHub`, `@StreamHighlightsHubGTA`, `@SHHclips`
- [ ] Grab the same handle on TikTok, Instagram and X today, even if you don't use them yet.

You can change the name and handle twice in 14 days, so pick carefully but don't freeze.

## Step 5. Description (2 min)

Same page, **Description**. Paste this and change the email:

```
Daily GTA 6 streamer moments, ranked and credited.

The Top 5 of the day, the funniest NPCs, the wildest chases, and the tips streamers found first. Every clip credits the streamer on screen and in the description. Go follow them.

New Shorts every day. Best of the week every Sunday.

Fan channel. Not affiliated with Rockstar Games or Take-Two.
Streamer and want a clip taken down or credited differently? Email the address on this page and it's gone the same day.
```

- [ ] **Contact info (email):** use a separate email just for this channel, not your personal one. Takedown requests and sponsor offers go here.
- [ ] **Links:** leave empty for now. Add your TikTok and Instagram once they have a few posts.

## Step 6. Picture and banner (5 min, already made)

Same page. The files are in `01_WORKING/04_templates/channel_art/`:

- [ ] **Picture:** click Change, upload `profile_picture.png` (800 x 800), keep the crop as it is, Done.
- [ ] **Banner image:** click Change, upload `banner.png` (2048 x 1152). The preview shows the TV, desktop and mobile crops; the logo and all text sit inside the mobile box. Done.
- [ ] **Video watermark:** upload `watermark_150.png`, display "End of video".
- [ ] Click **Publish** (top right).

The current art is the "control room" concept: a wall of stream tiles, "STREAM **HIGHLIGHTS** HUB" with a lime highlighter swipe, camera-viewfinder corners. It is not GTA-only (tags: GTA 6 / Gaming / IRL), because the channel covers other streaming too. The logo is a dark play button on a lime swipe inside viewfinder corners. To change the text, run `python make_channel_art.py --tagline "..." --schedule "..."` in that folder. Older concepts are kept in `v1_cartoon/`, `v2_five_star/` and `v3_sunset_hub/`.

Specs, for reference:

| Item | Size | What to put |
|---|---|---|
| Profile picture | 800 x 800 px, shows as a circle | 5 stars in a row, or "5★" in big bold type. Readable at thumbnail size. |
| Banner | 2048 x 1152 px; only the middle 1235 x 338 px shows on every device | Channel name + "GTA 6 streamer moments, daily" + "Top 5 daily · Best of the week every Sunday" |
| Video watermark (optional) | 150 x 150 px | The profile picture. Shows a subscribe button on desktop. |

Rules: your own design. No Rockstar logo, no official GTA 6 key art, no AI-generated faces. The fonts and colours should match the clips (bold white text with a black outline, yellow for accents).

## Step 7. Channel settings (5 min)

Studio > **Settings** (bottom left).

**Channel > Basic info**
- [ ] **Country of residence:** where you actually live. This drives payments and tax later, and a false country can get monetization refused. US viewers come from the content, posting times and language (Step 10), not from this setting.
- [ ] **Keywords:** paste

```
gta 6, gta vi, gta 6 streamers, gta 6 funny moments, gta 6 clips, gta 6 gameplay, gta 6 tips, leonida, vice city, xqc gta 6, asmongold gta 6, kai cenat gta 6, top 5 gta 6
```

**Channel > Advanced settings**
- [ ] **Audience:** "No, set this channel as not made for kids". The game is M-rated.

**Community > Automated filters** (optional but smart)
- [ ] Turn on "Hold potentially inappropriate comments for review".
- [ ] Blocked words: add slurs and spam words like "free robux", "telegram", "whatsapp".

## Step 8. Upload defaults (5 min, saves time on every upload)

Studio > **Settings > Upload defaults**.

**General tab**
- [ ] **Title:** leave empty.
- [ ] **Description:** paste this. You'll replace the first line per clip:

```
Clip: @CREATOR on Kick (https://kick.com/CREATOR)
Go follow CREATOR on Kick.

Daily GTA 6 streamer moments. Subscribe for the Top 5 every day.
Fan channel. Not affiliated with Rockstar Games.

#gta6 #gtavi
```

- [ ] **Visibility:** Public.
- [ ] **Tags:** paste

```
gta 6, gta vi, gta 6 gameplay, gta 6 funny moments, gta 6 streamers, gta 6 clips
```

**Advanced settings tab**
- [ ] **Video language:** English (United States).
- [ ] **Title and description language:** English (United States).
- [ ] **Category:** Gaming.
- [ ] **Comments:** On, "Hold potentially inappropriate comments for review".
- [ ] **Shorts remixing:** "Don't allow remixing". It's the streamers' footage, not ours to hand out.
- [ ] **Altered content:** No. Real stream frames only.

## Step 9. Playlists (3 min)

Studio > **Content > Playlists > New playlist**. Make these 3 now, the rest later when the series start:

| Playlist | Description |
|---|---|
| `GTA 6 Streamer Moments` | `Every GTA 6 streamer moment on the channel, newest first.` |
| `GTA 6 Launch Week` | `The first week of GTA 6, as the biggest streamers played it.` |
| `GTA 6 Top 5 Daily` | `The 5 best GTA 6 streamer moments of the day, ranked.` |

All Public. Add each upload to "Streamer Moments" + "Launch Week" this week.

## Step 10. When to post (for US viewers)

| What | When (US Eastern) | In UTC |
|---|---|---|
| Shorts, slot 1 | 12 pm to 3 pm ET | 17:00 to 20:00 UTC |
| Shorts, slot 2 | 7 pm to 10 pm ET | 00:00 to 03:00 UTC (the next day) |
| Long video | Fri to Sun, 11 am to 2 pm ET | 16:00 to 19:00 UTC |

US daylight saving ended Nov 1, so ET is UTC-5 until March. Convert to your own time zone once and write it here. If the evening slot is late at night for you, use YouTube's **Schedule** option instead of staying up. Spread 5 Shorts across both slots, at least an hour apart.

---

## Step 11. Post your first Shorts

The queue with every title and description already written is in **`02_OUTPUTS/03_post_copy/youtube_queue_2026-11-19.md`**. 32 clips in posting order, 5 a day for a week. 3 clips are marked "skip on YouTube" (fine for TikTok).

For each clip:

1. **Watch it once** with sound, start to end. Clips marked **WATCH** had short black flashes in QC; make sure they're scene cuts, not glitches.
2. Studio > **Create** (top right) > **Upload videos** > pick the `.mp4` from the path in the queue. Vertical and under 3 minutes means it's posted as a Short automatically.
3. **Details**
   - **Title:** copy from the queue.
   - **Description:** replace the whole box with the grey box from the queue. Clips marked **SPOILER** already start with "SPOILER (story scene)"; keep it.
   - **Thumbnail:** skip on desktop. For Shorts, pick the cover frame in the YouTube phone app after upload (edit video > thumbnail). Choose the frame with the biggest face reaction.
   - **Playlists:** GTA 6 Streamer Moments + GTA 6 Launch Week.
   - **Audience:** No, not made for kids (already set by your defaults).
   - **Show more:**
     - **Altered content:** No.
     - **Category:** Gaming, then in **Game title** type `Grand Theft Auto VI` and pick it if it shows up. That puts the Short on the game's page.
     - Tags, language and comments are already set by your defaults.
4. **Video elements:** nothing for now. Once the first long video is up, set **Related video** on every Short to point at it.
5. **Checks:** wait for the copyright check to finish.
   - "No issues found": go on.
   - A **Content ID claim** (usually music playing on stream): don't publish that one. Move it to the end of the queue and tell me, I'll re-cut it.
6. **Visibility:** Publish now for the first one. For the evening slot, use **Schedule**.
7. After it's live, move the `.mp4` into `02_OUTPUTS/04_posted_archive/` so the ready folder only shows what's left.

**Today (Day 1):** post the 5 clips under "Day 1" in the queue, 2 in the afternoon ET slot and 3 in the evening slot.

## Step 12. The first two days after posting

- [ ] Reply to the first comments on each Short (a short reply in your own words). Early replies help the Short get shown to more people.
- [ ] Don't delete and re-upload a Short that starts slow. Shorts often pick up after a day or two.
- [ ] After 48 hours, open each Short in Studio > **Analytics** and note **"Viewed vs. swiped away"**. Write the number in `00_TRACKER/clip_log.csv` (or tell me and I'll log it). Under about 60% viewed means the opening didn't hook, not that the moment was bad.
- [ ] Day 2: post the first **Top 5 Daily** Short. I'll compile it from the best clips with `clipit.py compile`.

---

## Later (not needed to start)

- **Home tab** (Customization > Layout): once there are playlists with videos, add "Shorts" and the "Top 5 Daily" playlist as sections.
- **Channel trailer**: skip until there's a long video worth showing.
- **Monetization** (YouTube Partner Program): needs 1,000 subscribers + 4,000 watch hours in 12 months or 10M Shorts views in 90 days. Read Rockstar's video policy before applying.
