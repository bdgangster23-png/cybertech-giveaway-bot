import os, sqlite3, random, asyncio, logging
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatMemberStatus
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN", "").strip()
CHANNEL = os.getenv("CHANNEL_USERNAME", "@CYBERTECH_HUB_BD").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
MIN_INVITES = int(os.getenv("MIN_INVITES", "1"))
DB = os.getenv("DB_PATH", "giveaway.sqlite3")
logging.basicConfig(level=logging.INFO)

def connect():
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT, referrals INTEGER DEFAULT 0)")
    c.execute("CREATE TABLE IF NOT EXISTS giveaways(id INTEGER PRIMARY KEY AUTOINCREMENT, prize TEXT, winners INTEGER, ends TEXT, status TEXT DEFAULT 'active')")
    c.execute("CREATE TABLE IF NOT EXISTS entries(gid INTEGER, uid INTEGER, PRIMARY KEY(gid,uid))")
    c.commit()
    return c

def active():
    c=connect(); r=c.execute("SELECT id,prize,winners,ends FROM giveaways WHERE status='active' ORDER BY id DESC LIMIT 1").fetchone(); c.close(); return r

async def member(context, uid):
    try:
        m=await context.bot.get_chat_member(CHANNEL, uid)
        return m.status in (ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER) or (m.status == ChatMemberStatus.RESTRICTED and m.is_member)
    except Exception:
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u=update.effective_user; c=connect()
    exists=c.execute("SELECT id FROM users WHERE id=?", (u.id,)).fetchone()
    if not exists:
        c.execute("INSERT INTO users(id,name) VALUES(?,?)",(u.id,u.first_name or ""))
        if context.args:
            try:
                ref=int(context.args[0])
                if ref != u.id: c.execute("UPDATE users SET referrals=referrals+1 WHERE id=?",(ref,))
            except ValueError: pass
    c.commit(); c.close()
    await update.message.reply_text("স্বাগতম! /myinvite দিয়ে আপনার Invite Link নিন। Giveaway পোস্টের Join বাটনে অংশ নিন।")

async def myinvite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u=update.effective_user; me=await context.bot.get_me(); c=connect()
    r=c.execute("SELECT referrals FROM users WHERE id=?",(u.id,)).fetchone(); c.close()
    await update.message.reply_text(f"আপনার Invite Link:\\nhttps://t.me/{me.username}?start={u.id}\\nInvite count: {r[0] if r else 0}")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    g=active()
    if not g: return await update.message.reply_text("এখন কোনো Giveaway চলছে না।")
    c=connect(); n=c.execute("SELECT COUNT(*) FROM entries WHERE gid=?",(g[0],)).fetchone()[0]; c.close()
    await update.message.reply_text(f"Prize: {g[1]}\\nParticipants: {n}\\nEnds (UTC): {g[3]}")

