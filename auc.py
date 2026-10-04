# welcome to my mess of a code
import socket
import threading
import shutil
# this is meant for restarting python when logging out and the quit command
import os
import sys
from rich.console import Console
from rich.text import Text
from discord_markdown_ast_parser import parse
from urllib.parse import unquote, quote
from pathlib import Path
console = Console()

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
        password = input("password")
    elif choice == "r":
        username = input("username: ")
        password = input("password: ")
        password2 = input("repeat password: ")

        if password != password2:
            print("have you tried matching them correctly")
            exit()

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect(("104.236.25.60", 7070))

    # hello server
    s.recv(1024)

    if choice == "l":
        s.sendall(f"login|{username}|{password}\n".encode())
    elif choice == "r":
        s.sendall(f"register|{username}|{password}\n".encode())

    # login response
    response = s.recv(1024).decode().strip()

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

    # history logic
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
                message = Text(f"<{messenger}> ")
                console.print(message, end="")
                console.print(format_message(content))
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
        prefix = "/auc "
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
            s.sendall(b"history\n")
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
                    s.sendall(b"history\n")
        # motd
        elif message == prefix + "motd":
            s.sendall(b"motd|\n")
            print("\033[2J\033[H", end="")
            input()
            print("\033[2J\033[H", end="")
            set_room_header(room)

            s.sendall(b"history\n")
        # rules command because i feel like it and nobody can stop me
        elif message == prefix +"rules":
            s.sendall(b"rules\n")
            print("\033[2J\033[H", end="", flush=True)
            input()
            print("\033[2J\033[H", end="", flush=True)
            set_room_header(room)
            s.sendall(b"history\n")
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
        # no commands found
        elif message.startswith(prefix):
            console.print("unknown command")
        # normal message
        else:
            s.sendall(f"msg|{quote(message)}\n".encode())