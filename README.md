Ollama-based Roleplay AI Discord Bot

A customizable, local-first Discord bot for role-playing, chatGPT, moderation, and utilities, powered by the Ollama framework.
This project allows you to run powerful Large Language Models (LLMs) on your own hardware while interacting through Discord.

Why this exists: This project was created as an attempt to replace the old Shapes.inc bots that were removed from the Discord platform.
These run independently, and you fully own them!
They can talk to other bots too!

✨ Key Features:

*   **Persistent Emotional Memory:** The bot's mood and personality evolve based on your interactions. These emotions are saved locally, so it remembers you even after a crash or power outage.
*   **True Privacy:** Uses SHA-256 encryption tied to your bot token. Only you can read your history files.
*   **Smart Context Management:** Supports separate conversation histories for every User, Channel, and DM.
*   **Flexible Activation:** Responds to its name, pings, and mentions, or works exclusively in specific channels (`/activate`).
*   **User Commands:** Includes a `/reset` command to wipe chat history and start fresh (per-user/per-channel), `/activate` to allow auto-replies in a channel, and `/deactive` desiables auto-replies in a chennel.
*   **Hardware Efficient:** Tested and confirmed to run smoothly on mid-range hardware (tested on an AMD RX 580 and 24GB RAM).

🎭 Interaction & Behavior:
The bot is designed to act as a "Human User" rather than a robotic assistant.

*   **Activation:** The bot listens for its name (as configured in `bot.py`), replies, and direct `@mentions` (pings).
*   **Mood & Tone:** Responses are dictated by its current memory state. If you are rude, the bot will remember; if you are kind, it will reciprocate.
*   **DM Support:** The bot can engage in private DMs. (Note: Outgoing DM initiation is a protected feature that requires manual configuration in the source code and no i will not say how).
*   **Memory Reset:** As stated above, use `/reset` in any channel or DM to clear the context for that specific conversation, only clears the chat history for the user who used it and in that channel.


Requirements:
1. Software

    Ollama Server: The backend engine for running LLM models. [Download from its repository:](https://github.com/ollama)
    Python 3.8+: The language powering the bot. [Download that here:](https://www.python.org/downloads/)

2. Dependencies:

    Install the required libraries via [pip:](https://pip.pypa.io/en/stable/)
    (in a terminal or powershell): pip install discord.py aiohttp


3. required Files:
    You will need to download from this repository:
    bot.py
    conversation_handler.py


Setup Instructions:

1. Configure the Code:
   
Before launching, you must edit bot.py to point to your specific Ollama model.
Open bot.py in a text editor (like notepad++ or an IDE of your choice, but notepad works too) and update the following variables:

    MODEL_NAME: Set this to the exact name of your model in Ollama on line 19.
    BOT_NAMES: add your bot's names (undercased, uppercased, capitalized, alt or shortened versions, ect) on line 18
    mood_prompt: add bot info on line 261, REPLACE "[bot info]" with your bot's charactor description, remove the [] brackets.
    ollama link is on line 280, change this to a local IP if your running the ollama server on a different machine, you can also try use an external/other AI API with this project but this is untested.
    *(change any other internal variables you have here, like mood stuff or command prefixes).*

2: Discord Authentication:

    For the bot to connect to your server, create two local text files in the root directory. ⚠️ WARNING: NEVER SHARE THESE FILES OR UPLOAD THEM TO GITHUB OR ANYWHERE!
    you need to make thses:
    token.txt: Your Discord Bot Token (found in the Discord Developer Portal), copy token and paste into a text file named "token.txt", without the quotes, spacings, or any symbols.
    app_id.txt: Your Discord Application ID (found in the Discord Developer Portal), copy APP ID and paste into a text file named "app_id", without the quotes, spacings, or any symbols.

3: Ollama Modelfile:

    Define your bot’s personality by creating a Modelfile.
    Example: FROM llama3, followed by SYSTEM "You are a helpful roleplay narrator."
    Follow the Ollama Modelfile Guide for custom instructions.
   

When your done you should have in the same folder:

    bot.py (bot itself)
    conversation_handler.py (memory system for the bot)
    token.txt (discord bot token)
    app_id.txt (for discord slash commands)
    <ollama model file> (used to create your ollama model)

Install Python Dependencies:

Before running the bot, install the necessary libraries using the [Python Package Installer (pip)](https://pip.pypa.io)
open local dir in the terminal and run: pip install -r requirements.txt

Getting Started:

    Start your Ollama server and ensure its running.
    Ensure your custom model is loaded and accessible via "ollama run <your-model-name>" in the terminal.
    Run the bot script:
        open local dir in terminal (linux/macOS) or powershell (Windows), and run: "python bot.py" without quotes

Privacy & Encryption:
This bot uses Local History Encryption (LHE) to keep your data private:

    Conversation logs are encrypted using SHA-256.
    The encryption key is generated from your unique token.txt.

    Result: ONLY you (the owner of the bot token) can decrypt and read the stored history files.

The current version is strictly a high-end text roleplay experience. If you would like to add features like **Image Generation** or additional API support, please feel free to submit a **Pull Request**!

---

⚠️ Disclaimer:

*   **AI Responses:** This bot utilizes third-party models via Ollama. The developer of this bot script is not responsible for the content generated by the AI.
*   **Safe for RP:** While the default model has built-in safeguards, users should ensure their chosen models comply with Discord's [Terms of Service](https://discord.com) and [Community Guidelines](https://discord.com).
*   **Hardware:** Running LLMs locally can generate high heat. Monitor your hardware temperatures during extended sessions.





