# xbook

Forked from https://github.com/fistaco/xbook, xbook is a CLI utility to allow users to quickly book a gym slot at TU Delft's X. This version is much restricted than the original fork, in that it only focuses on booking a gym slot for non TU Delft members.

As an additional feature, if the tool finds a valid `credentials.json` containing access to a google service account, it will attempt to create an event in your calendar.

## Quickstart

### Pre-Requisites
- Make sure you have [uv](https://docs.astral.sh/uv/getting-started/installation/) installed and available in your commandline.
- (Optional) If you don't want the tool to prompt for your username and password everytime, you can export the values to `X_USERNAME` and `X_PASSWORD` environment variables in your shell.

You can then clone the repository and run the tool like so.

```bash
git clone https://github.com/gauthsvenkat/xbook.git
cd xbook
uv run xbook
```
