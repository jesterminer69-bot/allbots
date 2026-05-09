Profit GitHub Local Updater v1.0.0

Install folder:
  C:\Users\marcg\Documents\kraken-bot\profit-github

What it does:
  1. Reads:
       C:\Users\marcg\Documents\kraken-bot\profit-monkey-v2\status\status.json

  2. Leaves placeholders for:
       C:\Users\marcg\Documents\kraken-bot\profit-ape\status\status.json
       C:\Users\marcg\Documents\kraken-bot\profit-llama\status\status.json
       C:\Users\marcg\Documents\kraken-bot\profit-alcuna\status\status.json

  3. Creates:
       data\status.json

  4. Runs:
       git add -A
       git commit -m "Update allbots status"
       git push -u origin main

Important first-time setup:
  1. Create the GitHub repo:
       https://github.com/jesterminer69-bot/allbots

  2. Upload or copy the GitHub Pages ZIP files into:
       C:\Users\marcg\Documents\kraken-bot\profit-github

  3. Put this local updater app in the same folder:
       C:\Users\marcg\Documents\kraken-bot\profit-github

  4. Run:
       RUN_GITHUB_UPDATE_ONCE.bat

  5. If that works, run:
       RUN_GITHUB_UPDATE_LOOP.bat

Notes:
  - If the folder does not have a .git folder yet, github_update.py initializes it.
  - If origin is missing, it adds:
       https://github.com/jesterminer69-bot/allbots.git
  - If GitHub asks you to log in, use GitHub Desktop, browser login, or your normal Git credential flow.
  - Status is considered stale/idle if the source status file is more than 15 minutes old.
