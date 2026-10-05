# welcome to my mess of a code
import socket
import threading
import shutil
# this is meant for restarting python when logging out and the quit command
import os
import sys
import tkinter as tk
import urllib.request
import getpass
import readline
from tkinter import filedialog
from rich.console import Console
from rich.text import Text
from discord_markdown_ast_parser import parse
from urllib.parse import unquote, quote
from pathlib import Path
from PIL import Image, ImageTk
from urllib.request import urlopen
from io import BytesIO
console = Console()

# ip

SERVER = ("104.236.25.60", 7070)
# SERVER = ("startendo.org", 7070)
# SERVER = ("192.168.1.191", 7070)

# history logic
def history():    
    s.sendall(b"history|65536|\n")
    history = b""
    s.settimeout(0.5)
    try:
        while True:
            chunk = s.recv(2048)
            if not chunk:
                break
            history += chunk
    except socket.timeout:
        pass
    s.settimeout(None)
    for line in history.decode().splitlines():
        parts = line.split("|")
        if parts[0] == "msg":
            messenger = parts[1]
            content = unquote(parts[2])
            console.print(f"<{messenger}> ", end="")
            console.print(format_message(content))

# markdown

spoilers = {}
spoiler_count = 0
def format_message(content):
    global spoiler_count
    try:
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

account_file = Path(__file__).parent / "aucaccount.txt"
# check for account file
if account_file.exists():
    username, password= account_file.read_text().splitlines()
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
    account_file.write_text(f"{username}\n{password}")

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
            message = s.recv(1024).decode()
            # format it better
            parts = message.split("|")

            if parts[0] == "msg":
                messenger = parts[1]
                content = parts[2]
                content = unquote(content)
                chatbox = readline.get_line_buffer()
                print("\r\033[2K", end="")
                message = Text(f"<{messenger}> ", end="")
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
        # gif embeds
        elif message == prefix + "image gif":
            root = tk.Tk()
            root.withdraw()
            file = filedialog.askopenfilename(
                filetypes=[("choose a gif", "*.gif")]
            )
            root.destroy()
            if file:
                with open(file, "rb") as f:
                    data = f.read()
                request = urllib.request.Request(
                    f"http://{SERVER[0]}:7080/embeds",
                    data=data,
                    headers={
                        "Authorization": f"V7 {username}|{password}|",
                        "Content-Type": "image/gif"
                    },
                    method="POST"
                ) 
                with urllib.request.urlopen(request) as response:
                    embed = response.read().decode().strip()
                message = f"http://{SERVER[0]}:7080/embeds/" + embed
                s.sendall(f"msg|{quote(message)}|\n".encode()
                )
        # png embeds
        elif message == prefix + "image png":
                    root = tk.Tk()
                    root.withdraw()
                    file = filedialog.askopenfilename(
                        filetypes=[("choose a png", "*.png")]
                    )
                    root.destroy()
                    if file:
                        with open(file, "rb") as f:
                            data = f.read()
                        request = urllib.request.Request(
                            f"http://{SERVER[0]}:7080/embeds",
                            data=data,
                            headers={
                                "Authorization": f"V7 {username}|{password}|",
                                "Content-Type": "image/png"
                            },
                            method="POST"
                        ) 
                        with urllib.request.urlopen(request) as response:
                            embed = response.read().decode().strip()
                        message = f"http://{SERVER[0]}:7080/embeds/" + embed
                        s.sendall(f"msg|{quote(message)}|\n".encode()
                        )
        elif message == prefix + "image":
            print("you gotta do /image png or gif")
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
            print("/room #[room] switches rooms\n/dm @[user] dms a user\n/motd shows the motd\n/rules shows the rules again\n/reveal spoiler[id]\n/logout logs you out and restarts the app\n/exit closes the app\n/image png uploads a png\n/image gif uploads a gif\n/whatsapp i forgor\n/shit shitting toothpaste.")

        # shit
        elif message == prefix + "shit":
            shitgif = "https://media1.tenor.com/m/7I_oY2VHBuQAAAAd/poop.gif"
            data = urlopen(shitgif).read()
            image = Image.open (BytesIO(data))
            s.sendall(f"msg|{quote("https://tenor.com/view/poop-gif-21741703")}\n".encode())
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
            
        # no commands found
        elif message.startswith(prefix):
            console.print("unknown command")
        # normal message
        else:
            s.sendall(f"msg|{quote(message)}\n".encode())