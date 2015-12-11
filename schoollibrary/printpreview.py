# -*- coding: utf-8 -*-

# Client for a schoollibrary-server.
# Copyright (c) 2014-2015 Niklas Fiekas <niklas@backscattering.de>
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

import os


class ZoomFactorValidator(QDoubleValidator):
    """Validator for the zoom factor field."""

    def validate(self, input, pos):
        """Passes the factor on to the double validator without the %."""
        replacePercent = False
        if input.endswith("%"):
            input = input[:-1]
            replacePercent = True

        state, input, pos = super(ZoomFactorValidator, self).validate(input, pos)

        if replacePercent:
            input += "%"

        # Ensure it does not exceed size.
        if state == QValidator.Intermediate:
            comma = QLocale.system().decimalPoint()
            if comma in input:
                if input.index(comma) > 4:
                    return QValidator.Invalid, input, pos
                elif len(input) > 4:
                    return QValidator.Invalid, input, pos

        return state, input, pos


class ExtendedPrintPreview(QWidget):
    """
    Wraps a print preview widget and a toolbar with actions for page fitting,
    zooming, navigating pages, printing and exporting to PDF.
    """

    def __init__(self, app, parent=None):
        super(ExtendedPrintPreview, self).__init__(parent)
        self.app = app

        # Create the controls.
        self._initToolBar()
        self._initPrintPreview()

        # Set the initial state.
        self.fitWidthAction.setChecked(True)
        self.singleModeAction.setChecked(True)

        # Put the controls into the layout.
        vbox = QVBoxLayout()
        vbox.addWidget(self.toolBar)
        vbox.addWidget(self.printPreview)
        self.setLayout(vbox)

    def _initToolBar(self):
        """Creates the tool bar."""
        self.toolBar = QToolBar()

        # Create page fitting actions.
        self.fitGroup = QActionGroup(self)
        self.fitWidthAction = self.fitGroup.addAction("An Breite anpassen")
        self.fitWidthAction.setIcon(QIcon(":/trolltech/dialogs/qprintpreviewdialog/images/fit-width-24.png"))
        self.fitWidthAction.setCheckable(True)
        self.fitPageAction = self.fitGroup.addAction("An Seite anpassen")
        self.fitPageAction.setIcon(QIcon(":/trolltech/dialogs/qprintpreviewdialog/images/fit-page-24.png"))
        self.fitPageAction.setCheckable(True)
        self.fitGroup.triggered.connect(self.onFitGroupTriggered)

        self.toolBar.addAction(self.fitWidthAction)
        self.toolBar.addAction(self.fitPageAction)
        self.toolBar.addSeparator()

        # Create zoom widgets and actions.
        self.zoomFactorBox = QComboBox()
        self.zoomFactorBox.setMinimumContentsLength(7)
        self.zoomFactorBox.setInsertPolicy(QComboBox.NoInsert)
        zoomEditor = QLineEdit()
        zoomEditor.setValidator(ZoomFactorValidator(1, 1000, 1, zoomEditor))
        self.zoomFactorBox.setLineEdit(zoomEditor)
        for factor in [12.5, 25, 50, 75, 100, 125, 150, 200, 400, 800]:
            self.zoomFactorBox.addItem("%s%%" % factor)
        zoomEditor.editingFinished.connect(self.onZoomFactorChanged)
        self.zoomFactorBox.currentIndexChanged.connect(self.onZoomFactorChanged)

        self.zoomGroup = QActionGroup(self)
        self.zoomInAction = self.zoomGroup.addAction(u"Größer")
        self.zoomInAction.setIcon(QIcon(":/trolltech/dialogs/qprintpreviewdialog/images/zoom-in-24.png"))
        self.zoomOutAction = self.zoomGroup.addAction("Kleiner")
        self.zoomOutAction.setIcon(QIcon(":/trolltech/dialogs/qprintpreviewdialog/images/zoom-out-24.png"))

        self.toolBar.addWidget(self.zoomFactorBox)
        self.toolBar.addAction(self.zoomInAction)
        self.toolBar.addAction(self.zoomOutAction)
        self.toolBar.addSeparator()

        # Set special repeat handling for the zoom actions.
        zoomInButton = self.toolBar.widgetForAction(self.zoomInAction)
        zoomInButton.setAutoRepeat(True)
        zoomInButton.setAutoRepeatInterval(200)
        zoomInButton.setAutoRepeatDelay(200)
        zoomInButton.clicked.connect(self.onZoomIn)
        zoomOutButton = self.toolBar.widgetForAction(self.zoomOutAction)
        zoomOutButton.setAutoRepeat(True)
        zoomOutButton.setAutoRepeatInterval(200)
        zoomOutButton.setAutoRepeatDelay(200)
        zoomOutButton.clicked.connect(self.onZoomOut)

        # Create the page navigation actions and widgets.
        self.navGroup = QActionGroup(self)
        self.navGroup.setExclusive(False)
        self.nextPageAction = self.navGroup.addAction(u"Nächste Seite")
        self.nextPageAction.setIcon(QIcon(":/trolltech/dialogs/qprintpreviewdialog/images/go-next-24.png"))
        self.prevPageAction = self.navGroup.addAction("Vorherige Seite")
        self.prevPageAction.setIcon(QIcon(":/trolltech/dialogs/qprintpreviewdialog/images/go-previous-24.png"))
        self.firstPageAction = self.navGroup.addAction("Erste Seite")
        self.firstPageAction.setIcon(QIcon(":/trolltech/dialogs/qprintpreviewdialog/images/go-first-24.png"))
        self.lastPageAction = self.navGroup.addAction("Letzte Seite")
        self.lastPageAction.setIcon(QIcon(":/trolltech/dialogs/qprintpreviewdialog/images/go-last-24.png"))
        self.navGroup.triggered.connect(self.onNavGroupTriggered)

        self.pageNumBox = QLineEdit()
        self.pageNumBox.setAlignment(Qt.AlignRight)
        self.pageNumBox.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
        self.pageNumBox.editingFinished.connect(self.onPageNumBoxEdited)

        self.pageNumLabel = QLabel()

        pageEdit = QWidget()
        wrapper = QVBoxLayout()
        wrapper.setContentsMargins(0, 0, 0, 0)
        formLayout = QFormLayout()
        formLayout.setWidget(0, QFormLayout.LabelRole, self.pageNumBox)
        formLayout.setWidget(0, QFormLayout.FieldRole, self.pageNumLabel)
        wrapper.addLayout(formLayout)
        wrapper.setAlignment(Qt.AlignVCenter)
        pageEdit.setLayout(wrapper)

        self.toolBar.addAction(self.firstPageAction)
        self.toolBar.addAction(self.prevPageAction)
        self.toolBar.addWidget(pageEdit)
        self.toolBar.addAction(self.nextPageAction)
        self.toolBar.addAction(self.lastPageAction)
        self.toolBar.addSeparator()

        # Create display mode actions.
        self.modeGroup = QActionGroup(self)
        self.singleModeAction = self.modeGroup.addAction("Einzelne Seiten zeigen")
        self.singleModeAction.setIcon(QIcon(":/trolltech/dialogs/qprintpreviewdialog/images/view-page-one-24.png"))
        self.singleModeAction.setCheckable(True)
        self.facingModeAction = self.modeGroup.addAction("Seiten paarweise zeigen")
        self.facingModeAction.setIcon(QIcon(":/trolltech/dialogs/qprintpreviewdialog/images/view-page-sided-24.png"))
        self.facingModeAction.setCheckable(True)
        self.overviewModeAction = self.modeGroup.addAction(u"Übersicht aller Seiten")
        self.overviewModeAction.setIcon(QIcon(":/trolltech/dialogs/qprintpreviewdialog/images/view-page-multi-24.png"))
        self.overviewModeAction.setCheckable(True)
        self.modeGroup.triggered.connect(self.onModeGroupTriggered)

        self.toolBar.addAction(self.singleModeAction)
        self.toolBar.addAction(self.facingModeAction)
        self.toolBar.addAction(self.overviewModeAction)
        self.toolBar.addSeparator()

        # Create printing and saving actions.
        self.printerGroup = QActionGroup(self)
        self.printAction = self.printerGroup.addAction("Drucken")
        self.printAction.setIcon(QIcon(":/trolltech/dialogs/qprintpreviewdialog/images/print-24.png"))
        self.printAction.triggered.connect(self.onPrint)
        self.pdfAction = self.printerGroup.addAction("Als PDF speichern")
        self.pdfAction.setIcon(QIcon(self.app.data("pdf.png")))
        self.pdfAction.triggered.connect(self.onPdf)

        self.toolBar.addAction(self.printAction)
        self.toolBar.addAction(self.pdfAction)

    def _initPrintPreview(self):
        """Creates the print preview widget."""
        self.printer = QPrinter()
        self.printPreview = QPrintPreviewWidget(self.printer)
        self.printPreview.previewChanged.connect(self.onPrintPreviewChanged)
        self.printPreview.fitToWidth()

    def setFitting(self, on):
        """Handles the exclusiveness of fitting and zooming."""
        self.fitGroup.setExclusive(on)
        if on:
            action = self.fitWidthAction if self.fitWidthAction.isChecked() else self.fitPageAction
            action.setChecked(True)
            if self.fitGroup.checkedAction() != action:
                self.fitGroup.removeAction(action)
                self.fitGroup.addAction(action)
        else:
            self.fitWidthAction.setChecked(False)
            self.fitPageAction.setChecked(False)

    def onFitGroupTriggered(self, action):
        """Handles the fit to page or the fit to width action."""
        self.setFitting(True)
        if action == self.fitPageAction:
            self.printPreview.fitInView()
        else:
            self.printPreview.fitToWidth()

    def onZoomFactorChanged(self):
        """Handles changes of the zoom factor."""
        text = self.zoomFactorBox.lineEdit().text()
        try:
            factor = max(1.0, min(1000.0, float(text.replace("%", "").replace(",", "."))))
            self.printPreview.setZoomFactor(factor / 100.0)
            self.setFitting(False)
        except ValueError:
            pass

    def onZoomIn(self):
        """Handles zooming in."""
        self.setFitting(False)
        self.printPreview.zoomIn()
        self.updateZoomFactor()

    def onZoomOut(self):
        """Handles zooming out."""
        self.setFitting(False)
        self.printPreview.zoomOut()
        self.updateZoomFactor()

    def onNavGroupTriggered(self, action):
        """Handles page navigation actions."""
        if action == self.prevPageAction:
            self.printPreview.setCurrentPage(self.printPreview.currentPage() - 1)
        elif action == self.nextPageAction:
            self.printPreview.setCurrentPage(self.printPreview.currentPage() + 1)
        elif action == self.firstPageAction:
            self.printPreview.setCurrentPage(1)
        elif action == self.lastPageAction:
            self.printPreview.setCurrentPage(self.printPreview.pageCount())
        self.updateNavActions()

    def onPageNumBoxEdited(self):
        """Handles changes of the current page edit field."""
        try:
            self.printPreview.setCurrentPage(int(self.pageNumBox.text()))
        except ValueError:
            pass

    def onModeGroupTriggered(self, action):
        """Handles the view mode actions."""
        if action == self.overviewModeAction:
            self.printPreview.setViewMode(QPrintPreviewWidget.AllPagesView)
            self.setFitting(False)
            self.fitGroup.setEnabled(False)
            self.navGroup.setEnabled(False)
            self.pageNumBox.setEnabled(False)
            self.pageNumLabel.setEnabled(False)
        else:
            if action == self.facingModeAction:
                self.printPreview.setViewMode(QPrintPreviewWidget.FacingPagesView)
            elif action == self.singleModeAction:
                self.printPreview.setViewMode(QPrintPreviewWidget.SinglePageView)

            self.fitGroup.setEnabled(True)
            self.navGroup.setEnabled(True)
            self.pageNumBox.setEnabled(True)
            self.pageNumLabel.setEnabled(True)
            self.setFitting(True)

    def onPrint(self, checked=False):
        """Handles the print action."""
        self.printer.setOutputFormat(QPrinter.NativeFormat)
        self.printer.setOutputFileName(None)
        dialog = QPrintDialog(self.printer, self)
        if dialog.exec_() == QDialog.Accepted:
            self.printPreview.print_()

    def onPdf(self):
        """Handles the PDF printing action."""
        fileName, selectedFilter = QFileDialog.getSaveFileName(self, "Als PDF speichern", os.path.expanduser("~"), "PDF Dokument (*.pdf)")
        if fileName:
            if not QFileInfo(fileName).suffix():
                fileName += ".pdf"
            self.printer.setOutputFormat(QPrinter.PdfFormat)
            self.printer.setOutputFileName(fileName)
            self.printPreview.print_()

    def onPrintPreviewChanged(self):
        """Handles changes of the print preview."""
        self.updateNavActions()
        self.updatePageNumLabel()
        self.updateZoomFactor()

    def updateZoomFactor(self):
        """Keeps the zoom factor selection in sync."""
        self.zoomFactorBox.lineEdit().setText("%0.1f%%" % (self.printPreview.zoomFactor() * 100))

    def updateNavActions(self):
        """Updates the page navigation states."""
        currentPage = self.printPreview.currentPage()
        pageCount = self.printPreview.pageCount()
        self.nextPageAction.setEnabled(currentPage < pageCount)
        self.prevPageAction.setEnabled(currentPage > 1)
        self.firstPageAction.setEnabled(currentPage > 1)
        self.lastPageAction.setEnabled(currentPage < pageCount)
        self.pageNumBox.setText(str(currentPage))

    def updatePageNumLabel(self):
        """Updates the page num label and the size of the edit field."""
        pageCount = self.printPreview.pageCount()
        maxChars = len(str(pageCount))
        self.pageNumLabel.setText("/ %d" % pageCount)

        cyphersWidth = self.fontMetrics().width("8" * maxChars)
        maxWidth = self.pageNumBox.minimumSizeHint().width() + cyphersWidth
        self.pageNumBox.setMinimumWidth(maxWidth)
        self.pageNumBox.setMaximumWidth(maxWidth)
        self.pageNumBox.setValidator(QIntValidator(1, pageCount, self.pageNumBox))
