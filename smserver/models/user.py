""" User model module """

import datetime
import enum
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, func
from sqlalchemy.orm import relationship, reconstructor, object_session

from smserver.models import schema
from smserver.chathelper import with_color, nick_color
from smserver.models.privilege import Privilege
from smserver import ability

__all__ = ['UserStatus', 'User']


class UserStatus(enum.Enum):
    spectator       = 0
    room_selection  = 1
    music_selection = 2
    option          = 3
    evaluation      = 4


class User(schema.Base):
    """ User model. """

    __tablename__ = 'users'

    REPR = {
        0: "",
        2: "%",
        3: "@",
        5: "&",
        10: "~"
    }

    id               = Column(Integer, primary_key=True)
    pos              = Column(Integer)
    name             = Column(String(255), unique=True, index=True)
    password         = Column(String(255))
    email            = Column(String(255))
    rank             = Column(Integer, default=1)
    xp               = Column(Integer, default=0)
    last_ip          = Column(String(255))
    client_version   = Column(String(255))
    client_name      = Column(String(255))
    online           = Column(Boolean)
    status           = Column(Integer, default=1)
    chat_timestamp   = Column(Boolean, default=False)

    room_id          = Column(Integer, ForeignKey('rooms.id'))
    room             = relationship("Room", back_populates="users")

    connection_token = Column(String(255), ForeignKey('connections.token'))
    connection       = relationship("Connection", back_populates="users")

    song_stats       = relationship("SongStat", back_populates="user")
    privileges       = relationship("Privilege", back_populates="user")
    bans             = relationship("Ban", back_populates="user")

    created_at       = Column(DateTime, default=datetime.datetime.now)
    updated_at       = Column(DateTime, onupdate=datetime.datetime.now)

    @reconstructor
    def _init_on_load(self):
        self._room_level = {}

    def __repr__(self):
        return "<User #%s (name='%s')>" % (self.id, self.name)

    @property
    def enum_status(self):
        """ Return the enum associate with the user status """
        return UserStatus(self.status)

    def fullname(self, room_id=None):
        """ Return user name with level prefix (~, &, ...) """

        return "%s%s" % (
            self._level_to_symbol(self.level(room_id)),
            self.name)

    def fullname_colored(self, room_id=None):
        """ Retun user fullname with chat_color """

        color = nick_color(self.name)
        if not self.online:
            color = "141414"

        if self.room_id != room_id:
            color = "313131"

        return with_color(message=self.fullname(room_id), color=color)

    def can(self, action, room_id=None):
        """ Return True if the user can do this action """

        return ability.Ability.can(action, self.level(room_id))

    def cannot(self, action, room_id=None):
        """ Return True if the user cannot do this action """

        return ability.Ability.cannot(action, self.level(room_id))

    def level(self, room_id=None):
        """ Return the level of the user, given his room """
        if not room_id:
            return self.rank

        priv = self.room_privilege(room_id)
        if priv:
            return priv.level

        return 1

    def room_privilege(self, room_id):
        if room_id in self._room_level:
            return self._room_level[room_id]

        priv = Privilege.find(room_id, self.id, object_session(self))

        self._room_level[room_id] = priv

        return priv

    def set_level(self, room_id, level):
        session = object_session(self)
        if not room_id:
            self.rank = level
            session.commit()
            return level

        priv = Privilege.find_or_update(room_id, self.id, session, level=level)
        self._room_level[room_id] = priv

        return level

    @classmethod
    def _level_to_symbol(cls, level):
        """ Return a symbol corresponding of the user level """

        if not level:
            return None

        symbol = cls.REPR.get(level)
        if symbol:
            return symbol

        keys = sorted(cls.REPR, reverse=True)

        for key in keys:
            if key < level:
                return cls.REPR[key]

        return cls.REPR[keys[-1]]

    @classmethod
    def from_ids(cls, ids, session):
        """ Return a list of user instance from the ids list """

        if not ids:
            return []

        return session.query(cls).filter(cls.id.in_(ids))


    @classmethod
    def from_connection_token(cls, token, session):
        """ Return a list of online user assiociated with the connection token """

        if not token:
            return []

        return cls.onlines(session).filter_by(connection_token=token)

    @classmethod
    def online_from_ids(cls, ids, session):
        """ Return a list of online users from the ids list """

        if not ids:
            return []

        return cls.onlines(session).filter(cls.id.in_(ids))

    @classmethod
    def get_from_pos(cls, ids, pos, session):
        if not ids:
            return None

        return session.query(cls).filter(
            cls.id.in_(ids),
            cls.pos == pos
        ).first()

    @classmethod
    def nb_onlines(cls, session):
        return session.query(func.count(User.id)).filter_by(online=True).scalar()

    @classmethod
    def onlines(cls, session, room_id=None):
        users = session.query(User).filter_by(online=True)
        if room_id:
            users = users.filter_by(room_id=room_id)

        return users

    @classmethod
    def user_index(cls, user_id, room_id, session):
        for idx, user in enumerate(cls.onlines(session, room_id)):
            if user_id == user.id:
                return idx

        return 0

    @staticmethod
    def users_repr(users, room_id=None):
        """
            Textual representation of multiple users?

            :param int room_id: The ID of the room
        """

        return "%s" % " & ".join(user.fullname(room_id) for user in users)

    @staticmethod
    def colored_users_repr(users, room_id=None):
        """
            Colored textual representation of multiple users.

            :param int room_id: The ID of the room
        """

        return "%s" % " & ".join(user.fullname_colored(room_id) for user in users)

    @classmethod
    def disconnect(cls, user, session):
        user.online = False
        user.pos = None
        user.room_id = None
        session.commit()
        return user

    @classmethod
    def disconnect_all(cls, session):
        users = session.query(User).all()

        for user in users:
            user.pos = None
            user.online = False
            user.status = UserStatus.room_selection.value
            user.room_id = None

        session.commit()
