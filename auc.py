# welcome to my mess of a code
import socket
import threading
import shutil
# this is meant for restarting python when logging out and the quit command
import os
import sys
import tkinter as tk
import getpass
import readline
import signal
import shlex
from tkinter import filedialog
from rich.console import Console
from rich.text import Text
from discord_markdown_ast_parser import parse
from urllib.parse import unquote, quote
from pathlib import Path
from PIL import Image, ImageTk
from urllib.request import Request, urlopen
from io import BytesIO
from datetime import datetime
console = Console()

# ip

#SERVER = ("104.236.25.60", 7070)
#SERVER = ("startendo.org", 7070)
SERVER = ("144.217.26.87", 7070)
#SERVER = ("192.168.1.191", 7070)
#SERVER = ("localhost", 7070)
#SERVER = ("10.246.54.25", 7070)

# history logic
pissity = threading.Lock()
def history():    
    data = b""
    with pissity:
        s.sendall(b"history|65536|\n")
        s.settimeout(0.5)
        try:
            while True:
                chunk = s.recv(2048)
                if not chunk:
                    break
                data += chunk
        except socket.timeout:
            pass
        finally:
            s.settimeout(0.1)
    for line in data.decode().splitlines():
        parts = line.split("|")
        if parts[0] == "msg":
            messenger = parts[1]
            if messenger.lower() in muted_users:
                continue                
            content = unquote(parts[2])
            timestamp = int(parts[3])
            time = datetime.fromtimestamp(timestamp).strftime("%H:%M")
            console.print(f"[{time}] <{messenger}> ", end="")
            console.print(format_message(content))

# markdown

spoilers = {}
spoiler_count = 0
def format_message(content):
    global spoiler_count
    try:
        content = content.replace(f"@{username}", f"**@{username}**")
        parsed = parse(content)
    except Exception:
        return Text(content)
    text = Text()

    for node in parsed:
        if node.node_type.name == "TEXT":
            text.append(node.text_content)
        elif node.node_type.name == "BOLD":
            text.append(node.children[0].text_content, style="bold")
        elif node.node_type.name == "ITALIC":
            text.append(node.children[0].text_content, style="italic")
        elif node.node_type.name == "STRIKETHROUGH":
            text.append(node.children[0].text_content, style="strike")
        elif node.node_type.name == "CODE_BLOCK":
            width = max(len(line) for line in node.children[0].text_content.splitlines()) + 10
            for line in node.children[0].text_content.splitlines():
                text.append(line.ljust(width), style="white on grey23")
                text.append("\n")
        elif node.node_type.name == "CODE_INLINE":
            text.append(node.children[0].text_content, style="white on grey23")
        elif node.node_type.name in ("URL_WITH_PREVIEW", "URL_WITHOUT_PREVIEW"):
            text.append(node.url)
        elif node.node_type.name == "SPOILER":
            spoiler_count += 1
            spoiler_id = f"SPOILER{spoiler_count}"
            spoilers[spoiler_id] = node.children[0].text_content
            text.append(f"[{spoiler_id}]", style="dim")
    return text

# room information at the top of the screen
def set_room_header(room):
    rows = shutil.get_terminal_size().lines

    print("\033[2J", end="")
    if room.startswith("@"):
        print(f"\033[1;1H\033[2K{room}", end="")
    else:
        print(f"\033[1;1H\033[2K#{room}", end="")
    print(f"\033[2;{rows}r", end="")
    print("\033[2;1H", end="")

# muted user saving

mute_list = Path(__file__).parent / "mutedusers.txt"
if mute_list.exists():
    muted_users = {
        line.strip().lower()
        for line in mute_list.read_text().splitlines()
        if line.strip()
    }
else:
    muted_users = set()

def keep_muted():
    mute_list.write_text("\n".join(sorted(muted_users)) + ("\n" if muted_users else ""))

# account
account_file = Path(__file__).parent / "aucaccount.txt"

