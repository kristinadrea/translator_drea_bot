# Oracle Operations

This file is a quick reminder for maintaining the translator bot on the Oracle Always Free VM.

## Server

```text
Host: 141.253.112.50
SSH user: opc
SSH key: ../castaneda_drea_bot/secrets/oracle-drea.key
Project path: /opt/translator_drea_bot
Service: translator-drea-bot
```

## Update Bot Code On Oracle

First commit and push changes from the local project to GitHub:

```bash
git status
git add .
git commit -m "Describe your change"
git push
```

Then deploy the latest GitHub code to Oracle:

```bash
ssh -i ../castaneda_drea_bot/secrets/oracle-drea.key opc@141.253.112.50 'cd /opt/translator_drea_bot && git pull && .venv/bin/pip install -r requirements.txt && sudo systemctl restart translator-drea-bot && sudo systemctl status translator-drea-bot --no-pager'
```

## Useful Server Commands

These are the main day-to-day commands for the second bot.

Open an SSH session:

```bash
ssh -i ../castaneda_drea_bot/secrets/oracle-drea.key opc@141.253.112.50
```

Check bot status:

```bash
sudo systemctl status translator-drea-bot --no-pager
```

Restart bot:

```bash
sudo systemctl restart translator-drea-bot
```

Stop bot:

```bash
sudo systemctl stop translator-drea-bot
```

Start bot again:

```bash
sudo systemctl start translator-drea-bot
```

Watch live logs:

```bash
sudo journalctl -u translator-drea-bot -f
```

Show recent logs:

```bash
sudo journalctl -u translator-drea-bot -n 100 --no-pager
```

Check that both bots are running:

```bash
systemctl is-active castaneda-drea-bot
systemctl is-active translator-drea-bot
```

## After Changing Local Settings

If you change `.env` locally, copy it to Oracle and restart the bot:

```bash
scp -i ../castaneda_drea_bot/secrets/oracle-drea.key .env opc@141.253.112.50:/opt/translator_drea_bot/.env
ssh -i ../castaneda_drea_bot/secrets/oracle-drea.key opc@141.253.112.50 'sudo systemctl restart translator-drea-bot && sudo systemctl status translator-drea-bot --no-pager'
```
