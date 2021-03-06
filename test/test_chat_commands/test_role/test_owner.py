""" Test for chat command /owner """

from smserver.chat_commands import role

from test.test_chat_commands import base
from test.factories.room_factory import RoomFactory
from test.factories.user_factory import user_with_room_privilege

class ChatOwnerTest(base.ChatCommandTest):
    """ Chat owner test """

    @property
    def chat_command(self):
        return role.ChatOwner(self.server)

    def test_set_owner(self):
        """ Test to owner a user in a room """

        room = RoomFactory()

        self.connection.room = room
        user_with_room_privilege(
            level=12,
            connection=self.connection,
            online=True,
            room=room
        )

        target_user_admin = user_with_room_privilege(
            level=16,
            online=True,
            room=room
        )
        target_user = user_with_room_privilege(
            level=1,
            online=True,
            room=room
        )
        target_user2 = user_with_room_privilege(
            level=11,
            online=True,
            room=room
        )

        ret = self.chat_command(self.resource, "invalid_user")
        self.assertEqual(len(ret), 1)
        self.assertRegex(ret[0], "Unknown user")

        ret = self.chat_command(self.resource, target_user_admin.name)
        self.assertEqual(len(ret), 1)
        self.assertRegex(ret[0], "Not authorize")
        self.assertEqual(target_user_admin.level(room.id), 16)

        ret = self.chat_command(self.resource, target_user.name)
        self.assertIsNone(ret)
        self.assertEqual(target_user.level(room.id), 10)

        ret = self.chat_command(self.resource, target_user2.name)
        self.assertIsNone(ret)
        self.assertEqual(target_user2.level(room.id), 10)