accounts = {}
# check for account file
if account_file.exists():
    account_data = account_file.read_text().splitlines()
    for i in range(0, len(account_data) - 2, 3):
        accounts[account_data[i]] = (
            account_data[i + 1],
            account_data[i + 2]
        )

# server sign in logic

if SERVER[0] not in accounts:
    if "startendo.org" in accounts:
        accounts[SERVER[0]] = accounts["startendo.org"]
    elif "104.236.25.60" in accounts:
        accounts[SERVER[0]] = accounts["104.236.25.60"]

accounts.pop("startendo.org", None)
accounts.pop("104.236.25.60", None)

if SERVER[0] in accounts:
    username, password= accounts[SERVER[0]]
    choice = "l"
else:
    choice = input("[L]ogin or [R]egister: ").lower()

    if choice == "l":
        username = input("username: ")
        password = getpass.getpass("password: ")
    elif choice == "r":
        username = input("username: ")
        password = getpass.getpass("password: ")
        password2 = getpass.getpass("repeat password: ")

        if password != password2:
            print("have you tried matching them correctly")
            exit()

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    try:
        s.connect(SERVER)
    except ConnectionRefusedError:
        print("failed to connect (servers probably down)")
        exit()

    os.system('clear')

    # hello server
    response = s.recv(1024).decode().strip()
    parts = response.split("|")
    if not response.startswith("hello|"):
        if parts[0] == "err":
            if parts[1] == "unknown_internal":
                print("unknown server error")
                exit()
        print(response)
        exit()

    if choice == "l":
        s.sendall(f"login|{username}|{password}\n".encode())
    elif choice == "r":
        s.sendall(f"register|{username}|{password}\n".encode())

    # login response
    response = s.recv(1024).decode().strip()
    parts = response.split("|")
    if response != "ok|":
        if parts[0] == "err":
            if parts[1] == "banned":
                if parts[2]:
                    print(f"you were banned for: {parts[2]}")
                else:
                    print("you were banned with no reason")
                exit()
            elif parts[1] == "user_exists":
                print("choose a different user (err|user_exists|)")
                exit()
            elif parts[1] == "bad_login":
                print("wrong user or password twih 💔 (err|bad_login|)")
                exit()
            elif parts[1] == "register_disabled":
                print("registers are disabled (err|register_disabled|)")
                exit()

    
    if response != "ok|":
        print(response)
        exit()
    # account server saving
    accounts[SERVER[0]] = (username, password)
    account_data = []
    for server, account in accounts.items():
        account_data.extend([server, account[0], account[1]])
    account_file.write_text("\n".join(account_data) + "\n")

    # rules
    s.sendall(b"rules\n")
    data = b""
    while not data.endswith(b"\n"):
        data += s.recv(1024)
    rules = data.decode()
    parts = rules.split("|", 2)
    if parts[0] == "rules":
        rules = unquote(parts[1])
        print("\033[2J\033[H", end="")
        console.print(rules)
        input("\npress enter to continue")

    # join room when logged in
    room = "general"
    s.sendall(b"join|general\n")
    set_room_header(room)
    history()

    # messages
    def receive_messages():
        while True:
            try:
                with pissity:
                    message = s.recv(1024).decode()
            except socket.timeout:
                continue
            except OSError:
                break
            # format it better
            parts = message.split("|")

            if parts[0] == "msg":
                messenger = parts[1]
                if messenger.lower() in muted_users:
                    continue
                content = parts[2]
                timestamp = int(parts[3])
                content = unquote(content)
                time = datetime.fromtimestamp(timestamp).strftime("%H:%M")
                chatbox = readline.get_line_buffer()
                print("\r\033[2K", end="")
                message = Text(f"[{time}] <")
                if "[DISCORD]" in messenger:
                    username, tag = messenger.split("[DISCORD]", 1)
                    message.append(username)
                    message.append("[DISCORD]", style="blue")
                else:
                    message.append(messenger)
                message.append("> ")
                console.print(message, end="")
                console.print(format_message(content))
                print(chatbox, end="", flush=True)
            # display motd
            elif parts[0] == "motd":
                content = unquote(parts[1])
                console.print(content)
            # display rules
            elif parts[0] == "rules":
                content = unquote(parts[1])
                console.print(content)
    threading.Thread(target=receive_messages, daemon=True).start()


    # message box
    while True:
        message = input("")
        print("\033[1A\033[2K", end="")
        # commands
        prefix = "/"
        # room switching
        if message.startswith(prefix +"room #"):
            command = "room"
        elif message.startswith(prefix + "join #"):
            command = "room"
        else:
            command = ""

        if command == "room":
            if message.startswith(prefix + "room #"):
                room = message[len(prefix + "room #"):].strip()
            elif message.startswith(prefix + "join #"):
                room = message[len(prefix + "join #"):].strip()
            set_room_header(room)
            s.sendall(f"join|{room}\n".encode())
            history()
        # dms
        elif message.startswith(prefix + "dm @"):
            dm_user = message[len(prefix + "dm @"):].strip()
            if dm_user:
                if dm_user.lower() == username.lower():
                    console.print("why would you want to dm yourself")
                else:
                    room = "@" + dm_user
                    set_room_header(room)
                    s.sendall(f"join|{room}\n".encode())
        # motd
        elif message == prefix + "motd":
            s.sendall(b"motd|\n")
            print("\033[2J\033[H", end="")
            input()
            print("\033[2J\033[H", end="")
            set_room_header(room)
            history()
        # rules command because i feel like it and nobody can stop me
        elif message == prefix +"rules":
            s.sendall(b"rules\n")
            print("\033[2J\033[H", end="", flush=True)
            input()
            print("\033[2J\033[H", end="", flush=True)
            set_room_header(room)
            history()
        # spoiler revealing
        elif message.startswith(prefix + "reveal "):
            spoiler_id = message[len(prefix + "reveal "):].upper()
            if spoiler_id in spoilers:
                console.print(spoilers[spoiler_id])
            else:
                console.print("there's no spoiler id with that")
        # logout
        elif message == prefix + "logout":
            if account_file.exists():
                account_file.unlink()
            os.execv(sys.executable, [sys.executable] + sys.argv)
        # exit
        elif message == prefix + "exit":
            s.close()
            sys.exit()
        # embeds
        elif message == prefix + "image":
            root = tk.Tk()
            root.withdraw()
            file = filedialog.askopenfilename(
                filetypes=[("images", "*.gif *.png *.jpg *.jpeg *.webp *.bmp")]
            )
            root.destroy()
            if file:
                extension = Path(file).suffix.lower()
                if extension == ".gif":
                    apple = "image/gif"
                elif extension == ".png":
                    apple = "image/png"
                elif extension in (".jpg", ".jpeg", ".bmp", ".webp"):
                    convert_dir = Path(__file__).parent / "convert"
                    convert_dir.mkdir(exist_ok=True)
                    yesconvert = convert_dir / f"{Path(file).stem}.png"
                    command = (
                        f"ffmpeg -v error -y -i {shlex.quote(file)} "
                        f"{shlex.quote(str(yesconvert))}"
                    )
                    if os.system(command) != 0:
                                console.print("uh oh stinky")
                                yesconvert.unlink(missing_ok=True)
                                continue
                    file = str(yesconvert)
                    apple = "image/png"
                else:
                    print("this isnt supported or i havent bothered to add support yet")
                    continue
                with open(file, "rb") as f:
                    data = f.read()
                request = Request(
                    f"http://{SERVER[0]}:7080/embeds",
                    data=data,
                    headers={
                        "Authorization": f"V7 {username}|{password}|",
                        "Content-TYpe": apple
                    },
                    method="POST"
                )
                with urlopen(request) as response:
                    embed = response.read().decode().strip()
                message = f"http://{SERVER[0]}:7080/embeds/" + embed
                s.sendall(f"msg|{quote(message)}|\n".encode())
        # whatsapp
        elif message == prefix + "whatsapp":
            whatsapp = Path(__file__).parent / "whatsapp.jpg"
            root = tk.Tk()
            root.title("WhatsApp")
            image = Image.open(whatsapp)
            photo = ImageTk.PhotoImage(image)
            label = tk.Label(root, image=photo)
            label.pack()
            root.mainloop()
        # help
        elif message == prefix + "help":
            print("/room #[room] switches rooms\n/dm @[user] dms a user\n/motd shows the motd\n/rules shows the rules again\n/reveal spoiler[id]\n/logout logs you out and restarts the app\n/exit closes the app\n/image png uploads a png\n/image gif uploads a gif\n/whatsapp i forgor\n/shit shitting toothpaste.\n/orstando converts the code to orstandos code\n/mute mutes a user\n/unmute unmutes a user")
        # shit
        elif message == prefix + "shit" or message == "s!shit":
            shitgif = "https://media1.tenor.com/m/7I_oY2VHBuQAAAAd/poop.gif"
            data = urlopen(shitgif).read()
            image = Image.open (BytesIO(data))
            s.sendall(f"msg|{quote("s!shit https://tenor.com/view/poop-gif-21741703")}\n".encode())
            window = tk.Tk()
            window.title("s!shit")
            frames = []
            try:
                while True:
                    frame = ImageTk.PhotoImage(image.copy())
                    frames.append(frame)
                    image.seek(len(frames))
            except EOFError:
                pass
            label = tk.Label(window)
            label.pack()
            after_id = None
            def animate(frame=0):
                global afterid
                label.config(image=frames[frame])
                afterid = window.after(100, animate, (frame + 1) % len(frames))
            def windowclose():
                if afterid is not None:
                    window.after_cancel(afterid)
                window.destroy()
            window.protocol("WM_DELETE_WINDOW", windowclose)
            animate()
            window.mainloop()
        # orstando
        elif message == prefix + "orstando":
            print("im gonna segfault")
            os.kill(os.getpid(), signal.SIGSEGV)
        # goog...
        elif message == prefix + "goog":
            data = urlopen(Request("https://static2.klipy.com/ii/a8ada81afc59159ea5c8927feffa2e31/2a/d9/Zf6EfGvoabz5t0zDzf1.gif", headers={"User-Agent": "Mozilla/5.0"})).read()
            image = Image.open(BytesIO(data))
            window = tk.Tk()
            window.title("goog")
            frames = []
            try:
                while True:
                    frame = ImageTk.PhotoImage(image.copy())
                    frames.append(frame)
                    image.seek(len(frames))
            except EOFError:
                pass
            label = tk.Label(window)
            label.pack()
            after_id = None
            def animate(frame=0):
                global after_id
                label.config(image=frames[frame])
                after_id = window.after(100, animate, (frame + 1) % len(frames))
            def windowclose():
                if after_id is not None:
                    window.after_cancel(after_id)
                window.destroy()
            window.protocol("WM_DELETE_WINDOW", windowclose)
            animate()
            window.mainloop()
        # mute
        elif message.startswith(prefix + "mute @"):
            muted_user = message[len(prefix + "mute @"):].strip().lower()
            if muted_user:
                muted_users.add(muted_user)
                keep_muted()
                console.print(f"muted {muted_user}")
        # unmute
        elif message.startswith(prefix + "unmute @"):
            muted_user = message[len(prefix + "unmute @"):].strip().lower()
            if muted_user in muted_users:
                muted_users.remove(muted_user)
                keep_muted()
                console.print(f"unmuted {muted_user}")
            else:
                console.print("wrong username twih")
        elif message == prefix + "mute":
            console.print("you need to do @username")
        # no commands found
        elif message.startswith(prefix):
            console.print("unknown command")
        # normal message
        else:
            s.sendall(f"msg|{quote(message)}\n".encode())
