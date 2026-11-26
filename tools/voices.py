"""Lists the recorded voice lines so the game can find them. Run from the game folder: python3 tools/voices.py"""
import json, os, sys
root = sys.argv[1] if len(sys.argv) > 1 else 'voices'
names = {'start', 'super', 'win', 'lose', 'taunt1', 'taunt2', 'taunt3', 'hit1', 'hit2'}; out = {}
for who in ('himanshu', 'aman', 'charan'):
    d = os.path.join(root, who)
    for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        stem, ext = os.path.splitext(f)
        if ext.lower() in ('.m4a', '.mp3', '.wav', '.ogg') and stem in names: out[who + '/' + stem] = who + '/' + f
        elif ext.lower() in ('.m4a', '.mp3', '.wav', '.ogg'): print('skipped (name not recognised):', os.path.join(who, f))
json.dump(out, open(os.path.join(root, 'voices.json'), 'w'), indent=1); print(len(out), 'recorded lines listed in', os.path.join(root, 'voices.json'))
