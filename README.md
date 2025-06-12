# Ina's Discord Bot

![Ina's Bot Logo](docs/src/images/logo.png)

A playful, **New World MMO-themed** Discord bot for your server!

[![Invite Ina's Bot](https://img.shields.io/badge/Invite%20Ina's%20Bot-5865F2?style=for-the-badge&logo=discord&logoColor=white&labelColor=5865F2)](https://discord.com/oauth2/authorize?client_id=1368579444209352754&scope=bot+applications.commands&permissions=8)
[![GitHub Repo](https://img.shields.io/badge/GitHub-View%20Repo-181717?style=for-the-badge&logo=github)](https://github.com/involvex/ina-discord-bot-)
[![Docs](https://img.shields.io/badge/Docs-Project%20Page-3a5a40?style=for-the-badge&logo=readthedocs)](https://involvex.github.io/ina-discord-bot-/)
[![About New World](https://img.shields.io/badge/About%20New%20World-ffd700?style=for-the-badge&logo=amazon&logoColor=black)](https://www.newworld.com/)

---

## ✨ Features

- **New World Database Lookup:** Instantly fetch item stats, recipes, and lore from Aeternum.
- **Fun Status Rotation:** The bot cycles through witty New World-themed statuses.
- **AI-powered Chat:** Ask questions, get tips, or lore with Gemini AI integration.
- **Petpet Rituals:** Perform the legendary `/petpet` on your friends—summon magical GIFs!
- **Random GIFs:** Bring laughter to your company with trending GIFs.
- **Expedition Tools:** Handy calculators and utilities for your New World journey.
- **Fully Customizable:** Open source, easy to extend, and ready for your guild.

---

## 🚀 Invite Ina's Bot to Your Server

[**Click here to invite Ina's Bot**](https://discord.com/oauth2/authorize?client_id=1368579444209352754&scope=bot+applications.commands&permissions=8)

---

## 📚 Documentation

See the [GitHub Pages site](https://involvex.github.io/ina-discord-bot-/) for full documentation and usage instructions.

---

## 🛠️ Quickstart

```bash
pip install -U discord-py-interactions
```

```python
import interactions

bot = interactions.Client()

@interactions.listen()
async def on_startup():
    print("Bot is ready!")

bot.start("token")
```

---

_Made with ❤️ for the New World community &copy; 2025_