async def giveaway(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID or ADMIN_ID == 0:
        return await update.message.reply_text("শুধু অনুমোদিত Admin এই কমান্ড ব্যবহার করতে পারবেন।")
    p=[x.strip() for x in " ".join(context.args).split("|")]
    if len(p)!=3:
        return await update.message.reply_text("ব্যবহার: /giveaway 100000 BTTC | 3 | 24")
    try:
        prize, winners, hours=p[0], int(p[1]), float(p[2])
        if not prize or winners<1 or hours<=0: raise ValueError()
    except ValueError:
        return await update.message.reply_text("সঠিক ফরম্যাট দিন: /giveaway Prize | winners | hours")
    if active(): return await update.message.reply_text("আগের Giveaway এখনো চলছে।")
    end=datetime.now(timezone.utc)+timedelta(hours=hours)
    c=connect(); cur=c.execute("INSERT INTO giveaways(prize,winners,ends) VALUES(?,?,?)",(prize,winners,end.isoformat())); gid=cur.lastrowid; c.commit(); c.close()
    botname=(await context.bot.get_me()).username
    text=(f"🎁 CYBERTECH HUB BD GIVEAWAY\\n\\n🏆 Prize: {prize}\\n👑 Winners: {winners}\\n"
          f"⏰ Ends: {end.strftime('%Y-%m-%d %H:%M')} UTC\\n\\n"
          f"১. চ্যানেলে Join করুন।\\n২. /myinvite দিয়ে Invite Link নিন।\\n"
          f"৩. অন্তত {MIN_INVITES} জন নতুন ব্যবহারকারীকে আপনার লিংক দিয়ে বট Start করান।\\n"
          "৪. নিচের বাটনে Join করুন।")
    kb=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Join Giveaway",callback_data=f"join:{gid}")]])
    try:
        await context.bot.send_message(CHANNEL,text,reply_markup=kb)
        await update.message.reply_text(f"Giveaway #{gid} চ্যানেলে পোস্ট হয়েছে।")
        context.application.create_task(finish_later(context.application,gid,end))
    except Exception:
        c=connect(); c.execute("UPDATE giveaways SET status='failed' WHERE id=?",(gid,)); c.commit(); c.close()
        await update.message.reply_text("পোস্ট করা যায়নি। বটটি চ্যানেলের Admin কি না এবং CHANNEL_USERNAME ঠিক আছে কি না দেখুন।")

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    if not q.data.startswith("join:"): return
    gid=int(q.data.split(":")[1]); c=connect()
    g=c.execute("SELECT ends,status FROM giveaways WHERE id=?",(gid,)).fetchone()
    r=c.execute("SELECT referrals FROM users WHERE id=?",(q.from_user.id,)).fetchone()
    c.close()
    if not g or g[1]!="active" or datetime.now(timezone.utc)>=datetime.fromisoformat(g[0]):
        return await q.message.reply_text("এই Giveaway শেষ হয়েছে।")
    if not await member(context,q.from_user.id):
        return await q.message.reply_text(f"আগে চ্যানেলে Join করুন: https://t.me/{CHANNEL.lstrip('@')}")
    if not r or r[0]<MIN_INVITES:
        return await q.message.reply_text(f"আপনার Invite count {r[0] if r else 0}; অন্তত {MIN_INVITES} জন নতুন ব্যবহারকারীকে আপনার লিংক দিয়ে /start করান।")
    c=connect()
    try:
        c.execute("INSERT INTO entries(gid,uid) VALUES(?,?)",(gid,q.from_user.id)); c.commit()
        await q.message.reply_text("আপনি Giveaway-তে অংশ নিয়েছেন! 🎉")
    except sqlite3.IntegrityError:
        await q.message.reply_text("আপনি ইতিমধ্যে অংশ নিয়েছেন।")
    finally: c.close()

async def finish_later(app,gid,end):
    await asyncio.sleep(max(0,(end-datetime.now(timezone.utc)).total_seconds()))
    c=connect(); g=c.execute("SELECT prize,winners FROM giveaways WHERE id=? AND status='active'",(gid,)).fetchone()
    if not g: c.close(); return
    ids=[x[0] for x in c.execute("SELECT uid FROM entries WHERE gid=?",(gid,)).fetchall()]
    c.execute("UPDATE giveaways SET status='ended' WHERE id=?",(gid,)); c.commit(); c.close()
    winners=random.sample(ids,min(len(ids),g[1])) if ids else []
    if winners:
        names=[]
        for uid in winners:
            try:
                ch=await app.bot.get_chat(uid); names.append(f'<a href="tg://user?id={uid}">{ch.full_name}</a>')
            except Exception: names.append(f'<a href="tg://user?id={uid}">Winner</a>')
        msg=f"🏆 GIVEAWAY ENDED!\\nPrize: {g[0]}\\nWinner(s): {', '.join(names)}\\nঅভিনন্দন! 🎉"
    else: msg=f"Giveaway শেষ। Prize: {g[0]}\\nকোনো যোগ্য অংশগ্রহণকারী পাওয়া যায়নি।"
    await app.bot.send_message(CHANNEL,msg,parse_mode="HTML")

async def post_init(app):
    c=connect(); rows=c.execute("SELECT id,ends FROM giveaways WHERE status='active'").fetchall(); c.close()
    for gid, end in rows: app.create_task(finish_later(app,gid,datetime.fromisoformat(end)))

def main():
    if not TOKEN: raise RuntimeError("BOT_TOKEN environment variable missing")
    if not ADMIN_ID: raise RuntimeError("ADMIN_ID environment variable missing")
    app=Application.builder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start",start)); app.add_handler(CommandHandler("myinvite",myinvite))
    app.add_handler(CommandHandler("status",status)); app.add_handler(CommandHandler("giveaway",giveaway))
    app.add_handler(CallbackQueryHandler(buttons)); app.run_polling()

if __name__=="__main__": main()
