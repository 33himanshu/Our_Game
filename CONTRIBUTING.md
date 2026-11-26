# How to add something to the game

Every change is looked at before it becomes part of the game. Nothing goes straight into `main`.

## Steps

1. Get the latest version.
   ```bash
   git checkout main
   git pull
   ```
2. Make a branch named after what you are adding.
   ```bash
   git checkout -b add-new-stage
   ```
3. Make your change and try it in the browser, on a computer and on a phone-sized window.
   ```bash
   python3 -m http.server 8000
   ```
4. Commit and push your branch.
   ```bash
   git add -A
   git commit -m "Add a new stage: the canteen"
   git push -u origin add-new-stage
   ```
5. Open a pull request on GitHub. Say what you changed and how you tested it. A screenshot or a short clip helps a lot.
6. Himanshu reviews it. He may ask for changes. Once he approves, it is merged into `main`.

## Good to know

- Almost all the code is in `index.html`. Search for the section headers (lines starting with `// ----`) to find your way around.
- Keep one idea per pull request. Small pull requests get reviewed faster.
- Do not commit passwords, tokens or anyone's private photos.
- The game must keep working on phones. If you add a control, add a touch button for it too.
