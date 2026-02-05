# ===============================
# IMPORTS
# ===============================

import discord
from discord.ext import commands
import aiohttp
import asyncio
from conversation_handler import ConversationHandler
import asyncio


# ===============================
# CONFIG
# ===============================

OLLAMA_LOCK = asyncio.Lock()
BOT_NAMES = [""] #your discrod bot names here
OLLAMA_MODEL = "" #your Ollama model here, THIS PROJECT USES THE GENERATE API, chat api not supported!
MEMORY_FILE = "memory.enc"
BOT_NAMES = BOT_NAMES or []
ACTIVE_CHANNELS = set()
ENABLE_SAFETY = False #this is a future feature, it does not work at this time
RESPOND_TO_BOTS = True #this allows respondign to other bots, needed/used for RP servers


#soft-ban, "trolls the trolls", prevents abuse, response farming, ect
HARD_LOCK = 0.05     # absolute silence

#warning before soft-ban enacts
SOFT_LOCK = 0.15     # warning / refusal

#channel/DM chat history limit
MAX_HISTORY = 80

# ===============================
# OLLAMA SAFETY
# ===============================

OLLAMA_SEMAPHORE = asyncio.Semaphore(1)

OLLAMA_TIMEOUT = aiohttp.ClientTimeout(
    total=600,       # allow long generations
    connect=10,
    sock_read=600
)

# ===============================
# BOT SETUP
# ===============================

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True

with open("app_id.txt", "r") as f:
    APP_ID = int(f.read().strip())

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    application_id=APP_ID
)

with open("token.txt", "r", encoding="utf-8") as f:
    DISCORD_TOKEN = f.read().strip()
    ENCRYPTION_KEY = DISCORD_TOKEN.encode("utf-8")

conv_handler = ConversationHandler(MEMORY_FILE, ENCRYPTION_KEY)

# ===============================
# MOOD HELPERS
# ===============================

def analyze_mood_delta(text: str, interactions: int):
    text = text.lower()
    delta = {"confidence": 0.0, "patience": 0.0, "affection": 0.0}

    if interactions < 1:
        return delta  # grace period

    if any(w in text for w in ["thanks", "love", "cool", "nice", "awesome"]):
        delta["affection"] += 0.04
        delta["confidence"] += 0.02

    if any(w in text for w in ["your stupid", "shut up", "hate you"]):
        delta["patience"] -= 0.06
        delta["confidence"] -= 0.03

    if text.strip() in ["hi", "hello", "hey"]:
        delta["patience"] -= 0.02

    if any(w in text for w in ["sorry", "apologize", "my bad", "didn't mean"]):
        delta["patience"] += 0.08
        delta["affection"] += 0.05

    return delta


def apply_mood_decay(mood: dict):
    for k in mood:
        mood[k] = min(1.0, mood[k] + 0.01)

def locked_out_response(severity="soft"):
    if severity == "soft":
        return "…I don’t like how this is going. Let’s reset the tone."
    return

def build_prompt(history, user_prompt):
    history_text = "\n".join(
        f"{m['role']}: {m['content']}"
        for m in history
    )

    return (
        history_text
        + "\nuser: "
        + user_prompt
        + "\nassistant:"
    )



# ===============================
# EVENTS
# ===============================

@bot.event
async def on_ready():
    await bot.tree.sync()
    print("Logged in as", bot.user)
    print("Synced global slash commands.")


@bot.event
async def on_message(message):

    print("MESSAGE SEEN:", message.content)

    channel_key = (
        f"dm-{message.author.id}"
        if message.guild is None
        else str(message.channel.id)
    )
    user_id = str(message.author.id)


    # Ignore self completely
    if message.author.id == bot.user.id:
        return

    content = message.content.strip()
    if not content:
        return

    should_respond = False
    user_prompt = ""
    user_id = None
    channel_key = None

    # ---- ROUTING ----
    if message.guild is None:
        should_respond = True
        user_prompt = content
        user_id = str(message.author.id)
        channel_key = f"dm-{user_id}"

    elif bot.user.mentioned_in(message) or any(
        n in content.lower() for n in (BOT_NAMES or [])
    ):
        should_respond = True
        user_prompt = content
        user_id = str(message.author.id)
        channel_key = str(message.channel.id)

    elif message.guild and conv_handler.is_channel_active(
        str(message.guild.id), str(message.channel.id)
    ):
        should_respond = True
        user_prompt = content
        user_id = str(message.author.id)
        channel_key = str(message.channel.id)

    if not should_respond:
        return

# ---- CHANNEL CONCURRENCY GUARD ----
    if channel_key in ACTIVE_CHANNELS:
        return

# ---- HARD SAFETY GUARDS ----

    history = conv_handler.get_history(channel_key, user_id) or []
    if history is None:
        history = []

