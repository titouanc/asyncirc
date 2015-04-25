from blinker import signal

import logging
logger = logging.getLogger("asyncirc.plugins.cap")

capabilities_requested = set()
capabilities_available = set()
capabilities_pending = []

registration_state = set()

def request_capability(cap):
    capabilities_requested.add(cap)

def request_capabilities(client, caps):
    if len(registration_state) >= 2:
        client.writeln("CAP REQ :{}".format(" ".join(list(caps))))
        client.caps |= caps

def registration_complete(client):
    registration_state.add("registered")
    request_capabilities(client, capabilities_available & capabilities_requested)

def handle_client_create(client):
    client.writeln("CAP LS")

def check_all_caps_done(client):
    if not capabilities_pending:
        client.writeln("CAP END")

def cap_done(client, cap):
    capabilities_pending.remove(cap)
    check_all_caps_done(client)

def cap_wait(cap):
    capabilities_requested.add(cap)
    capabilities_pending.append(cap)

def handle_irc_cap(message):
    if message.params[1] == "LS":
        capabilities_available.update(set(message.params[2].split()))
        logger.debug("Capabilities provided by server are {}".format(capabilities_available))
        registration_state.add("caps-known")
        request_capabilities(message.client, capabilities_available & capabilities_requested)

    if message.params[1] == "ACK":
        logger.debug("ACK received from server, ending capability negotiation. {}".format(message.client.caps))
        signal("caps-acknowledged").send(message.client)
        check_all_caps_done(message.client)

signal("registration-complete").connect(registration_complete)
signal("connected").connect(handle_client_create)
signal("irc-cap").connect(handle_irc_cap)
