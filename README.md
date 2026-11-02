# CyberTech Giveaway Bot

## Environment variables
- `BOT_TOKEN`: BotFather token (keep secret)
- `ADMIN_ID`: your numeric Telegram user ID
- `CHANNEL_USERNAME`: `@CYBERTECH_HUB_BD`
- `MIN_INVITES`: default `1`
- `DB_PATH`: persistent SQLite path if supported by your host

## Commands
- `/start`
- `/myinvite`
- `/status`
- Admin only: `/giveaway 100000 BTTC | 3 | 24`

## Setup
1. Add the bot to your Telegram channel as an administrator with permission to post.
2. It must be able to check channel membership (admin status is recommended).
3. Upload these files to a private or public GitHub repository.
4. Deploy as a continuously running Python worker.
5. Set the environment variables in the host dashboard; never paste the token into public code.

## Important limitations
Referral count increases when a new Telegram account starts the bot with a user's referral link. This does not prove that the invitee joined the channel or is a unique real person. The bot cannot reliably identify every Telegram channel invite source without additional invite-link tracking. Test thoroughly before using for valuable prizes. Free hosting uptime and persistent storage are not guaranteed.
