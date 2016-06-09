#!/usr/bin/env python3
# -*- coding: utf8 -*-

from smserver.smutils import smpacket
from smserver.stepmania_controller import StepmaniaController
from smserver import models

class UserStatusController(StepmaniaController):
    command = smpacket.SMClientCommand.NSSCSMS
    require_login = True

    def handle(self):
        status_mapping = {
            1: models.UserStatus.music_selection,
            3: models.UserStatus.option,
            5: models.UserStatus.evaluation,
            7: models.UserStatus.room_selection
        }

        if self.packet["action"] == 7:
            self.send(models.Room.smo_list(self.session))

        if self.room and self.packet["action"] in status_mapping:
            self.send_user_message("is in %s screen" % (
                status_mapping[self.packet["action"]].name
                ))

        for user in self.active_users:
            user.status = status_mapping.get(self.packet["action"], models.UserStatus.unknown).value

        self.server.send_user_list(self.session)

