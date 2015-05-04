from blinker import signal
from asyncirc.irc import get_target, get_user, get_channel
from asyncirc.parser import RFC1459Message

import asyncio
import logging
import random
import time
logger = logging.getLogger("asyncirc.plugins.core")

ping_clients = []

def _pong(message):
    message.client.writeln("PONG {}".format(message.params[0]))

def _redispatch_message_common(message, type):
    target, text = get_target(message.params[0]), message.params[1]
    user = get_user(message.source)
    signal(type).send(message, user=user, target=target, text=text)
    if target == message.client.nickname:
        signal("private-{}".format(type)).send(message, user=user, target=target, text=text)
    else:
        signal("public-{}".format(type)).send(message, user=user, target=target, text=text)

def _redispatch_privmsg(message):
    _redispatch_message_common(message, "message")

def _redispatch_notice(message):
    _redispatch_message_common(message, "notice")

def _redispatch_join(message):
    user = get_user(message.source)
    channel = get_channel(message.params[0])
    signal("join").send(message, user=user, channel=channel)

def _redispatch_part(message):
    user = get_user(message.source)
    channel, reason = get_channel(message.params[0]), None
    if len(message.params) > 1:
        reason = message.params[1]
    signal("part").send(message, user=user, channel=channel, reason=reason)

def _redispatch_quit(message):
    user = get_user(message.source)
    reason = message.params[0]
    signal("quit").send(message, user=user, reason=reason)

def _redispatch_kick(message):
    kicker = get_user(message.source)
    channel, kickee, reason = get_channel(message.params[0]), get_user(message.params[1]), message.params[2]
    signal("kick").send(message, kicker=kicker, kickee=kickee, channel=channel, reason=reason)

def _redispatch_nick(message):
    old_user = get_user(message.source)
    new_nick = message.params[0]
    if old_user.nick == message.client.nickname:
        message.client.nickname = new_nick
    signal("nick").send(message, user=old_user, new_nick=new_nick)

def _parse_mode(message):
    # :ChanServ!ChanServ@services. MODE ##fwilson +o fwilson
    argument_modes = "".join(message.client.server_supports["CHANMODES"].split(",")[:-1])
    argument_modes += message.client.server_supports["PREFIX"].split(")")[0][1:]
    user = get_user(message.source)
    channel = message.params[0]
    modes = message.params[1]
    args = message.params[2:]
    flag = "+"
    for mode in modes:
        if mode in "+-":
            flag = mode
            continue
        if mode in argument_modes:
            arg = args.pop(0)
        else:
            arg = None
        signal("{}mode".format(flag)).send(message, mode=mode, arg=arg, user=user, channel=channel)
        signal("mode {}{}".format(flag, mode)).send(message, arg=arg, user=user, channel=channel)

def _server_supports(message):
    supports = message.params[1:]
    for feature in supports:
        if "=" in feature:
            k, v = feature.split("=")
            message.client.server_supports[k] = v
        else:
            message.client.server_supports[feature] = True

def _nick_in_use(message):
    message.client.old_nickname = message.client.nickname
    s = "a{}".format("".join([random.choice("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ") for i in range(8)]))
    message.client.nickname = s
    message.client.writeln("NICK", s)

def _ping_servers():
    for client in ping_clients:
        if client.last_pong != 0 and time.time() - client.last_pong > 90:
            client.connection_lost(Exception())
        client.writeln("PING :GNIP")
        client.last_ping = time.time()
    asyncio.get_event_loop().call_later(60, _ping_servers)

def _catch_pong(message):
    message.client.last_pong = time.time()

def _redispatch_irc(message):
    signal("irc-{}".format(message.verb.lower())).send(message)

def _redispatch_raw(client, text):
    message = RFC1459Message.from_message(text)
    message.client = client
    signal("irc").send(message)

def _queue_ping(client):
    ping_clients.append(client)
    _ping_servers()

signal("raw").connect(_redispatch_raw)
signal("irc").connect(_redispatch_irc)
signal("connected").connect(_queue_ping)
signal("irc-ping").connect(_pong)
signal("irc-pong").connect(_catch_pong)
signal("irc-privmsg").connect(_redispatch_privmsg)
signal("irc-notice").connect(_redispatch_notice)
signal("irc-join").connect(_redispatch_join)
signal("irc-part").connect(_redispatch_part)
signal("irc-quit").connect(_redispatch_quit)
signal("irc-kick").connect(_redispatch_kick)
signal("irc-nick").connect(_redispatch_nick)
signal("irc-mode").connect(_parse_mode)
signal("irc-005").connect(_server_supports)
signal("irc-433").connect(_nick_in_use)