# Ignore other bots UNLESS conditions allow it
    MAX_BOT_REPLIES = 3  # you can tune this (1–3 is ideal)

    if message.author.bot:
        count = conv_handler.get_bot_reply_count(channel_key)

        if count >= MAX_BOT_REPLIES:
            print(f"[BOT LOOP GUARD] Silencing in channel {channel_key}")
            return

        # Allow bot-to-bot ONLY if your bot would normally respond

    ACTIVE_CHANNELS.add(channel_key)
    try:
        async with message.channel.typing():
            
            history = conv_handler.get_history(channel_key, user_id) or []
            interactions = len(history)

            delta = analyze_mood_delta(user_prompt, interactions)

            mood = None  # ALWAYS initialize first

            if conv_handler.is_channel_mood_enabled(channel_key):
                conv_handler.update_channel_mood(channel_key, delta)
                mood = conv_handler.get_channel_mood(channel_key)
            else:
                conv_handler.update_mood(channel_key, user_id, delta)
                mood = conv_handler.get_mood(channel_key, user_id)


            # Safety guard (prevents crash)
            if mood is None:
                print("[ERROR] mood not set — aborting reply")
                return

            apply_mood_decay(mood)
            conv_handler.apply_cooldown_recovery(mood)

              # ----------------------------
            # SOFT / HARD LOCK CHECKS
            # ----------------------------
            if mood["patience"] <= HARD_LOCK:
                return

            if mood["patience"] <= SOFT_LOCK:
                await message.channel.send(locked_out_response("soft"))
                return



            conv_handler.add_message(channel_key, "user", user_prompt, user_id)

            # Hard cap by message count (RP memory window)
            if len(history) > 80:
                history = history[-80:]

            # 2) Cap by character size (prevents huge prompts)
            while len("\n".join(m["content"] for m in history)) > 6000:
                history.pop(0)


            mood_prompt = (
                "You are [bot info].\n" #<- put bot RP info here and personality in here, replace "[bot info]"
                "Maintain a consistent emotional tone influenced subtly by prior interactions.\n"
                "Do NOT describe or quantify emotions directly.\n"
            )

            history = history[-80:]

            while len("\n".join(m["content"] for m in history)) > 6000:
                history.pop(0)


            prompt_text = mood_prompt + "\n" + build_prompt(history, user_prompt)

#========================
#ollama call block
#========================
            async with OLLAMA_LOCK:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "http://localhost:11434/api/generate", #change this to a local IP if your running Ollama on a server
                        json={
                            "model": OLLAMA_MODEL,
                            "prompt": prompt_text,
                            "stream": False,
                            "options": {
                                "num_predict": 350
                            }
                        }
                    ) as resp:
                        resp.raise_for_status()
                        data = await resp.json()


#======================================================
# ---- COMMIT PHASE: MESSAGE WAS ACTUALLY SENT ----
# (bot loop counters + memory updates belong ONLY here)
#======================================================

            raw = data.get("response")
            reply = raw.strip() if isinstance(raw, str) else ""

            if reply:
                if message.author.bot:
                    conv_handler.increment_bot_reply_count(channel_key)
                else:
                    conv_handler.reset_bot_reply_count(channel_key)

                print("[DEBUG] Sending reply:")
                print(repr(reply))
                print("ATTEMPTING SEND")
                await message.channel.send(reply)
                conv_handler.add_message(channel_key, "assistant", reply, user_id)
                print("SEND COMPLETE")

    except asyncio.CancelledError:
        print("[WARN] Ollama request cancelled (event loop pressure)")

    except Exception:
        import traceback
        print("[ERROR] on_message failure:")
        traceback.print_exc()

    finally:
        ACTIVE_CHANNELS.discard(channel_key)

    await bot.process_commands(message)

# ===============================
# SLASH COMMANDS
# ===============================

#clears chat history per-user AND per-channel
@bot.tree.command(name="reset")
async def reset(interaction: discord.Interaction):
    conv_handler.reset_channel_user(
        str(interaction.channel_id),
        str(interaction.user.id)
    )
    await interaction.response.send_message(
        "Conversation reset.", ephemeral=True
    )


#allows bot to auto-reply in a set channel, admin command
@bot.tree.command(name="activate")
@discord.app_commands.checks.has_permissions(manage_channels=True)
async def activate(interaction: discord.Interaction):
    conv_handler.activate_channel(
        str(interaction.guild.id),
        str(interaction.channel.id)
    )
    await interaction.response.send_message(
        "Channel activated.", ephemeral=True
    )


#removes the auto-reply function in a set channel, admin command
@bot.tree.command(name="deactivate")
@discord.app_commands.checks.has_permissions(manage_channels=True)
async def deactivate(interaction: discord.Interaction):
    conv_handler.deactivate_channel(
        str(interaction.guild.id),
        str(interaction.channel.id)
    )
    await interaction.response.send_message(
        "Channel deactivated.", ephemeral=True
    )

# ===============================
# RUN
# ===============================

bot.run(DISCORD_TOKEN)
