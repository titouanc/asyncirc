import asyncirc
import logging
from blinker import signal
logger = logging.getLogger("asyncirc.plugins.tracking")

class Registry:
    def __init__(self):
        self.mappings = []
        self.users = {}
        self.channels = {}

registry = Registry()

class User:
    def __init__(self, nick, user, host):
        self.nick = nick
        self.user = user
        self.host = host

    def _get_channels(self):
        return filter(lambda x: x[0] == self, registry.mappings)

    def __repr__(self):
        return "User {}!{}@{}".format(self.nick, self.user, self.host)

    channels = property(_get_channels)

class Channel:
    def __init__(self, channel):
        self.channel = channel

    def _get_users(self):
        return filter(lambda x: x[1] == self, registry.mappings)

    def __repr__(self):
        return "Channel {}".format(self.channel)

    users = property(_get_users)

class Target:
    def __init__(self, target):
        self.target = target

    def get(self):
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

## things we redefine

def get_user(x):
    nick, user, host = parse_hostmask(x)
    if nick in registry.users:
        if user is not None and host is not None:
            registry.users[nick].user = user
            registry.users[nick].host = host
        return registry.users[nick]

    if user is not None and host is not None:
        registry.users[nick] = User(nick, user, host)
        return registry.users[nick]

    if "." in nick: # it's probably a server
        return User(nick, nick, nick)

    # we don't know about this user yet, so return a dummy.
    # FIXME it would probably be a good idea to /whois here
    return User(nick, None, None)

def get_channel(x):
    if x not in registry.channels:
        registry.channels[x] = Channel(x)
    return registry.channels[x]

def get_target(x):
    return Target(x)

asyncirc.irc.get_user = get_user
asyncirc.irc.get_channel = get_channel
asyncirc.irc.get_target = get_target

## signal definitions

join = signal("join")
part = signal("part")
quit = signal("quit")
kick = signal("kick")
nick = signal("nick")

## event handlers

@join.connect
def handle_join(message, user, channel):
    registry.mappings.append((user, channel))

@part.connect
def handle_part(message, user, channel, reason):
    registry.mappings.remove((user, channel))

@quit.connect
def handle_quit(message, user, reason):
    for channel in user.channels:
        registry.mappings.remove((user, channel))

@kick.connect
def handle_kick(message, kicker, kickee, channel, reason):
    registry.mappings.remove((kickee, channel))

@nick.connect
def handle_nick(message, user, new_nick):
    user.nick = new_nick

logger.info("Plugin registered")
