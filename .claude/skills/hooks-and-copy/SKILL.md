---
name: hooks-and-copy
description: Write the on-screen hook, the title and the caption for a clip so it reads like a person wrote it, credits the creator and never spoils the story. Use whenever a hook, title, caption or hashtags are needed.
---

# Hooks and post copy

Read `docs/playbook.md` sections 3 (not looking like AI) and 6 (writing hooks) first.

## The on-screen hook

- 8 words max. It shows for the whole clip, so it must read in one glance.
- Say why to keep watching: a question, an unfinished claim, or the streamer's name plus the situation.
- True to what the clip shows. Exaggeration is fine, invention is not.
- No story spoilers, no character deaths, no mission twists.
- No emoji in the on-screen hook (the font can't draw them).

Good: "GTA 6 made xQc build furniture", "He needed guns. Then he saw the old man", "GTA 6 tip: lose the cops on a jet ski".
Bad: "INSANE GTA 6 MOMENT 🤯", "You won't believe what happens next", "Unleashing chaos in Vice City".

Write 3 options in your head, keep the most specific one.

## The caption file

`clipit.py render` writes a draft in `02_OUTPUTS/03_post_copy/<date>/<clip>.txt`. Edit it to this shape:

```
<hook, or a slightly longer version of it>

Clip: @<creator> on <Kick/Twitch/YouTube>

#gta6 #gtavi #<creator> #<one topical tag>
```

Per platform (the person copies the right part):

- **TikTok / Shorts:** the text above, 3 to 5 hashtags.
- **Instagram:** hook line, one or two sentences of context, credit, 3 to 5 hashtags.
- **X:** hook line and credit only, no hashtags.

## Voice check (do this every time)

- No em dashes. No "unleash", "insane", "epic", "you won't believe", "game-changer", "dive in".
- Short sentences, the way chat talks. Lowercase is fine.
- At most one emoji, and only in the caption, never in the hook.
- If the `ig-human` or a "humanizer" skill is available, run the caption through it.
- Story clips get "SPOILER" at the start of the caption.
