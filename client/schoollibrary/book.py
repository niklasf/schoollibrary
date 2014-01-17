# -*- coding: utf-8 -*-

# Client for a schoollibrary-server.
# Copyright (c) 2014 Niklas Fiekas <niklas.fiekas@tu-clausthal.de>
#
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
import util

class Book(object):
    """A book object."""

    def __init__(self):
        self.id = 0
        self.signature = ""
        self.location = ""
        self.title = ""
        self.authors = ""
        self.topic = ""
        self.volume = ""
        self.keywords = ""
        self.publisher = ""
        self.placeOfPublication = ""
        self.year = None
        self.isbn = ""
        self.edition = ""
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
        return 9

    def data(self, index, role=Qt.DisplayRole):
        book = index.internalPointer()

        if role == Qt.DisplayRole:
            if index.column() == 0:
                return book.title
            elif index.column() == 1:
                return book.topic
            elif index.column() == 2:
                return book.volume
            elif index.column() == 3:
                return book.publisher
            elif index.column() == 4:
                return book.placeOfPublication
            elif index.column() == 5:
                return book.year
            elif index.column() == 6:
                return book.keywords
            elif index.column() == 7:
                return book.isbn
            elif index.column() == 8:
                return book.edition
        elif role == util.TitleAndDescriptionDelegate.DescriptionRole:
            if index.column() == 0:
                return book.authors
        elif role == Qt.TextAlignmentRole:
            if index.column() in (2, 5, 7):
                return Qt.AlignCenter

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal:
            if role == Qt.DisplayRole:
                if section == 0:
                    return "Buch"
                elif section == 1:
                    return "Thema"
                elif section == 2:
                    return "Band"
                elif section == 3:
                    return "Verlag"
                elif section == 4:
                    return "Erscheinungsort"
                elif section == 5:
                    return "Jahr"
                elif section == 6:
                    return u"Schlüsselwörter"
                elif section == 7:
                    return "ISBN"
                elif section == 8:
                    return "Auflage"
        else:
            if role == Qt.DisplayRole:
                book = self.cache.values()[section]
                lines = []

                if book.signature:
                    lines.append(book.signature)

                lines.append(str(book.id))

                if book.location:
                    lines.append(book.location)

                return "\n".join(lines)

            elif role == Qt.TextAlignmentRole:
                return Qt.AlignCenter

    def save(self, book):
        """Saves a book to the server."""
        params = QUrl()
        params.addQueryItem("_csrf", self.app.login.csrf)
        params.addQueryItem("isbn", book.isbn)
        params.addQueryItem("title", book.title)
        params.addQueryItem("authors", book.authors)
        params.addQueryItem("topic", book.topic)
        params.addQueryItem("keywords", book.keywords)
        params.addQueryItem("signature", book.signature)
        params.addQueryItem("location", book.location)

        if book.year:
            params.addQueryItem("year", str(book.year))

        params.addQueryItem("publisher", book.publisher)
        params.addQueryItem("placeOfPublication", book.placeOfPublication)
        params.addQueryItem("volume", book.volume)
        params.addQueryItem("lendable", "true" if book.lendable else "false")

        request = QNetworkRequest(self.app.login.getUrl("/books/"))
        request.setHeader(QNetworkRequest.ContentTypeHeader, "application/x-www-form-urlencoded")
        self.app.network.post(request, params.encodedQuery())

    def reload(self):
        request = QNetworkRequest(self.app.login.getUrl("/books/"))
        self.app.network.get(request)

    def onNetworkRequestFinished(self, reply):
        if reply.request().url().path() != "/books/":
            return

        print reply.request().attribute(QNetworkRequest.HttpStatusCodeAttribute)
        print reply.request().attribute(QNetworkRequest.CustomVerbAttribute)

        blob = unicode(reply.readAll())
        print blob

        books = json.loads(blob)

        if "_id" in books:
            # TODO: ...
            return

        self.beginResetModel()
        self.cache.clear()

        for data in books.values():
            book = Book()

            book.id = int(data["_id"])
            book.isbn = data["isbn"]
            book.title = data["title"]
            book.authors = data["authors"]
            book.volume = data["volume"]
            book.topic = data["topic"]
            book.keywords = data["keywords"]
            book.signature = data["signature"]
            book.location = data["location"]
            book.year = int(data["year"]) if data["year"] else None
            book.publisher = data["publisher"]
            book.placeOfPublication = data["placeOfPublication"]
            book.lent = bool(data["lent"])

            if book.lent:
                book.lendingUser = data["lending"]["user"]
                book.lendingSince = data["lending"]["since"]
                book.lendingDays = data["lending"]["days"]

            self.cache[book.id] = book

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

        grid.addWidget(QLabel("ID:"), 0, 0, Qt.AlignRight)
        self.idBox = QLabel()
        grid.addWidget(self.idBox, 0, 1)

        grid.addWidget(QLabel("ISBN:"), 1, 0, Qt.AlignRight)
        self.isbnBox = QLineEdit()
        grid.addWidget(self.isbnBox, 1, 1)

        grid.addWidget(QLabel("Titel:"), 2, 0, Qt.AlignRight)
        self.titleBox = QLineEdit()
        grid.addWidget(self.titleBox, 2, 1)

        grid.addWidget(QLabel("Autoren:"), 3, 0, Qt.AlignRight)
        self.authorsBox = QLineEdit()
        grid.addWidget(self.authorsBox, 3, 1)

        grid.addWidget(QLabel("Band:"), 4, 0, Qt.AlignRight)
        self.volumeBox = QLineEdit()
        grid.addWidget(self.volumeBox, 4, 1)

        grid.addWidget(QLabel("Thema:"), 5, 0, Qt.AlignRight)
        self.topicBox = QLineEdit()
        grid.addWidget(self.topicBox, 5, 1)

        grid.addWidget(QLabel(u"Schlüsselwörter:"), 6, 0, Qt.AlignRight)
        self.keywordsBox = QLineEdit()
        grid.addWidget(self.keywordsBox, 6, 1)

        grid.addWidget(QLabel("Signatur:"), 7, 0, Qt.AlignRight)
        self.signatureBox = QLineEdit()
        grid.addWidget(self.signatureBox, 7, 1)

        grid.addWidget(QLabel("Standort:"), 8, 0, Qt.AlignRight)
        self.locationBox = QLineEdit()
        grid.addWidget(self.locationBox, 8, 1)

        grid.addWidget(QLabel("Jahr:"), 9, 0, Qt.AlignRight)
        self.yearBox = QLineEdit()
        grid.addWidget(self.yearBox, 9, 1)

        grid.addWidget(QLabel("Verlag:"), 10, 0, Qt.AlignRight)
        self.publisherBox = QLineEdit()
        grid.addWidget(self.publisherBox, 10, 1)

        grid.addWidget(QLabel(u"Veröffentlichungsort:"), 11, 0, Qt.AlignRight)
        self.placeOfPublicationBox = QLineEdit()
        grid.addWidget(self.placeOfPublicationBox, 11, 1)

        buttonBox = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.onSaveClicked)
        buttonBox.rejected.connect(self.close)
        grid.addWidget(buttonBox, 12, 1)

        self.setLayout(grid)
        self.setWindowFlags(self.windowFlags() &~ Qt.WindowContextHelpButtonHint)

    def initValues(self):
        """Initialize the displayed values according to the book."""
        if self.book:
            self.setWindowTitle("Buch: %s" % self.book.title)
            self.idBox.setText(self.book.id)
        else:
            self.setWindowTitle("Neues Buch")
            self.idBox.setText("automatisch")
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

        # TODO: Validate year
        # TODO: Validate ISBN

        self.book.isbn = self.isbnBox.text().strip()
        self.book.title = self.titleBox.text().strip()
        self.book.authors = self.authorsBox.text().strip()
        self.book.topic = self.topicBox.text().strip()
        self.book.keywords = self.keywordsBox.text().strip()
        self.book.signature = self.signatureBox.text().strip()
        self.book.location = self.locationBox.text().strip()

        year = self.yearBox.text().strip()
        if year:
            self.book.year = int(year)
        else:
            self.book.year = None

        self.book.publisher = self.publisherBox.text().strip()
        self.book.placeOfPublication = self.placeOfPublicationBox.text().strip()
        self.book.volume = self.volumeBox.text().strip()

        # TODO
        self.book.lendable = True

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
