from blinker import signal

def handle_nickserv_notices(message, user, target, text):
    if "You are now identified" in text:
        signal("nickserv-auth-success").send(message)
    if "Invalid password" in text:
        signal("nickserv-auth-fail").send(message)

def check_regain_needed(message):
    if message.client.old_nickname is not None:
        message.client.say("NickServ", "REGAIN {}".format(message.client.old_nickname))

signal("irc-001").connect(check_regain_needed)
signal("private-notice").connect(handle_nickserv_notices)
signal("plugin-registered").send("asyncirc.plugins.nickserv")
