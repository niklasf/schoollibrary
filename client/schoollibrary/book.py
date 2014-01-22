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
import uuid
import re

import indexed
import util
import progressspinner
import network

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

        self.bookPathPattern = re.compile(r"^\/books\/([0-9]+)\/$")

    def index(self, row, column, parent=QModelIndex()):
        if parent.isValid() or not self.hasIndex(row, column, parent):
            return QModelIndex()
        else:
            return self.createIndex(row, column, self.cache.values()[row])

    def rowCount(self, parent=QModelIndex()):
        return len(self.cache)

    def columnCount(self, parent=QModelIndex()):
        return 10

    def data(self, index, role=Qt.DisplayRole):
        book = index.internalPointer()

        if role == Qt.DisplayRole:
            if index.column() == 0:
                lines = []
                if book.signature:
                    lines.append(book.signature)
                lines.append(str(book.id))
                if book.location:
                    lines.append(book.location)
                return "\n".join(lines)
            elif index.column() == 1:
                return book.title
            elif index.column() == 2:
                return book.topic
            elif index.column() == 3:
                return book.volume
            elif index.column() == 4:
                return book.publisher
            elif index.column() == 5:
                return book.placeOfPublication
            elif index.column() == 6:
                return book.year
            elif index.column() == 7:
                return book.keywords
            elif index.column() == 8:
                return book.isbn
            elif index.column() == 9:
                return book.edition
        elif role == Qt.UserRole:
            if index.column() == 0:
                return book.id
            else:
                return index.data(Qt.DisplayRole)
        elif role == util.TitleAndDescriptionDelegate.DescriptionRole:
            if index.column() == 1:
                return book.authors
        elif role == Qt.TextAlignmentRole:
            if index.column() in (0, 3, 6, 8):
                return Qt.AlignCenter
        elif role == Qt.FontRole:
            if index.column() == 0:
                font = QFont()
                font.setPointSizeF(font.pointSize() * 0.8)
                return font

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal:
            if role == Qt.DisplayRole:
                if section == 0:
                    return "Label"
                if section == 1:
                    return "Buch"
                elif section == 2:
                    return "Thema"
                elif section == 3:
                    return "Band"
                elif section == 4:
                    return "Verlag"
                elif section == 5:
                    return "Erscheinungsort"
                elif section == 6:
                    return "Jahr"
                elif section == 7:
                    return u"Schlüsselwörter"
                elif section == 8:
                    return "ISBN"
                elif section == 9:
                    return "Auflage"

    def reload(self):
        request = QNetworkRequest(self.app.login.getUrl("/books/"))
        return self.app.network.http("GET", request)

    def delete(self, book):
        path = "/books/%d/" % book.id
        request = QNetworkRequest(self.app.login.getUrl(path))
        request.setRawHeader(QByteArray("X-CSRF-Token"), QByteArray(self.app.login.csrf))
        return self.app.network.http("DELETE", request)

    def onNetworkRequestFinished(self, reply):
        request = reply.request()

        if request.url().path() == "/books/" and request.attribute(network.HttpMethod) == "POST":
            # Book created.
            data = json.loads(unicode(reply.readAll()))
            book = self.bookFromData(data)
            assert not book.id in self.cache

            self.beginInsertRows(QModelIndex(), self.rowCount(), self.rowCount())
            self.cache[book.id] = book
            self.endInsertRows()
        elif request.url().path() == "/books/" and request.attribute(network.HttpMethod) == "GET":
            # Book list reloaded.
            self.beginResetModel()
            self.cache.clear()

            for data in json.loads(unicode(reply.readAll())).values():
                book = self.bookFromData(data)
                self.cache[book.id] = book

            self.endResetModel()
        else:
            match = self.bookPathPattern.match(request.url().path())
            if match and request.attribute(network.HttpMethod) == "DELETE":
                # Book deleted.
                id = int(match.group(1))
                row = self.cache.keys().index(id)
                self.beginRemoveRows(QModelIndex(), row, row)
                del self.cache[id]
                self.endRemoveRows()
            elif match and request.attribute(network.HttpMethod) in ("GET", "PUT"):
                # Book changed or reloaded.
                # TODO: Implement.
                pass

    def bookFromData(self, data):
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

        return book

    def indexFromBook(self, book):
        books = self.cache.viewvalues()
        if book in books:
            return self.createIndex(self.cache.keys().index(book.id), 0, book)
        else:
            return QModelIndex()

    def indexToBook(self, index):
        if not index.isValid():
            return None
        else:
            return index.internalPointer()

    def getSortProxy(self):
        proxy = BookTableSortFilterProxyModel()
        proxy.setSourceModel(self)
        return proxy

