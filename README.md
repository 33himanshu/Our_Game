# Our_Game: QC Showdown

A 3D fighting game about our team, played in the browser on a computer or a phone.

Fighters: **Himanshu** ("bhaiya bhaiya"), **Aman** ("cosine similarity") and **Charan** ("galti ho gayi... of course").

## Play it

Open `index.html` through any local web server:

```bash
python3 -m http.server 8000
# then open http://127.0.0.1:8000
```

To play with a friend on another device, run the game's own server instead (it also relays the two players' moves):

```bash
uv run --python 3.12 --with aiohttp python -B server/serve_share.py . 8788
```

Then put the server on a public address (for example `cloudflared tunnel --url http://127.0.0.1:8788`), write that address into `share_url.txt`, and press **PLAY WITH A FRIEND** in the game.

## Controls

| Action | Keyboard | Phone |
|---|---|---|
| Move, jump, crouch | A / D, W, S or the arrow keys | Thumb stick: drag, flick up, pull down |
| Block | Walk away from the opponent | Same |
| Punch / Kick | J / K | PUNCH / KICK |
| Grab | I | GRAB |
| Super (full meter) | L or Space | SUPER |
| Domain expansion (full meter, once per round) | O | DOMAIN |

Combos: punch, punch, punch · punch, punch, kick · punch, kick, kick · kick, kick.

## What is in the game

- Best of three rounds against the computer, or against a friend with a room code.
- Critical hits that launch the opponent, counter hits, a rage mode at low health, and pickups that drop into the ring.
- A domain expansion for each fighter: Final QC Tribunal, Cosine Void and Galti Nagar.
- Himanshu never loses. This is on purpose.

## Files

| Path | What it is |
|---|---|
| `index.html` | The whole game: page, styles and code |
| `anim.js`, `mocap.js` | Animation clips |
| `models/` | The fighters' 3D models, packed into script files |
| `faces.js`, `faces_real.js` | Portraits for the menus |
| `server/serve_share.py` | Serves the game and relays friend play |
| `tools/` | Scripts that built the characters and animations (they expect local paths; read before running) |

The animation clips come from Quaternius' Universal Animation Library (public domain, CC0).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). In short: make a branch, open a pull request, and Himanshu reviews it before it goes in.

## Added on 26 November

| Action | Keyboard | Phone |
|---|---|---|
| Ultimate (full bar, once a match) | U | ULT |
| Domain | O | DOMAIN |
| Parry | Tap back just before a hit lands | Flick the stick back |
| Full screen | F | The ⛶ button |

- **Ultimates.** Aman's *Eightfold Cosine* is Aman's own idea and design: copies of him close a ring round the opponent, fire in turn, then all at once, and a knockout shatters the loser into glowing pieces. Himanshu's *Bhaiya Stampede* and Charan's *Galti Cascade* are built in the same shape.
- **After the match** (from Aman's pull request): the fighter nobody picked walks in beside the winner and has a word for the loser while the crowd cheers. If Charan wins he slips on a cup of chai; if he loses he walks to the corner, kneels and cries. Press Enter to skip.
- **Betting.** Play money called chai points, kept on your device. Bet on yourself, or switch on WATCH & BET and let the computer fight for your pick. Harder opponents pay more. Nothing here is real money.
- **Speed readout.** Add `?fps` to the address, or tap the round clock three times.
- Himanshu still heals and gets back up. He stays down only to a parry critical or inside the other fighter's domain.
