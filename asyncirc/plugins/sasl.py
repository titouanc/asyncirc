from blinker import signal
import base64

import logging
logger = logging.getLogger("asyncirc.plugins.sasl")

import asyncirc.plugins.cap
asyncirc.plugins.cap.cap_wait("sasl")

pending_authentications = []

class AuthenticationFailed(Exception): pass

def auth(username, password):
    pending_authentications.append([username, password])

def caps_acknowledged(client):
    client.writeln("AUTHENTICATE PLAIN")

def handle_authenticate(message):
    if message.params[0] == "+":
        logger.debug("Authentication request acknowledged, sending username/password")
        authinfo = pending_authentications.pop()
        authdata = base64.b64encode("{0}\x00{0}\x00{1}".format(*authinfo).encode())
        message.client.writeln("AUTHENTICATE {}".format(authdata.decode()))

def handle_900(message):
    logger.debug("SASL authentication complete.")
    signal("sasl-auth-complete").send(message)
    signal("auth-complete").send(message)
    asyncirc.plugins.cap.cap_done(message.client, "sasl")

def handle_failure(message):
    raise AuthenticationFailed("Numeric {}".format(message.verb))

signal("caps-acknowledged").connect(caps_acknowledged)
signal("irc-authenticate").connect(handle_authenticate)
signal("irc-900").connect(handle_900)
signal("irc-904").connect(handle_failure)
