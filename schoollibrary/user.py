# -*- coding: utf-8 -*-

# Client for a schoollibrary-server.
# Copyright (c) 2014 Niklas Fiekas <niklas.fiekas@tu-clausthal.de>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have receicved a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from PySide.QtCore import *
from PySide.QtGui import *
from PySide.QtNetwork import *

class UserListModel(QAbstractListModel):

    def __init__(self, app):
        super(UserListModel, self).__init__()
        self.app = app
        self.app.network.finished.connect(self.onNetworkRequestFinished)
        self.cache = []

    def index(self, row, column, parent=QModelIndex()):
        if parent.isValid() or not self.hasIndex(row, column, parent):
            return QModelIndex()
        else:
            return self.createIndex(row, column, row)

    def rowCount(self, parent=QModelIndex()):
        return len(self.cache)

    def data(self, index, role=Qt.DisplayRole):
        user = self.cache[index.row()]

        if role == Qt.DisplayRole:
            return user
        elif role == Qt.EditRole:
            return user

    def reload(self):
        request = QNetworkRequest(self.app.login.getUrl("/users/"))
        self.app.network.get(request)

    def onNetworkRequestFinished(self, reply):
        if not reply.request().url().path().endswith("/users/"):
            return

        self.beginResetModel()
        self.cache = []

        while reply.canReadLine():
            self.cache.append(str(reply.readLine()).strip())

        self.cache.sort()

        self.endResetModel()
