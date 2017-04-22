#!/usr/bin/env python3

import socket
import threading
import queue
import random
import time

# Config
HOST = "example.com"
PORT = 6667
NICK = "bot"
CHANS = ["#test"]
OPS = ["me"]
DEBUG = True
FORTUNES = open("fortunes.txt", "r").read().strip().split("\n")
DELAY = 0.1 # reading & sending new messages

# Handlers
def handle_PING(bot):
    bot.send("PONG %s" % bot.params)

def handle_376(bot):
    for chan in CHANS:
        bot.send("JOIN %s" % chan)

def handle_JOIN(bot):
    nick = bot.src[1:bot.src.index("!")]
    if nick in OPS:
        bot.send("MODE %s +o %s" % (bot.params, nick))
    else:
        if nick != NICK:
            bot.send_msg(bot.params, "Cześć %s!" % nick)

def handle_PRIVMSG(bot):
    chan, msg = bot.params.split(" ", 1)
    msg = msg[1:]
    if msg in msg_handles:
        bot.send_msg(chan, msg_handles[msg]())

def handle_KICK(bot):
    chan, nick, params = bot.params.split(" ", 2)
    if nick == NICK and chan in CHANS:
        time.sleep(5)
        bot.send("JOIN %s" % chan)

handles = {
    "PING": handle_PING,
    "376": handle_376,
    "JOIN": handle_JOIN,
    "PRIVMSG": handle_PRIVMSG,
    "KICK": handle_KICK
}

def msg_handle_fortune():
    return random.choice(FORTUNES)

msg_handles = {
    "!fortune": msg_handle_fortune
}

# Magic. It works because of magic. Don't touch it.
class IrcSocket(socket.socket):
    def __init__(self, *attr):
        super().__init__(*attr)

    def recvuntil(self, txt):
        result = b""
        while result.find(txt) == -1:
            try:
                char = self.recv(1)
                if len(char) == 0:
                    return False
            except socket.error as msg:
                print(msg)
                return False
            result += char
        return result


class ReciverThread(threading.Thread):
    def __init__(self, socket, queue):
        super().__init__()
        self.socket = socket
        self.queue = queue

    def run(self):
        while True:
            msg = str(self.socket.recvuntil(b"\n").strip(), "utf-8")
            self.queue.put(msg)

class IrcBot:
    def __init__(self):
        self.socket = IrcSocket(socket.AF_INET, socket.SOCK_STREAM)
        self.queue = queue.Queue()
        self.reciver = ReciverThread(self.socket, self.queue)
        self.reciver.daemon = False

    def start(self):
        self.socket.connect((HOST, PORT))
        self.reciver.start()

        self.send("NICK %s" % NICK)
        self.send("USER %s %s %s :%s" % (NICK, NICK, NICK, NICK))

        while True:
            try:
                msg = self.queue.get(timeout=DELAY)
                msg_splited = msg.split(" ", 2)
                if len(msg_splited) == 2:
                    msg_splited.insert(0, "")
                self.src, self.cmd, self.params = msg_splited
                if DEBUG:
                    print("RECIVED: %s %s %s" % (self.src, self.cmd, self.params))
                self.runHandle()
            except queue.Empty:
                pass

    def runHandle(self):
        if self.cmd in handles:
            handles[self.cmd](self)

    def send(self, msg):
        msg_utf = bytes(msg + "\r\n", "utf-8")
        if DEBUG:
            print("SEND: %s" % msg)
        self.socket.sendall(msg_utf)

    def send_msg(self, chan, msg):
        self.send("PRIVMSG %s :%s" % (chan, msg))

if __name__ == "__main__":
    bot = IrcBot()
    bot.start()
