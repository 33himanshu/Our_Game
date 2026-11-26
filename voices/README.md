# Put your real voice in the game

Record each line on your phone (Voice Memos is fine), then drop the files in your own folder here.

## File names

Folder: `voices/himanshu/`, `voices/aman/` or `voices/charan/`

| File name | When it plays |
|---|---|
| `start` | Round begins |
| `super` | Super move and domain |
| `win` | You win |
| `lose` | You lose the match |
| `taunt1`, `taunt2`, `taunt3` | Taunt button |
| `hit1`, `hit2` | Getting hit |

Any of `.m4a`, `.mp3`, `.wav`, `.ogg` works, for example `voices/aman/super.m4a`.

You do not need all of them. Any line without a recording keeps the computer voice.

## After adding files

Run this once from the game folder so the game knows which recordings exist:

```bash
python3 tools/voices.py
```

It rewrites `voices/voices.json`. Then refresh the game.

## Tips

- Keep each clip under 3 seconds and trim the silence at the start.
- Loud and silly beats clean and quiet.
