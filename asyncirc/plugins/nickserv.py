import logging
from blinker import signal
logger = logging.getLogger("asyncirc.plugin.nickserv")

def handle_nickserv_notices(client, user, target, text):
    if "You are now identified" in text:
        signal("nickserv-auth-success").send(text)
    if "Invalid password" in text:
        signal("nickserv-auth-fail").send(text)

signal("private-notice").connect(handle_nickserv_notices)
