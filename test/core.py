from asynctest import test, TestManager
from asyncirc.plugins import core
from blinker import signal
from mocks import Client

def receive_pong(line):
    if line != "PONG irc.example.com":
        test_ping.failure()
    else:
        test_ping.success()

def receive_public_message_signal(message, user, target, text):
    if user.nick == "example" and user.user == "example" and \
            user.host == "example.com" and target == "#example" and \
            text == "example public message":
        test_public_message_dispatch.success()
    else:
        test_public_message_dispatch.failure()

signal("public-message").connect(receive_public_message_signal)

@test("should respond to IRC PING messages")
def test_ping():
    client = Client(writeln=receive_pong)
    signal("raw").send(client, text="PING irc.example.com")

@test("should redispatch messages sent to channels")
def test_public_message_dispatch():
    client = Client()
    signal("raw").send(client, text=":example!example@example.com PRIVMSG #example :example public message")

TestManager([test_ping, test_public_message_dispatch]).run_all()
