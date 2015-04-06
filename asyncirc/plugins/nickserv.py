from blinker import signal

def handle_nickserv_notices(message, user, target, text):
    if "You are now identified" in text:
        signal("nickserv-auth-success").send(text)
    if "Invalid password" in text:
        signal("nickserv-auth-fail").send(text)

signal("private-notice").connect(handle_nickserv_notices)
signal("plugin-registered").send("asyncirc.plugins.nickserv")
