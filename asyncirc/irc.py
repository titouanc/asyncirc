import asyncio
import base64
import collections
import functools
import importlib
import logging
import socket
import ssl
from blinker import signal
from .parser import RFC1459Message
loop = asyncio.get_event_loop()

plugins = []
def plugin_registered_handler(plugin_name):
    logging.getLogger("asyncirc.plugins").info("Plugin {} registered".format(plugin_name))
    plugins.append(plugin_name)

signal("plugin-registered").connect(plugin_registered_handler)

def load_plugins(*plugins):
    for plugin in plugins:
        if plugin not in plugins:
            importlib.import_module(plugin)

class User:
    def __init__(self, nick, user, host):
        self.nick = nick
        self.user = user
        self.host = host
        self.hostmask = "{}!{}@{}".format(nick, user, host)

    @classmethod
    def from_hostmask(self, hostmask):
        if "!" in hostmask and "@" in hostmask:
            nick, userhost = hostmask.split("!", maxsplit=1)
            user, host = userhost.split("@", maxsplit=1)
            return self(nick, user, host)
        return self(None, None, hostmask)

class IRCProtocol(asyncio.Protocol):

    ## Required by asyncio.Protocol

    def connection_made(self, transport):
        self.transport = transport
        self.logger = logging.getLogger("asyncirc.IRCProtocol")
        self.buf = ""
        self.nickname = ""
        self.server_supports = collections.defaultdict(lambda *_: None)
        self.caps = set()

        signal("connected").send(self)
        self.logger.info("Connection success.")

    def data_received(self, data):
        data = data.decode()

        self.buf += data
        while "\n" in self.buf:
            index = self.buf.index("\n")
            line_received = self.buf[:index].strip()
            self.buf = self.buf[index + 1:]
            signal("raw").send(self, text=line_received)

    def connection_lost(self, exc):
        self.logger.info("Connection lost; stopping event loop.")
        loop.stop()

    ## Core helper functions

    def on(self, event):
        def process(f):
            self.logger.debug("Registering function for event {}".format(event))
            signal(event).connect(f)
            return f
        return process

    def writeln(self, line):
        if not isinstance(line, bytes):
            line = line.encode()
        self.transport.get_extra_info('socket').send(line + b"\r\n")
        signal("irc-send").send(line.decode())

    def register(self, nick, user, realname, mode="+i", password=None):
        if password:
            self.writeln("PASS {}".format(password))
        self.writeln("USER {0} {1} {0} :{2}".format(user, mode, realname))
        self.writeln("NICK {}".format(nick))
        self.nickname = nick

    ## protocol abstractions

    def join(self, channels):
        if not isinstance(channels, list):
            channels = [channels]
        channels_str = ",".join(channels)
        self.writeln("JOIN {}".format(channels_str))

    def part(self, channels):
        if not isinstance(channels, list):
            channels = [channels]
        channels_str = ",".join(channels)
        self.writeln("PART {}".format(channels_str))

    def say(self, target_str, message):
        while message:
            self.writeln("PRIVMSG {} :{}".format(target_str, message[:400]))
            message = message[400:]

def get_user(hostmask):
    if "!" not in hostmask or "@" not in hostmask:
        return hostmask
    return User.from_hostmask(hostmask)

def get_channel(channel):
    return channel

def get_target(x):
    return x

## public functional API

def connect(server, port=6697, use_ssl=True):
    connector = loop.create_connection(IRCProtocol, host=server, port=port, ssl=use_ssl)
    transport, protocol = loop.run_until_complete(connector)
    return protocol

import asyncirc.plugins.core
