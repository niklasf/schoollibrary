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
import datetime
import dateutil.parser

import indexed
import util
import busyindicator
import network


def normalize_isbn(isbn):
    """Validates and normalizes an ISBN-10 or ISBN-13."""
    isbn = isbn.replace("-", "").replace(" ", "").strip().upper()

    if not isbn:
        return isbn
    elif re.match(r"^([0-9]{9}X|[0-9]{10})$", isbn):
        checksum = 0

        for i in range(0, 9):
            checksum += (i + 1) * int(isbn[i])

        if isbn[9] == "X":
            checksum += 10 * 10
        else:
            checksum += 10 * int(isbn[9])

        if checksum % 11 == 0:
            return isbn
        else:
            raise ValueError("Invalid ISBN-10.")
    elif re.match(r"^([0-9]{13})$", isbn):
        factor = [ 1, 3 ]
        checksum = 0

        for i in range(0, 12):
            checksum += factor[i % 2] * int(isbn[i])

        if (int(isbn[12]) - ((10 - (checksum % 10)) % 10)) == 0:
            return isbn
        else:
            raise ValueError("Invalid ISBN-13.")
    else:
        raise ValueError("Invalid ISBN.")


class Book(object):
    """A book object."""

    def __init__(self):
        self.id = 0
        self.etag = 0
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

        self.bookPathPattern = re.compile(r".*\/books\/([0-9]+)\/$")
        self.lendingPathPattern = re.compile(r".*\/books\/([0-9]+)\/lending$")

    def index(self, row, column, parent=QModelIndex()):
        if parent.isValid() or not self.hasIndex(row, column, parent):
            return QModelIndex()
        else:
            return self.createIndex(row, column, self.cache.values()[row])

    def rowCount(self, parent=QModelIndex()):
        return len(self.cache)

    def columnCount(self, parent=QModelIndex()):
        return 16

    def data(self, index, role=Qt.DisplayRole):
        book = index.internalPointer()

        if role == Qt.DisplayRole:
            if index.column() == 0:
                return book.id
            elif index.column() == 1:
                return book.etag
            elif index.column() == 2:
                return book.signature
            elif index.column() == 3:
                return book.location
            elif index.column() == 4:
                return book.title
            elif index.column() == 5:
                return book.authors
            elif index.column() == 6:
                return book.topic
            elif index.column() == 7:
                return book.volume
            elif index.column() == 8:
                return book.keywords
            elif index.column() == 9:
                return book.publisher
            elif index.column() == 10:
                return book.placeOfPublication
            elif index.column() == 11:
                return book.year
            elif index.column() == 12:
                return book.isbn
            elif index.column() == 13:
                return book.edition
            elif index.column() == 14:
                return "Ja" if book.lendable else "Nein"
            elif index.column() == 15:
                if book.lent:
                    if book.lendingUser:
                        today = datetime.date.today()
                        since = dateutil.parser.parse(book.lendingSince).date()
                        duration = (today - since).days
                        if duration == 0:
                            return "%s seit heute" % (book.lendingUser)
                        elif duration == 1:
                            return "%s seit gestern" % (book.lendingUser)
                        else:
                            return "%s seit %d Tagen" % (book.lendingUser, duration)
                    return "Ja"
        elif role == Qt.UserRole:
            if index.column() == 14:
                return 1 if book.lendable else 0
            elif index.column() == 15:
                if book.lendingUser:
                    return book.lendingUser
                else:
                    return book.lent
            else:
                return index.data(Qt.DisplayRole)
        elif role == Qt.TextAlignmentRole:
            if index.column() in (0, 1, 2, 11, 12, 14):
                return Qt.AlignCenter
        elif role == Qt.FontRole:
            if index.column() == 4:
                font = QFont()
                font.setBold(True)
                return font
        elif role == Qt.BackgroundRole:
            if book.lent:
                if book.lendingUser:
                    # Highlight red if overdue.
                    today = datetime.date.today()
                    since = dateutil.parser.parse(book.lendingSince).date()
                    days = datetime.timedelta(days=book.lendingDays)
                    if today - since > days:
                        return QColor(231, 76, 60)
                return QColor(46, 204, 113)
            elif not book.lendable:
                return QColor(236, 240, 241)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal:
            if role == Qt.DisplayRole:
                if section == 0:
                    return "ID"
                if section == 1:
                    return "ETag"
                elif section == 2:
                    return "Signatur"
                elif section == 3:
                    return "Standort"
                elif section == 4:
                    return "Titel"
                elif section == 5:
                    return "Autoren"
                elif section == 6:
                    return "Thema"
                elif section == 7:
                    return "Band"
                elif section == 8:
                    return u"Schlüsselwörter"
                elif section == 9:
                    return "Verlag"
                elif section == 10:
                    return u"Veröffentlichungsort"
                elif section == 11:
                    return "Jahr"
                elif section == 12:
                    return "ISBN"
                elif section == 13:
                    return "Ausgabe"
                elif section == 14:
                    return "Ausleihbar"
                elif section == 15:
                    return "Ausgeliehen"

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
        status = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
        method = request.attribute(network.HttpMethod)
        path = request.url().path()

        if path.endswith("/books/") and request.attribute(network.HttpMethod) == "POST":
            # Book created.
            data = json.loads(str(reply.readAll()))
            book = self.bookFromData(data)

            assert not book.id in self.cache

            self.beginInsertRows(QModelIndex(), self.rowCount(), self.rowCount())
            self.cache[book.id] = book
            self.endInsertRows()
        elif path.endswith("/books/") and request.attribute(network.HttpMethod) == "GET":
            # Book list reloaded.
            self.beginResetModel()
            self.cache.clear()

            blob = str(reply.readAll())
            books = json.loads(blob)

            for key in books:
                book = self.bookFromData(books[key])
                self.cache[book.id] = book

            self.endResetModel()

        # Book updated.
        match = self.bookPathPattern.match(path)
        if match:
            id = int(match.group(1))

            if method in ("GET", "PUT") and status == 200:
                data = json.loads(str(reply.readAll()))
                book = self.bookFromData(data)
                if book.id in self.sache:
                    bookIndex = self.indexFromBook(self.cache[book.id])
                    self.cache[book.id] = book
                    self.dataChanged.emit(bookIndex, self.index(bookIndex.row(), self.columnCount() - 1, QModelIndex()))
                else:
                    self.beginInsertRows(QModelIndex(), self.rowCount(), self.rowCount())
                    self.cache[book.id] = book
                    self.endInsertRows()
            elif (method in ("GET", "PUT") and status == 404) or (method == "DELETE" and status in (200, 204)):
                if id in self.cache:
                    row = self.cache.keys.index(id)
                    self.beginRemoveRows(QModelIndex(), row, row)
                    del self.cache[id]
                    self.endRemoveRows()

        # Lending updated.
        match = self.lendingPathPattern.match(path)
        if match:
            id = int(match.group(1))
            if not id in self.cache:
                return

            book = self.cache[id]

            if method in ("POST", "PUT", "GET") and status == 200:
                data = json.loads(str(reply.readAll()))
                book.lent = True
                book.etag = int(reply.rawHeader(QByteArray("ETag")))
                book.lendingUser = data["user"]
                book.lendingSince = data["since"]
                book.lendingDays = int(data["days"])
            elif (method == "GET" and status == 404) or (method == "DELETE" and status in (200, 204)):
                book.lent = False
                book.etag = int(reply.rawHeader(QByteArray("ETag")))
                book.lendingUser = None
                book.lendingSince = None
                book.lendingDays = None

            bookIndex = self.indexFromBook(book)
            self.dataChanged.emit(bookIndex, self.index(bookIndex.row(), self.columnCount() - 1, QModelIndex()))

    def bookFromData(self, data):
        book = Book()

        book.id = int(data["_id"])
        book.etag = data["etag"]
        book.isbn = data["isbn"]
        book.title = data["title"]
        book.authors = data["authors"]
        book.volume = data["volume"]
        book.edition = data["edition"]
        book.topic = data["topic"]
        book.keywords = data["keywords"]
        book.signature = data["signature"]
        book.location = data["location"]
        book.year = int(data["year"]) if data["year"] else None
        book.publisher = data["publisher"]
        book.placeOfPublication = data["placeOfPublication"]
        book.lendable = bool(data["lendable"])
        book.lent = bool(data["lent"])

        if book.lent and "lending" in data:
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

    def getProxy(self):
        proxy = BookTableSortFilterProxyModel()
        proxy.setSourceModel(self)
        return proxy

    def getLentProxy(self):
        proxy = self.getProxy()
        proxy.lentOnly = True
        return proxy


