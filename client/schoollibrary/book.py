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
            book.id = int(data["id"])
            book.title = data["title"]
            book.authors = data["authors"]
            book.isbn = data["isbn"]
            # TODO: More columns

        self.endResetModel()

class BookDialog(QDialog):
    """A product editing dialog."""

    def __init__(self, app, book, parent):
        super(BookDialog, self).__init__(parent)
        self.app = app
        self.book = book

        self.initUi()
        self.initValues()

    def initUi(self):
        """Initializes the user interface."""
        grid = QGridLayout()

        grid.addWidget(QLabel("ISBN:"), 0, 0, Qt.AlignRight)
        self.isbnBox = QLineEdit()
        grid.addWidget(self.isbnBox, 0, 1)

        grid.addWidget(QLabel("Titel:"), 1, 0, Qt.AlignRight)
        self.titleBox = QLineEdit()
        grid.addWidget(self.titleBox, 1, 1)

        grid.addWidget(QLabel("Autoren:"), 2, 0, Qt.AlignRight)
        self.authorsBox = QLineEdit()
        grid.addWidget(self.authorsBox, 2, 1)

        grid.addWidget(QLabel("Band:"), 3, 0, Qt.AlignRight)
        self.volumeBox = QLineEdit()
        grid.addWidget(self.volumeBox, 3, 1)

        grid.addWidget(QLabel("Thema:"), 4, 0, Qt.AlignRight)
        self.topicBox = QLineEdit()
        grid.addWidget(self.topicBox, 4, 1)

        grid.addWidget(QLabel(u"Schlüsselwörter:"), 5, 0, Qt.AlignRight)
        self.keywordsBox = QLineEdit()
        grid.addWidget(self.keywordsBox, 5, 1)

        grid.addWidget(QLabel("Signatur:"), 6, 0, Qt.AlignRight)
        self.signatureBox = QLineEdit()
        grid.addWidget(self.signatureBox, 6, 1)

        grid.addWidget(QLabel("Standort:"), 7, 0, Qt.AlignRight)
        self.locationBox = QLineEdit()
        grid.addWidget(self.locationBox, 7, 1)

        grid.addWidget(QLabel("Jahr:"), 8, 0, Qt.AlignRight)
        self.yearBox = QLineEdit()
        grid.addWidget(self.yearBox, 8, 1)

        grid.addWidget(QLabel("Verlag:"), 9, 0, Qt.AlignRight)
        self.publisherBox = QLineEdit()
        grid.addWidget(self.publisherBox, 9, 1)

        grid.addWidget(QLabel(u"Veröffentlichungsort:"), 10, 0, Qt.AlignRight)
        self.placeOfPublicationBox = QLineEdit()
        grid.addWidget(self.placeOfPublicationBox, 10, 1)

        self.setLayout(grid)
        self.setWindowFlags(self.windowFlags() &~ Qt.WindowContextHelpButtonHint)

    def initValues(self):
        """Initialize the displayed values according to the book."""
        if self.book:
            self.setWindowTitle("Buch: %s" % self.book.title)
        else:
            self.setWindowTitle("Neues Buch")
            self.book = Book()

        self.isbnBox.setText(self.book.isbn)
        self.titleBox.setText(self.book.title)
        self.authorsBox.setText(self.book.authors)

    def isDirty(self):
        """Checks if anything has been changed and not saved."""
        # TODO: Actually do this.
        return True

    def save(self):
        """Validates and saves the current product."""
        if not self.isDirty() and self.book.id:
            return True

        if not self.titleBox.text().strip():
            QMessageBox.warning(self, self.windowTitle(),
                u"Es muss ein Titel angegeben werden.")
            return False

        self.book.isbn = self.isbnBox.text().strip()
        self.book.title = self.titleBox.text().strip()
        self.book.authors = self.authorsBox.text().strip()
        self.app.books.save(self.book)
        return True

    def onSaveClicked(self):
        """Handles a click on the save button."""
        if self.save():
            self.close()

    def closeEvent(self, event):
        """Prevents the window from beeing closed if dirty."""
        if self.isDirty():
            result = QMessageBox.question(self, self.windowTitle(),
                u"Es gibt noch ungespeicherte Änderungen an diesem Buch.",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)

            if result == QMessageBox.Save:
                if not self.save():
                    event.ignore()
                    return
            elif result == QMessageBox.Cancel:
                event.ignore()
                return

        event.accept()