class BookTableSortFilterProxyModel(QSortFilterProxyModel):
    """Sorts and filters an underlying book table model."""

    def __init__(self):
        super(BookTableSortFilterProxyModel, self).__init__()
        self.setDynamicSortFilter(True)
        self.setSortRole(Qt.UserRole)

    def indexToBook(self, index):
        """Gets the book associated with an index."""
        return self.sourceModel().indexToBook(self.mapToSource(index))

    def indexFromBook(self, book):
        """Gets the index associated with a book."""
        return self.mapFromSource(self.sourceModel().indexFromBook(book))

class BookDialog(QDialog):
    """A product editing dialog."""

    dialogs = dict()

    @classmethod
    def open(cls, app, book, parent):
        """Opens a new dialog or sets the focus to an existing one."""
        if book:
            if not book.id in cls.dialogs or not cls.dialogs[book.id].isVisible():
                cls.dialogs[book.id] = BookDialog(app, book, parent)
                cls.dialogs[book.id].show()
            else:
                cls.dialogs[book.id].activateWindow()
            return cls.dialogs[book.id]
        else:
            dialog = BookDialog(app, book, parent)
            dialog.show()
            return dialog

    @classmethod
    def ensureClosed(cls, book):
        if book.id in cls.dialogs:
            dialog = cls.dialogs[book.id]
            del cls.dialogs[book.id]

            if not dialog.close():
                cls.dialogs[book.id] = dialog

    def __init__(self, app, book, parent):
        super(BookDialog, self).__init__(parent)
        self.app = app
        self.book = book

        # Create a stack of the form and a progress indicator.
        self.layoutStack = QStackedLayout()
        self.layoutStack.addWidget(self.initForm())
        self.layoutStack.addWidget(self.initProgressSpinner())
        self.setLayout(self.layoutStack)

        # Initialize form values.
        self.initValues()

        # Handle network responses.
        self.app.network.finished.connect(self.onNetworkRequestFinished)
        self.ticket = None

    def initForm(self):
        """Initializes the user interface."""
        form = QFormLayout()

        self.idBox = QLabel()
        form.addRow("ID:", self.idBox)

        self.isbnBox = QLineEdit()
        form.addRow("ISBN:", self.isbnBox)

        self.titleBox = QLineEdit()
        form.addRow("Titel:", self.titleBox)

        self.authorsBox = QLineEdit()
        form.addRow("Autoren:", self.authorsBox)

        self.volumeBox = QLineEdit()
        form.addRow("Band:", self.volumeBox)

        self.topicBox = QLineEdit()
        form.addRow("Thema:", self.topicBox)

        self.keywordsBox = QLineEdit()
        form.addRow(u"Schlüsselwörter", self.keywordsBox)

        self.signatureBox = QLineEdit()
        form.addRow("Signatur:", self.signatureBox)

        self.locationBox = QLineEdit()
        form.addRow("Standort:", self.locationBox)

        self.yearBox = QLineEdit()
        form.addRow("Jahr:", self.yearBox)

        self.publisherBox = QLineEdit()
        form.addRow("Verlag:", self.publisherBox)

        self.placeOfPublicationBox = QLineEdit()
        form.addRow(u"Veröffentlichungsort:", self.placeOfPublicationBox)

        buttonBox = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.onSaveClicked)
        buttonBox.rejected.connect(self.close)
        form.addRow(buttonBox)

        widget = QWidget()
        widget.setLayout(form)
        return widget

    def initValues(self):
        """Initialize the displayed values according to the book."""
        if self.book:
            self.setWindowTitle("Buch: %s" % self.book.title)
            self.idBox.setText(str(self.book.id))
        else:
            self.setWindowTitle("Neues Buch")
            self.idBox.setText("automatisch")
            self.book = Book()

        self.isbnBox.setText(self.book.isbn)
        self.titleBox.setText(self.book.title)
        self.authorsBox.setText(self.book.authors)

    def initProgressSpinner(self):
        """Initialize a progress indicator."""
        self.progressSpinner = progressspinner.ProgressSpinner()
        return self.progressSpinner

    def showProgress(self, visible):
        """Shows or hides the progress indicator."""
        if visible:
            self.progressSpinner.timer.start(100)
            self.layoutStack.setCurrentIndex(1)
        else:
            self.progressSpinner.timer.stop()
            self.layoutStack.setCurrentIndex(0)

    def isDirty(self):
        """Checks if anything has been changed and not saved."""
        # TODO: Actually do this.
        return True

    def save(self):
        """Validates and saves the current product."""
        params = QUrl()
        params.addQueryItem("_csrf", self.app.login.csrf)
        params.addQueryItem("isbn", self.isbnBox.text())
        params.addQueryItem("title", self.titleBox.text())
        params.addQueryItem("authors", self.authorsBox.text())
        params.addQueryItem("topic", self.topicBox.text())
        params.addQueryItem("keywords", self.keywordsBox.text())
        params.addQueryItem("signature", self.signatureBox.text())
        params.addQueryItem("location", self.locationBox.text())
        params.addQueryItem("year", self.yearBox.text())
        params.addQueryItem("publisher", self.publisherBox.text())
        params.addQueryItem("placeOfPublication", self.placeOfPublicationBox.text())
        params.addQueryItem("volume", self.volumeBox.text())
        params.addQueryItem("lendable", "true")

        if not self.book.id:
            request = QNetworkRequest(self.app.login.getUrl("/books/"))
            request.setHeader(QNetworkRequest.ContentTypeHeader, "application/x-www-form-urlencoded")
            self.ticket = self.app.network.http("POST", request, params.encodedQuery())
        else:
            assert False

        return True

    def onNetworkRequestFinished(self, reply):
        """Handles responses."""
        # Only handle requests that concern this dialog.
        if self.ticket != reply.request().attribute(network.Ticket):
            return

        self.showProgress(False)

        # Check for network errors.
        if reply.error() != QNetworkReply.NoError:
            QMessageBox.warning(self, self.windowTitle(), reply.errorString())
            return

        # Check for HTTP errors.
        status = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
        if status != 200:
            QMessageBox.warning(self, self.windowTitle(), "HTTP Status Code: %d" % status)
            return

        # Accepted.
        self.ticket = None
        self.accept()

    def onSaveClicked(self):
        """Handles a click on the save button."""
        if self.save():
            self.showProgress(True)

    def closeEvent(self, event):
        """Prevents the window from beeing closed if dirty."""
        # Saving in progress.
        if self.ticket:
            event.ignore()
            return

        # Close immediately if it should not be open.
        if self.book.id and not self.book.id in BookDialog.dialogs:
            event.accept()
            return

        # If there are changes, ask if they should be saved.
        if self.isDirty():
            result = QMessageBox.question(self, self.windowTitle(),
                u"Es gibt noch ungespeicherte Änderungen an diesem Buch.",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)

            if result == QMessageBox.Save:
                self.onSaveClicked()
                event.ignore()
                return
            elif result == QMessageBox.Cancel:
                event.ignore()
                return

        # Maintain list of open dialogs.
        if self.book.id in BookDialogs.dialogs:
            del BookDialogs.dialogs[self.book.id]

        event.accept()
