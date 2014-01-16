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

import json

import indexed

class Book(object):
    """A book object."""

    def __init__(self):
        self.id = 0
        self.title = ""
        self.authors = ""
        self.topic = ""
        self.keywords = ""
        self.signature = ""
        self.location = ""
        self.isbn = ""
        self.year = None
        self.publisher = ""
        self.placeOfPublication = ""
        self.volume = ""
        self.lendable = True
        self.lendingUser = None
        self.lendingSince = None
        self.lendingDays = None
        self.lent = False

class BookTableModel(QAbstractTableModel):
    """The book database."""

    def __init__(self, app):
        super(BookTableModel, self).__init__()
        self.app = app
        self.app.network.finished.connect(self.onNetworkRequestFinished)
        self.cache = indexed.IndexedOrderedDict()

    def index(self, row, column, parent=QModelIndex()):
        if parent.isValid() or not self.hasIndex(row, column, parent):
            return QModelIndex()
        else:
            return self.createIndex(row, column, self.cache.values()[row])

    def rowCount(self, parent=QModelIndex()):
        return len(self.cache)

    def columnCount(self, parent=QModelIndex()):
        return 1

    def data(self, index, role=Qt.DisplayRole):
        book = index.internalPointer()

        if role == Qt.DisplayRole:
            if index.column() == 0:
                return book.title
        elif role == util.TitleAndDescriptionDelegate.DescriptionRole:
            if index.column() == 0:
                return book.author

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal:
            if role == Qt.DisplayRole:
                if section == 0:
                    return "Buch"
        else:
            if role == Qt.DisplayRole:
                return self.cache.values()[section].id

    def reload(self):
        request = QNetworkRequest(self.app.login.getUrl("/books/"))
        self.app.network.get(request)

    def onNetworkRequestFinished(self, reply):
        if reply.request().url().path() != "/books/":
            return

        books = json.loads(unicode(reply.readAll()))

        self.beginResetModel()
        self.cache.clear()

        for data in books.values():
            book = Book()
            book.id = data["id"]
            book.title = data["title"]
            book.authors = data["authors"]
            # TODO: More columns

        self.endResetModel()

