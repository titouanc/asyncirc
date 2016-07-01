from asynctest import test, TestManager
from asyncirc.plugins import core
from blinker import signal
from _mocks import Client

core.attach_handlers()

def receive_pong(line):
    test_ping.succeed_if(line == "PONG irc.example.com")

def check_example_user(u):
    return u.nick == "example" and u.user == "example" and u.host == "example.com"

def try_public_thing(test, user, target, text):
    test.succeed_if(check_example_user(user) and target == "#example" and text.startswith("example public "))

def try_private_thing(test, user, text):
    test.succeed_if(check_example_user(user) and text.startswith("example private "))

def receive_public_message_signal(message, user, target, text):
    try_public_thing(test_public_message_dispatch, user, target, text)

def receive_private_message_signal(message, user, target, text):
    try_private_thing(test_private_message_dispatch, user, text)

def receive_public_notice_signal(message, user, target, text):
    try_public_thing(test_public_notice_dispatch, user, target, text)

def receive_private_notice_signal(message, user, target, text):
    try_private_thing(test_private_notice_dispatch, user, text)

def receive_join_signal(message, user, channel):
    test_join_dispatch.succeed_if(check_example_user(user) and channel == "#example")

def receive_part_signal(message, user, channel, reason):
    if check_example_user(user) and channel == "#example" and reason == "example part reason":
        test_part_dispatch_reason.success()
    elif check_example_user(user) and channel == "#example2" and reason is None:
        test_part_dispatch_no_reason.success()
    elif channel == "#example":
        test_part_dispatch_reason.failure()
    else:
        test_part_dispatch_no_reason.failure()

def receive_quit_signal(message, user, reason):
    test_quit_dispatch.succeed_if(check_example_user(user) and reason == "Quit (Example reason)")

def receive_kick_signal(message, kicker, kickee, channel, reason):
    test_kick_dispatch.succeed_if(check_example_user(kicker) and kickee == "user" and reason == "kicked" and channel == "#channel")

def receive_nick_signal(message, user, new_nick):
    test_nick_dispatch.succeed_if(check_example_user(user) and new_nick == "examp[le]")

signal("public-message").connect(receive_public_message_signal)
signal("private-message").connect(receive_private_message_signal)
signal("public-notice").connect(receive_public_notice_signal)
signal("private-notice").connect(receive_private_notice_signal)
signal("join").connect(receive_join_signal)
signal("part").connect(receive_part_signal)
signal("quit").connect(receive_quit_signal)
signal("kick").connect(receive_kick_signal)
signal("nick").connect(receive_nick_signal)

client = Client()

@test("should respond to IRC PING messages")
def test_ping():
    client = Client(writeln=receive_pong)
    signal("raw").send(client, text="PING irc.example.com")

@test("should redispatch messages sent to channels")
def test_public_message_dispatch():
    signal("raw").send(client, text=":example!example@example.com PRIVMSG #example :example public message")

@test("should redispatch messages sent privately")
def test_private_message_dispatch():
    signal("raw").send(client, text=":example!example@example.com PRIVMSG bot :example private message")

@test("should redispatch notices sent to channels")
def test_public_notice_dispatch():
    signal("raw").send(client, text=":example!example@example.com NOTICE #example :example public notice")

@test("should redispatch notices sent privately")
def test_private_notice_dispatch():
    signal("raw").send(client, text=":example!example@example.com NOTICE bot :example private notice")

@test("should redispatch join messages")
def test_join_dispatch():
    signal("raw").send(client, text=":example!example@example.com JOIN #example")

@test("should redispatch part messages with reasons")
def test_part_dispatch_reason():
    signal("raw").send(client, text=":example!example@example.com PART #example :example part reason")

@test("should redispatch part messages without reasons, setting reason=None")
def test_part_dispatch_no_reason():
    signal("raw").send(client, text=":example!example@example.com PART #example2")

@test("should redispatch quit messages")
def test_quit_dispatch():
    signal("raw").send(client, text=":example!example@example.com QUIT :Quit (Example reason)")

@test("should redispatch kick messages")
def test_kick_dispatch():
    signal("raw").send(client, text=":example!example@example.com KICK #channel user :kicked")

@test("should redispatch nick changes")
def test_nick_dispatch():
    signal("raw").send(client, text=":example!example@example.com NICK examp[le]")

@test("should recognize ISUPPORT messages and update the server_supports dict")
def test_isupport():
    signal("raw").send(client, text=":irc.example.com 005 bot EXTREMELY-VERBOSE-FEATURE-NAMES :Are supported by this server")
    test_isupport.succeed_if(client.server_supports["EXTREMELY-VERBOSE-FEATURE-NAMES"])

manager = TestManager([
    test_ping, test_public_message_dispatch, test_private_message_dispatch,
    test_public_notice_dispatch, test_private_notice_dispatch, test_join_dispatch,
    test_part_dispatch_reason, test_part_dispatch_no_reason, test_quit_dispatch,
    test_kick_dispatch, test_nick_dispatch, test_isupport
])

if __name__ == '__main__':
    manager.run_all()