class BookTableSortFilterProxyModel(QSortFilterProxyModel):
    """Sorts and filters an underlying book table model."""

    def __init__(self):
        super(BookTableSortFilterProxyModel, self).__init__()
        self.setDynamicSortFilter(True)
        self.setSortRole(Qt.UserRole)

        self.lentOnly = False

    def indexToBook(self, index):
        """Gets the book associated with an index."""
        return self.sourceModel().indexToBook(self.mapToSource(index))

    def indexFromBook(self, book):
        """Gets the index associated with a book."""
        return self.mapFromSource(self.sourceModel().indexFromBook(book))

    def filterAcceptsRow(self, row, parent=QModelIndex()):
        """Checks if a book should be displayed."""
        if self.lentOnly:
            book = self.sourceModel().indexToBook(self.sourceModel().index(row, 0, parent))
            if not book.lent:
                return False

        return True


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

        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        # Create a stack of the form and a busy indicator.
        self.layoutStack = QStackedLayout()
        self.layoutStack.addWidget(self.initForm())
        self.layoutStack.addWidget(self.initBusyIndicator())
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
        self.signatureBox.setMaxLength(50)
        form.addRow("Signatur:", self.signatureBox)

        self.locationBox = QLineEdit()
        form.addRow("Standort:", self.locationBox)

        self.yearBox = QLineEdit()
        form.addRow("Jahr:", self.yearBox)

        self.publisherBox = QLineEdit()
        form.addRow("Verlag:", self.publisherBox)

        self.placeOfPublicationBox = QLineEdit()
        form.addRow(u"Veröffentlichungsort:", self.placeOfPublicationBox)

        self.editionBox = QLineEdit()
        form.addRow("Auflage:", self.editionBox)

        self.lendableBox = QCheckBox()
        form.addRow("Ausleihbar:", self.lendableBox)

        buttonBox = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.onSaveClicked)
        buttonBox.rejected.connect(self.close)
        buttonBox.button(QDialogButtonBox.Cancel).setAutoDefault(False)
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
        self.volumeBox.setText(self.book.volume)
        self.topicBox.setText(self.book.topic)
        self.keywordsBox.setText(self.book.keywords)
        self.signatureBox.setText(self.book.signature)
        self.locationBox.setText(self.book.location)
        self.yearBox.setText(str(self.book.year) if self.book.year else "")
        self.publisherBox.setText(self.book.publisher)
        self.placeOfPublicationBox.setText(self.book.placeOfPublication)
        self.editionBox.setText(self.book.edition)
        self.lendableBox.setChecked(self.book.lendable)

    def initBusyIndicator(self):
        """Initialize a busy indicator."""
        self.busyIndicator = busyindicator.BusyIndicator()
        return self.busyIndicator

    def showBusy(self, visible):
        """Shows or hides the busy indicator."""
        if visible:
            self.busyIndicator.setEnabled(True)
            self.layoutStack.setCurrentIndex(1)
        else:
            self.busyIndicator.setEnabled(False)
            self.layoutStack.setCurrentIndex(0)

    def isDirty(self):
        """Checks if anything has been changed and not saved."""
        if self.isbnBox.text() != self.book.isbn:
            return True

        if self.titleBox.text() != self.book.title:
            return True

        if self.authorsBox.text() != self.book.authors:
            return True

        if self.volumeBox.text() != self.book.volume:
            return True

        if self.topicBox.text() != self.book.topic:
            return True

        if self.keywordsBox.text() != self.book.keywords:
            return True

        if self.signatureBox.text() != self.book.signature:
            return True

        if self.locationBox.text() != self.book.location:
            return True

        if not self.book.year:
            if self.yearBox.text():
                return True
        else:
            if self.yearBox.text() != str(self.book.year):
                return True

        if self.publisherBox.text() != self.book.publisher:
            return True

        if self.placeOfPublicationBox.text() != self.book.placeOfPublication:
            return True

        if self.editionBox.text() != self.book.edition:
            return True

        if self.lendableBox.isChecked() != self.book.lendable:
            return True

        return False

    def save(self):
        """Validates and saves the current product."""
        try:
            isbn = normalize_isbn(self.isbnBox.text())
        except ValueError:
            QMessageBox.warning(self, self.windowTitle(), u"Ungültige ISBN.")
            return False

        title = self.titleBox.text().strip()
        if not title:
            QMessageBox.warning(self, self.windowTitle(), "Ein Titel ist erforderlich.")
            return False

        year = self.yearBox.text().strip()
        if year:
            try:
                year = int(year)
            except ValueError:
                QMessageBox.warning(self, self.windowTitle(), u"Ungültige Eingabe für das Veröffentlichungsjahr.")
                return False

            if year < 0 or year > 3000:
                QMessageBox.warning(self, self.windowTitle(), u"Jahr ist außerhalb das gültigen Bereichs.")
                return False
        else:
            year = None

        params = QUrl()
        params.addQueryItem("_csrf", self.app.login.csrf)
        params.addQueryItem("etag", str(self.book.etag))
        params.addQueryItem("isbn", isbn)
        params.addQueryItem("title", title)
        params.addQueryItem("authors", self.authorsBox.text())
        params.addQueryItem("topic", self.topicBox.text())
        params.addQueryItem("keywords", self.keywordsBox.text())
        params.addQueryItem("signature", self.signatureBox.text())
        params.addQueryItem("location", self.locationBox.text())
        params.addQueryItem("year", str(year) if year else "")
        params.addQueryItem("publisher", self.publisherBox.text())
        params.addQueryItem("placeOfPublication", self.placeOfPublicationBox.text())
        params.addQueryItem("volume", self.volumeBox.text())
        params.addQueryItem("edition", self.editionBox.text())
        params.addQueryItem("lendable", "true" if self.lendableBox.isChecked() else "false")

        if not self.book.id:
            request = QNetworkRequest(self.app.login.getUrl("/books/"))
            request.setHeader(QNetworkRequest.ContentTypeHeader, "application/x-www-form-urlencoded")
            self.ticket = self.app.network.http("POST", request, params.encodedQuery())
        else:
            path = "/books/%d/" % self.book.id
            request = QNetworkRequest(self.app.login.getUrl(path))
            request.setHeader(QNetworkRequest.ContentTypeHeader, "application/x-www-form-urlencoded")
            self.ticket = self.app.network.http("PUT", request, params.encodedQuery())

        return True

    def onNetworkRequestFinished(self, reply):
        """Handles responses."""
        # Only handle requests that concern this dialog.
        if self.ticket != reply.request().attribute(network.Ticket):
            return

        self.ticket = None
        self.showBusy(False)

        # Check for network errors.
        if reply.error() == QNetworkReply.ContentNotFoundError:
            QMessageBox.warning(self, self.windowTitle(), u"Das Buch wurde inzwischen gelöscht.")
            self.reject()
            return
        elif reply.error() != QNetworkReply.NoError:
            QMessageBox.warning(self, self.windowTitle(), self.app.login.censorError(reply.errorString()))
            return

        # Check the HTTP status code.
        status = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
        if status != 200:
            QMessageBox.warning(self, self.windowTitle(), "HTTP Status Code: %d" % status)
            return

        # Accepted.
        self.accept()

    def onSaveClicked(self):
        """Handles a click on the save button."""
        if self.save():
            self.showBusy(True)

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
        if self.book.id in BookDialog.dialogs:
            del BookDialog.dialogs[self.book.id]

        event.accept()

    def sizeHint(self):
        """Make the dialog slightly wider than required."""
        size = super(BookDialog, self).sizeHint()
        return QSize(size.width() + 150, size.height())


