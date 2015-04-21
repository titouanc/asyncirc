import asyncirc
import asyncirc.irc
from blinker import signal

class Registry:
    def __init__(self):
        self.mappings = set()
        # mappings contains two-tuples (user, channel)
        self.users = {}
        self.channels = {}

registry = Registry()

class User:
    def __init__(self, nick, user, host):
        self.nick = nick
        self.user = user
        self.host = host
        self.previous_nicks = []

    def _get_channels(self):
        return map(lambda x: x[1], filter(lambda x: x[0] == self, registry.mappings))

    def __repr__(self):
        return "User {}!{}@{}".format(self.nick, self.user, self.host)

    channels = property(_get_channels)

class Channel:
    def __init__(self, channel):
        self.channel = channel
        self.available = False

    def _get_users(self):
        return map(lambda x: x[0], filter(lambda x: x[1] == self, registry.mappings))

    def __repr__(self):
        return "Channel {}".format(self.channel)

    users = property(_get_users)

class Target:
    def __init__(self, target):
        self.target = target

    def trackable(self):
        if self.target[0] == '#':
            return get_channel(self.target)
        return get_user(self.target)

## utility functions

def parse_hostmask(hostmask):
    if "!" in hostmask and "@" in hostmask:
        nick, userhost = hostmask.split("!", maxsplit=1)
        user, host = userhost.split("@", maxsplit=1)
        return nick, user, host
    return hostmask, None, None

## signal definitions

join = signal("join")
part = signal("part")
quit = signal("quit")
kick = signal("kick")
nick = signal("nick")
who_response = signal("irc-352")
who_done = signal("irc-315")
## event handlers

@who_response.connect
def handle_who_response(message):
    mynick, channel, ident, host, server, nick, state, realname = message.params
    user = get_user("{}!{}@{}".format(nick, ident, host))
    handle_join(message, user, channel, real=False)

@who_done.connect
def handle_who_done(message):
    signal("sync-done").send(message.params[1])

@join.connect
def handle_join(message, user, channel, real=True):
    if isinstance(channel, Channel):
        channel = channel.channel
    if user.nick == message.client.nickname and real:
        message.client.writeln("WHO {}".format(channel))
        channel.available = True
    registry.mappings.add((user, channel))

@part.connect
def handle_part(message, user, channel, reason):
    if user.nick == message.client.nickname:
        channel.available = False
    registry.mappings.discard((user, channel))

@quit.connect
def handle_quit(message, user, reason):
    del registry.users[user.nick]
    for channel in set(user.channels):
        registry.mappings.discard((user, channel))

@kick.connect
def handle_kick(message, kicker, kickee, channel, reason):
    registry.mappings.discard((kickee, channel))

@nick.connect
def handle_nick(message, user, new_nick):
    old_nick = user.nick
    user.previous_nicks.append(old_nick)
    user.nick = new_nick
    del registry.users[old_nick]
    registry.users[new_nick] = user

signal("plugin-registered").send("asyncirc.plugins.tracking")
