import asyncio
import base64
import functools
import logging
import socket
import ssl
from blinker import signal
from .parser import RFC1459Message
loop = asyncio.get_event_loop()

class User:
    def __init__(self, nick, user, host):
        self.nick = nick
        self.user = user
        self.host = host

    @classmethod
    def from_hostmask(self, hostmask):
        if "!" in hostmask and "@" in hostmask:
            nick, userhost = hostmask.split("!", maxsplit=1)
            user, host = userhost.split("@", maxsplit=1)
            return self(nick, user, host)
        return self(None, None, hostmask)

class CapFailedException(Exception): pass
class AuthenticationFailedException(Exception): pass

class IRCProtocol(asyncio.Protocol):

    ## Required by asyncio.Protocol

    def connection_made(self, transport):
        self.transport = transport
        self.logger = logging.getLogger("asyncirc.IRCProtocol")
        self.buf = ""
        self.nickname = ""

        self.logger.info("Connection success.")
        self.attach_default_listeners()

    def data_received(self, data):
        self.logger.debug("data_received called")
        data = data.decode()
        self.logger.debug("Received: \"{}\"".format(data))

        self.buf += data
        while "\n" in self.buf:
            index = self.buf.index("\n")
            line_received = self.buf[:index].strip()
            self.buf = self.buf[index + 1:]
            self.logger.debug("Line received: \"{}\"".format(line_received))
            message = RFC1459Message.from_message(line_received)
            message.client = self
            signal("irc").send(message)
            signal("irc-{}".format(message.verb.lower())).send(message)

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

    ## Default listeners

    def attach_default_listeners(self):
        signal("irc-ping").connect(_pong)
        signal("irc-privmsg").connect(_redispatch_privmsg)
        signal("irc-notice").connect(_redispatch_notice)
        signal("irc-cap").connect(_handle_cap)

    ## protocol abstractions

    def join(self, channels):
        if not isinstance(channels, list):
            channels = [channels]
        channels_str = ",".join(channels)
        self.writeln("JOIN {}".format(channels_str))

## cap handlers
def _handle_cap(message):
    result = message.params[1].lower()
    cap = message.params[2].lower()
    if result != "ack":
        raise CapFailedException("Capability negotiation for {} failed".format(cap))
    message.client.logger.info("Capability negotiation for {} succeeded".format(cap))
    signal("cap-success", cap)

## default listener functions

def _pong(message):
    message.client.logger.debug("Responding to PING")
    message.client.writeln("PONG {}".format(message.params[0]))

def _redispatch_message_common(message, type):
    target, text = message.params
    user = User.from_hostmask(message.source)
    signal(type).send(message.client, user=user, target=target, text=text)
    if target == message.client.nickname:
        signal("private-{}".format(type)).send(message.client, user=user, target=target, text=text)
    else:
        signal("public-{}".format(type)).send(message.client, user=user, target=target, text=text)

def _redispatch_privmsg(message):
    message.client.logger.debug("Redispatching PRIVMSG {}".format(message))
    _redispatch_message_common(message, "message")

def _redispatch_notice(message):
    message.client.logger.debug("Redispatching NOTICE {}".format(message))
    _redispatch_message_common(message, "notice")

## public functional API

def connect(server, port=6697, use_ssl=True):
    connector = loop.create_connection(IRCProtocol, host=server, port=port, ssl=use_ssl)
    transport, protocol = loop.run_until_complete(connector)
    return protocol
