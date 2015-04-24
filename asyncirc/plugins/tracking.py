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
        self.account = None
        self.previous_nicks = []

    def _get_channels(self):
        return map(lambda x: x[1], filter(lambda x: x[0] == self.nick, registry.mappings))

    def __repr__(self):
        return "User {}!{}@{}".format(self.nick, self.user, self.host)

    channels = property(_get_channels)

class Channel:
    def __init__(self, channel):
        self.channel = channel
        self.available = False
        self.mode = ""
        self.state = set()

    def _get_users(self):
        return map(lambda x: x[0], filter(lambda x: x[1] == self.channel, registry.mappings))

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

## things we actually really don't want to redefine

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
    # this will be updated when get_user is called again with the same nick
    # and a full hostmask
    # FIXME it would probably be a good idea to /whois here
    registry.users[nick] = User(nick, None, None)
    return registry.users[nick]

def get_channel(x):
    if x not in registry.channels:
        registry.channels[x] = Channel(x)
    return registry.channels[x]

def get_target(x):
    return Target(x)

## signal definitions

join = signal("join")
extjoin = signal("irc-join")
account = signal("irc-account")
part = signal("part")
quit = signal("quit")
kick = signal("kick")
nick = signal("nick")
extwho_response = signal("irc-354")
who_response = signal("irc-352")
who_done = signal("irc-315")
channel_mode = signal("irc-324")

def sync_channel(client, channel):
    if client.server_supports["WHOX"]:
        client.writeln("WHO {} %cnuha".format(channel))
    else:
        client.writeln("WHO {}".format(channel))
    client.writeln("MODE {}".format(channel))

sync_complete_set = {"mode", "who"}
def check_sync_done(channel):
    if get_channel(channel).state == sync_complete_set:
        signal("sync-done").send(channel)

## event handlers

@extwho_response.connect
def handle_extwho_response(message):
    mynick, channel, ident, host, nick, account = message.params
    user = get_user("{}!{}@{}".format(nick, ident, host))
    user.account = account if account != "0" else None
    handle_join(message, user, channel, real=False)

@who_response.connect
def handle_who_response(message):
    mynick, channel, ident, host, server, nick, state, realname = message.params
    user = get_user("{}!{}@{}".format(nick, ident, host))
    handle_join(message, user, channel, real=False)

@channel_mode.connect
def handle_received_mode(message):
    channel, mode = message.params[1], message.params[2]
    channel_obj = get_channel(channel)
    channel_obj.mode = mode
    channel_obj.state = channel_obj.state | {"mode"}
    check_sync_done(channel)

@who_done.connect
def handle_who_done(message):
    channel = message.params[1]
    channel_obj = get_channel(channel)
    channel_obj.state = channel_obj.state | {"who"}
    check_sync_done(channel)

@join.connect
def handle_join(message, user, channel, real=True):
    if user.nick == message.client.nickname and real:
        sync_channel(message.client, channel)
        get_channel(channel).available = True
    registry.mappings.add((user.nick, channel))

@extjoin.connect
def handle_extjoin(message):
    account = message.params[1]
    get_user(message.source).account = account if account != "*" else None

@account.connect
def account_notify(message):
    account = message.params[0]
    get_user(message.source).account = account if account != "*" else None

@part.connect
def handle_part(message, user, channel, reason):
    user = get_user(user.nick)
    if user == message.client.nickname:
        get_channel(channel).available = False
    registry.mappings.discard((user.nick, channel))

@quit.connect
def handle_quit(message, user, reason):
    user = get_user(user.nick)
    del registry.users[user.nick]
    for channel in set(user.channels):
        registry.mappings.discard((user.nick, channel))

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
