from blinker import signal
from asyncirc.irc import get_target, get_user, get_channel
from asyncirc.parser import RFC1459Message

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
    signal("nick").send(message, user=old_user, new_nick=new_nick)

def _server_supports(message):
    supports = message.params[1:-1]
    for feature in supports:
        if "=" in feature:
            k, v = feature.split("=")
            message.client.server_supports[k] = v
        else:
            message.client.server_supports[feature] = True

def _redispatch_irc(message):
    signal("irc-{}".format(message.verb.lower())).send(message)

def _redispatch_raw(client, text):
    message = RFC1459Message.from_message(text)
    message.client = client
    signal("irc").send(message)

signal("raw").connect(_redispatch_raw)
signal("irc").connect(_redispatch_irc)
signal("irc-ping").connect(_pong)
signal("irc-privmsg").connect(_redispatch_privmsg)
signal("irc-notice").connect(_redispatch_notice)
signal("irc-join").connect(_redispatch_join)
signal("irc-part").connect(_redispatch_part)
signal("irc-quit").connect(_redispatch_quit)
signal("irc-kick").connect(_redispatch_kick)
signal("irc-nick").connect(_redispatch_nick)
signal("irc-005").connect(_server_supports)

