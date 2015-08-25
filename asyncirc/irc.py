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

connections = {}

plugins = []
def plugin_registered_handler(plugin_name):
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
        self._register_wait = 0

    @classmethod
    def from_hostmask(self, hostmask):
        if "!" in hostmask and "@" in hostmask:
            nick, userhost = hostmask.split("!", maxsplit=1)
            user, host = userhost.split("@", maxsplit=1)
            return self(nick, user, host)
        return self(None, None, hostmask)

class IRCProtocolWrapper:
    def __init__(self, protocol):
        self.protocol = protocol

    def __getattr__(self, attr):
        if attr in self.__dict__:
            return self.__dict__[attr]
        return getattr(self.protocol, attr)

    def __attr__(self, attr, val):
        if attr == "protocol":
            self.protocol = val
        else:
            setattr(self.protocol, attr, val)

class IRCProtocol(asyncio.Protocol):
    def connection_made(self, transport):
        self.work = True
        self.transport = transport
        self.wrapper = None
        self.logger = logging.getLogger("asyncirc.IRCProtocol")
        self.last_ping = float('inf')
        self.last_pong = 0
        self.buf = ""
        self.old_nickname = None
        self.nickname = ""
        self.server_supports = collections.defaultdict(lambda *_: None)
        self.queue = []
        self.queue_timer = 1.5
        self.caps = set()
        self.registration_complete = False
        self.channels_to_join = []

        signal("connected").send(self)
        self.logger.info("Connection success.")
        self._register()
        self.process_queue()

    def data_received(self, data):
        if not self.work: return
        data = data.decode()

        self.buf += data
        while "\n" in self.buf:
            index = self.buf.index("\n")
            line_received = self.buf[:index].strip()
            self.buf = self.buf[index + 1:]
            self.logger.debug(line_received)
            signal("raw").send(self, text=line_received)

    def connection_lost(self, exc):
        if not self.work: return
        self.logger.critical("Connection lost.")
        signal("connection-lost").send(self.wrapper)

    ## Core helper functions

    def process_queue(self):
        if not self.work: return
        if self.queue:
            self._writeln(self.queue.pop(0))
        loop.call_later(self.queue_timer, self.process_queue)

    def on(self, event):
        def process(f):
            self.logger.debug("Registering function for event {}".format(event))
            signal(event).connect(f)
            return f
        return process

    def _writeln(self, line):
        if not isinstance(line, bytes):
            line = line.encode()
        self.transport.get_extra_info('socket').send(line + b"\r\n")
        signal("irc-send").send(line.decode())

    def writeln(self, line):
        """
        Queue a message for sending to the currently connected IRC server.
        """
        self.queue.append(line)
        return self

    def register(self, nick, user, realname, mode="+i", password=None):
        """
        Queue registration with the server. This includes sending nickname,
        ident, realname, and password (if required by the server).
        """
        self.nick = nick
        self.user = user
        self.realname = realname
        self.mode = mode
        self.password = password
        return self

    def _register(self):
        if self.password:
            self.writeln("PASS {}".format(self.password))
        self.writeln("USER {0} {1} {0} :{2}".format(self.user, self.mode, self.realname))
        self.writeln("NICK {}".format(self.nick))
        signal("registration-complete").send(self)
        self.nickname = self.nick

    ## protocol abstractions

    def join(self, channels):
        """
        Join channels. Pass a list to join all the channels, or a string to
        join a single channel. If registration with the server is not yet
        complete, this will queue channels to join when registration is done.
        """
        if not isinstance(channels, list):
            channels = [channels]
        channels_str = ",".join(channels)

        if not self.registration_complete:
            self.channels_to_join.append(channels_str)
        else:
            self.writeln("JOIN {}".format(channels_str))

        return self

    def part(self, channels):
        """
        Leave channels. Pass a list to leave all the channels, or a string to
        leave a single channel. If registration with the server is not yet
        complete, you're dumb.
        """
        if not isinstance(channels, list):
            channels = [channels]
        channels_str = ",".join(channels)
        self.writeln("PART {}".format(channels_str))

    def say(self, target_str, message):
        while message:
            self.writeln("PRIVMSG {} :{}".format(target_str, message[:400]))
            message = message[400:]

    ## catch-all

    def __getattr__(self, attr):
        if attr in self.__dict__:
            return self.__dict__[attr]

        def _send_command(*args):
            argstr = " ".join(args[:-1]) + " :{}".format(args[-1])
            self.writeln("{} {}".format(attr.upper(), argstr))

        _send_command.__name__ == attr
        return _send_command

def get_user(hostmask):
    if "!" not in hostmask or "@" not in hostmask:
        return hostmask
    return User.from_hostmask(hostmask)

def get_channel(channel):
    return channel

def get_target(x):
    return x

def connect(server, port=6697, use_ssl=True):
    connector = loop.create_connection(IRCProtocol, host=server, port=port, ssl=use_ssl)
    transport, protocol = loop.run_until_complete(connector)
    protocol.wrapper = IRCProtocolWrapper(protocol)
    protocol.server_info = {"host": server, "port": port, "ssl": use_ssl}
    protocol.net_id = "{}:{}:{}{}".format(id(protocol), server, port, "+" if use_ssl else "-")
    connections[protocol.net_id] = protocol.wrapper
    return protocol.wrapper

def disconnected(client_wrapper):
    logger.critical("Disconnected")

signal("connection-lost").connect(disconnected)

import asyncirc.plugins.core
