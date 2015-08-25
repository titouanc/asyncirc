from asynctest import test, Test, TestManager
from asyncirc.plugins import tracking
from blinker import signal
from _mocks import Client

client = Client()
client.netid = "mock for testing"
tracking.create_registry(client)

def join_example_user():
    signal("raw").send(client, text=":example!example@example.com JOIN #example exampleaccount :Example user")

def part_example_user():
    signal("raw").send(client, text=":example!example@example.com PART #example :Example reason")

def quit_example_user():
    signal("raw").send(client, text=":example!example@example.com QUIT :Example quit reason")

def kick_example_user():
    signal("raw").send(client, text=":someop!~someop@example.org KICK #example example :Example kick reason")

@test("should add users to the tracking database on channel joins")
def test_add_objects_to_database():
    join_example_user()

test_account_recording_on_extjoin = Test(None, "should track account names")
test_host_recording = Test(None, "should track hosts")
test_channel_membership_join_tracking = Test(None, "should track channel membership: joins")

@test_add_objects_to_database.done.connect
def check_objects_in_database(_):
    test_add_objects_to_database.succeed_if("example" in client.tracking_registry.users)
    test_account_recording_on_extjoin.succeed_if(client.tracking_registry.users["example"].account == "exampleaccount")
    test_host_recording.succeed_if(client.tracking_registry.users["example"].host == "example.com")
    test_channel_membership_join_tracking.succeed_if("#example" in client.tracking_registry.users["example"].channels)

@test("should track channel membership: parts")
def test_channel_membership_part_tracking():
    part_example_user()

@test_channel_membership_part_tracking.done.connect
def check_membership(_):
    test_channel_membership_part_tracking.succeed_if("#example" not in client.tracking_registry.users["example"].channels)

@test("should remove users from the registry on quit")
def test_quit():
    quit_example_user()

@test_quit.done.connect
def check_quit_actually_removed_user(_):
    test_quit.succeed_if("example" not in client.tracking_registry.users)

test_user_return_after_quit = Test(None, "users are re-added to the registry on reconnect")

@test("should remove users from channels on kick")
def test_kick():
    join_example_user()
    test_user_return_after_quit.succeed_if("example" in client.tracking_registry.users and "#example" in client.tracking_registry.users["example"].channels)
    kick_example_user()

@test_kick.done.connect
def check_kick_removes_user_from_channel(_):
    test_kick.succeed_if("#example" not in client.tracking_registry.users["example"].channels)

manager = TestManager([
    test_add_objects_to_database, test_account_recording_on_extjoin, test_host_recording,
    test_channel_membership_join_tracking, test_channel_membership_part_tracking, test_quit,
    test_kick, test_user_return_after_quit
])

if __name__ == '__main__':
    manager.run_all()