class LendingDialog(QDialog):
    """A dialog for lending or returning a book."""

    dialogs = dict()

    @classmethod
    def open(cls, app, book, parent):
        if not book.id in cls.dialogs or not cls.dialogs[book.id].isVisible():
            cls.dialogs[book.id] = LendingDialog(app, book, parent)
            cls.dialogs[book.id].show()
        else:
            cls.dialogs[book.id].activateWindow()

    @classmethod
    def ensureClosed(cls, book):
        if book.id in cls.dialogs:
            cls.dialogs[book.id].close()

    def __init__(self, app, book, parent):
        super(LendingDialog, self).__init__(parent)
        self.app = app
        self.book = book

        self.setWindowIcon(QIcon(self.app.data("basket.png")))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        # Create the stack of the different views and a busy indicator.
        self.layoutStack = QStackedLayout()
        self.layoutStack.addWidget(self.initLendPage())
        self.layoutStack.addWidget(self.initReturnPage())
        self.layoutStack.addWidget(self.initBusyIndicator())
        self.setLayout(self.layoutStack)

        # Initialize the displayed values.
        self.updateValues(False)

        # Handle network responses.
        self.app.network.finished.connect(self.onNetworkRequestFinished)
        self.ticket = None

        # Handle book data changes.
        self.app.books.dataChanged.connect(self.onBooksDataChanged)
        self.app.books.modelReset.connect(self.onBooksModelReset)

    def onBooksDataChanged(self, topLeft, bottomRight):
        for row in xrange(topLeft.row(), bottomRight.row() + 1):
            if self.book.id == self.app.books.index(row, 0, QModelIndex()).data(Qt.UserRole):
                self.updateValues(False)
                break

    def onBooksModelReset(self):
        self.updateValues(False)

    def updateValues(self, busy):
        self.book = self.app.books.cache[self.book.id]

        if busy:
            self.layoutStack.setCurrentIndex(2)
            self.busyIndicator.setEnabled(True)
        else:
            self.busyIndicator.setEnabled(False)

        if not self.book.lent:
            self.setWindowTitle("Buch ausleihen: %s" % self.book.title)
            self.layoutStack.setCurrentIndex(0)
            self.lendIdBox.setText(str(self.book.id))
            self.lendIsbnBox.setText(self.book.isbn)
            self.lendTitleBox.setText(self.book.title)
            self.lendAuthorsBox.setText(self.book.authors)
            self.lendLocationBox.setText(self.book.location)
            self.lendLendableBox.setText("Ja" if self.book.lendable else "Nein")
            self.lendSignatureBox.setText(self.book.signature)
        else:
            self.setWindowTitle(u"Buch zurücknehmen: %s" % self.book.title)
            self.layoutStack.setCurrentIndex(1)
            self.returnIdBox.setText(str(self.book.id))
            self.returnIsbnBox.setText(self.book.isbn)
            self.returnTitleBox.setText(self.book.title)
            self.returnAuthorsBox.setText(self.book.authors)
            self.returnLocationBox.setText(self.book.location)
            self.returnSignatureBox.setText(self.book.signature)

            today = datetime.date.today()
            since = dateutil.parser.parse(self.book.lendingSince).date()
            duration = (today - since).days
            if duration == 0:
                self.returnLendingBox.setText("<a href=\"mailto:%s\">%s</a> seit heute" % (self.book.lendingUser, self.book.lendingUser))
            elif duration == 1:
                self.returnLendingBox.setText("<a href=\"mailto:%s\">%s</a> seit gestern" % (self.book.lendingUser, self.book.lendingUser))
            else:
                self.returnLendingBox.setText("<a href=\"mailto:%s\">%s</a> seit %d Tagen" % (self.book.lendingUser, self.book.lendingUser, duration))

            palette = self.returnLendingBox.palette()
            role = self.returnLendingBox.backgroundRole()
            if duration > self.book.lendingDays:
                palette.setColor(role, QColor(231, 76, 60))
            else:
                palette.setColor(role, QColor(46, 204, 113))
            self.returnLendingBox.setPalette(palette)

    def initLendPage(self):
        form = QFormLayout()

        self.lendSignatureBox = QLabel()
        form.addRow("Signatur:", self.lendSignatureBox)

        self.lendIdBox = QLabel()
        form.addRow("ID:", self.lendIdBox)

        self.lendLocationBox = QLabel()
        form.addRow("Standort:", self.lendLocationBox)

        self.lendTitleBox = QLabel()
        font = self.lendTitleBox.font()
        font.setBold(True)
        self.lendTitleBox.setFont(font)
        form.addRow("Titel:", self.lendTitleBox)

        self.lendAuthorsBox = QLabel()
        form.addRow("Autoren:", self.lendAuthorsBox)

        self.lendIsbnBox = QLabel()
        form.addRow("ISBN:", self.lendIsbnBox)

        self.lendLendableBox = QLabel()
        form.addRow("Ausleihbar:", self.lendLendableBox)

        self.lendUserBox = QComboBox()
        self.lendUserBox.setModel(self.app.users)
        self.lendUserBox.setEditable(True)
        self.lendUserBox.setInsertPolicy(QComboBox.NoInsert)
        self.lendUserBox.setCurrentIndex(-1)
        form.addRow("Ausleihen an:", self.lendUserBox)

        row = QHBoxLayout()
        row.addStretch(1)
        self.lendButton = QPushButton(u"Für 14 Tage ausleihen")
        self.lendButton.setIcon(QIcon(self.app.data("basket-go.png")))
        self.lendButton.clicked.connect(self.onLendButton)
        row.addWidget(self.lendButton)
        form.addRow(row)

        widget = QWidget()
        widget.setLayout(form)
        return widget

    def initReturnPage(self):
        form = QFormLayout()

        self.returnSignatureBox = QLabel()
        form.addRow("Signatur:", self.returnSignatureBox)

        self.returnIdBox = QLabel()
        form.addRow("ID:", self.returnIdBox)

        self.returnLocationBox = QLabel()
        form.addRow("Standort:", self.returnLocationBox)

        self.returnTitleBox = QLabel()
        font = self.returnTitleBox.font()
        font.setBold(True)
        self.returnTitleBox.setFont(font)
        form.addRow("Titel:", self.returnTitleBox)

        self.returnAuthorsBox = QLabel()
        form.addRow("Autoren:", self.returnAuthorsBox)

        self.returnIsbnBox = QLabel()
        form.addRow("ISBN:", self.returnIsbnBox)

        self.returnLendingBox = QLabel()
        self.returnLendingBox.setAutoFillBackground(True)
        self.returnLendingBox.setOpenExternalLinks(True)
        form.addRow("Geliehen von:", self.returnLendingBox)

        row = QHBoxLayout()
        row.addStretch(1)
        self.returnButton = QPushButton(u"Zurücknehmen")
        self.returnButton.setIcon(QIcon(self.app.data("basket-back.png")))
        self.returnButton.clicked.connect(self.onReturnButton)
        row.addWidget(self.returnButton)
        form.addRow(row)

        widget = QWidget()
        widget.setLayout(form)
        return widget

    def initBusyIndicator(self):
        self.busyIndicator = busyindicator.BusyIndicator()
        return self.busyIndicator

    def onLendButton(self):
        user = self.lendUserBox.currentText()

        params = QUrl()
        params.addQueryItem("_csrf", self.app.login.csrf)
        params.addQueryItem("user", user)
        params.addQueryItem("days", str(14))
        params.addQueryItem("etag", str(self.book.etag))

        path = "/books/%d/lending" % self.book.id
        request = QNetworkRequest(self.app.login.getUrl(path))
        request.setHeader(QNetworkRequest.ContentTypeHeader, "application/x-www-form-urlencoded")
        self.ticket = self.app.network.http("POST", request, params.encodedQuery())
        self.updateValues(True)

    def onReturnButton(self):
        path = "/books/%d/lending" % self.book.id
        request = QNetworkRequest(self.app.login.getUrl(path))
        request.setRawHeader(QByteArray("X-CSRF-Token"), QByteArray(self.app.login.csrf))
        self.ticket = self.app.network.http("DELETE", request)
        self.updateValues(True)

    def closeEvent(self, event):
        # Saving in progress.
        if self.ticket:
            event.ignore()
            return

        # Maintain list of open dialogs.
        if self.book.id in LendingDialog.dialogs:
            del LendingDialog.dialogs[self.book.id]

        event.accept()

    def onNetworkRequestFinished(self, reply):
        # Only handle requests concerning this dialog.
        request = reply.request()
        if request.attribute(network.Ticket) != self.ticket:
            return

        # Update the user interface.
        self.ticket = None
        self.updateValues(False)

        # Check for network errors.
        if reply.error() != QNetworkReply.NoError:
            QMessageBox.warning(self, self.windowTitle(), self.app.login.censorError(reply.errorString()))
            return

        # Check for HTTP errors.
        status = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
        if not status in (200, 204):
            QMessageBox.warning(self, self.windowTitle(), "HTTP Status Code: %d" % status)
            return
