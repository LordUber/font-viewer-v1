import sys
import os
import zipfile
import tempfile

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QSplitter, QListWidget, QListWidgetItem,
    QFileDialog, QWidget, QGridLayout, QScrollArea,
    QPlainTextEdit, QAction, QMessageBox, QToolBar,
    QLabel, QLineEdit, QCheckBox, QShortcut
)
from PyQt5.QtGui import QFontDatabase, QFont, QFontMetrics, QIntValidator, QKeySequence
from PyQt5.QtCore import Qt, QDir, QStandardPaths

# Supported font extensions
FONT_EXTS = ('.ttf', '.otf')
ARCHIVE_EXT = '.zip'
ASCII_RANGE = range(32, 127)  # printable ASCII

class FontPreviewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Font Previewer")

        # Size window to 90% of available screen area
        screen = QApplication.primaryScreen().availableGeometry()
        width = int(screen.width() * 0.9)
        height = int(screen.height() * 0.9)
        x = screen.x() + (screen.width() - width) // 2
        y = screen.y() + (screen.height() - height) // 2
        self.setGeometry(x, y, width, height)

        # Menu Bar: File and Help
        fileMenu = self.menuBar().addMenu("File")
        openFolder = QAction("Open Folder…", self)
        openFolder.triggered.connect(self.open_folder)
        fileMenu.addAction(openFolder)

        helpMenu = self.menuBar().addMenu("Help")
        aboutAction = QAction("About", self)
        aboutAction.triggered.connect(self.show_about)
        helpMenu.addAction(aboutAction)

        # Toolbar for size/bold/italic
        tb = QToolBar("Font Controls", self)
        self.addToolBar(tb)
        tb.addWidget(QLabel(" Size:"))
        self.sizeEdit = QLineEdit("56", self)
        self.sizeEdit.setMaximumWidth(50)
        self.sizeEdit.setValidator(QIntValidator(1, 500, self))
        self.sizeEdit.editingFinished.connect(self.update_font_settings)
        tb.addWidget(self.sizeEdit)
        self.boldCheck = QCheckBox("Bold", self)
        self.boldCheck.stateChanged.connect(self.update_font_settings)
        tb.addWidget(self.boldCheck)
        self.italicCheck = QCheckBox("Italic", self)
        self.italicCheck.stateChanged.connect(self.update_font_settings)
        tb.addWidget(self.italicCheck)

        # Main splitter: left file list, right vertical panels
        outer = QSplitter(Qt.Horizontal)
        self.setCentralWidget(outer)

        # Left: file list
        self.fileList = QListWidget()
        self.fileList.setMouseTracking(True)
        self.fileList.itemClicked.connect(self.on_file_clicked)
        outer.addWidget(self.fileList)

        # Right: preview and text
        rightSplit = QSplitter(Qt.Vertical)
        outer.addWidget(rightSplit)
        outer.setStretchFactor(1, 3)

        # Top: glyph preview
        self.previewWidget = QWidget()
        # ensure white background
        self.previewWidget.setStyleSheet("background-color: white;")
        self.previewLayout = QGridLayout()
        self.previewWidget.setLayout(self.previewLayout)
        self.previewScroll = QScrollArea()
        # set scroll viewport white too
        self.previewScroll.setStyleSheet("background-color: white;")
        self.previewScroll.setWidgetResizable(True)
        self.previewScroll.setWidget(self.previewWidget)
        rightSplit.addWidget(self.previewScroll)

        # Bottom: text entry
        self.textEdit = QPlainTextEdit()
        self.textEdit.setPlaceholderText("Type here…")
        self.textEdit.textChanged.connect(self.on_text_changed)
        rightSplit.addWidget(self.textEdit)

        # Ctrl+C clears text
        clear_sc = QShortcut(QKeySequence("Ctrl+C"), self.textEdit)
        clear_sc.activated.connect(self.textEdit.clear)

        # Split 50/50
        rightSplit.setStretchFactor(0, 1)
        rightSplit.setStretchFactor(1, 1)
        rightSplit.setSizes([height//2, height//2])

        # Default folder: Documents/fonts or Documents
        docs = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
        fonts_dir = os.path.join(docs, 'fonts')
        self.currentFolder = fonts_dir if os.path.isdir(fonts_dir) else docs

        # Initial font state
        self.currentFont = QApplication.font()
        self.currentFontSize = 56

        # Load folder contents and focus text entry
        self.load_folder(self.currentFolder)
        self.textEdit.setFocus()

    def show_about(self):
        # Custom about dialog: centered content and manual padding
        mb = QMessageBox(self)
        mb.setWindowTitle("About Font Previewer")
        mb.setTextFormat(Qt.RichText)
        mb.setText(
            '<div align="center">'
            'Developed by <a href="http://www.mathiasnagy.com">Mathias Nagy</a>&nbsp;&nbsp;&nbsp;<br>'
            '<br>'
            '&nbsp;Coded by ChatGPT&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<br>'
            '<br>'
            '&nbsp;23 April 2025&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;'
            '</div>'
        )
        mb.setStandardButtons(QMessageBox.Ok)
        mb.exec_()

    def open_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Select Font Folder", self.currentFolder)
        if d:
            self.load_folder(d)

    def load_folder(self, folder):
        self.currentFolder = folder
        self.fileList.clear()
        for fn in sorted(os.listdir(folder), key=str.lower):
            low = fn.lower()
            if low.endswith(FONT_EXTS) or low.endswith(ARCHIVE_EXT):
                item = QListWidgetItem(fn)
                full = os.path.join(folder, fn)
                if low.endswith(ARCHIVE_EXT):
                    try:
                        with zipfile.ZipFile(full) as z:
                            contains = any(n.lower().endswith(FONT_EXTS) for n in z.namelist())
                        item.setToolTip(full if contains else "no fonts in here")
                    except zipfile.BadZipFile:
                        item.setToolTip("invalid zip")
                else:
                    item.setToolTip(full)
                self.fileList.addItem(item)

    def on_file_clicked(self, item):
        path = os.path.join(self.currentFolder, item.text())
        low = path.lower()
        if low.endswith(ARCHIVE_EXT):
            try:
                with zipfile.ZipFile(path) as z:
                    candidates = [n for n in z.namelist() if n.lower().endswith(FONT_EXTS)]
                    if not candidates:
                        QMessageBox.information(self, "No Fonts", "no fonts in here")
                        return
                    data = z.read(candidates[0])
            except zipfile.BadZipFile:
                QMessageBox.warning(self, "Error", "Invalid ZIP archive")
                return
            ext = os.path.splitext(candidates[0])[1]
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
            tmp.write(data)
            tmp.close()
            font_path = tmp.name
        elif low.endswith(FONT_EXTS):
            font_path = path
        else:
            return
        self.load_font(font_path)

    def load_font(self, path):
        while self.previewLayout.count():
            w = self.previewLayout.takeAt(0).widget()
            if w:
                w.deleteLater()
        font_id = QFontDatabase.addApplicationFont(path)
        if font_id < 0:
            QMessageBox.warning(self, "Error", "Failed to load font.")
            return
        fams = QFontDatabase.applicationFontFamilies(font_id)
        if not fams:
            QMessageBox.warning(self, "Error", "No font family found.")
            return
        fam = fams[0]
        self.currentFont = QFont(fam, self.currentFontSize)
        self.apply_style_flags()
        self.render_preview()
        self.textEdit.setFont(self.currentFont)
        self.textEdit.setFocus()

    def render_preview(self):
        while self.previewLayout.count():
            w = self.previewLayout.takeAt(0).widget()
            if w:
                w.deleteLater()
        fm = QFontMetrics(self.currentFont)
        default_font = QApplication.font()
        supported = [chr(c) for c in ASCII_RANGE if fm.inFont(chr(c))]
        if not supported:
            self.previewLayout.addWidget(QLabel("no characters in file"), 0, 0)
            return
        cols = 10
        for i, ch in enumerate(supported):
            r = (i // cols) * 2
            c = i % cols
            lbl_sys = QLabel(ch)
            lbl_sys.setFont(default_font)
            self.previewLayout.addWidget(lbl_sys, r, c)
            lbl_fnt = QLabel(ch)
            lbl_fnt.setFont(self.currentFont)
            self.previewLayout.addWidget(lbl_fnt, r+1, c)

    def update_font_settings(self):
        try:
            sz = int(self.sizeEdit.text())
            if sz > 0:
                self.currentFontSize = sz
        except ValueError:
            pass
        self.apply_style_flags()
        if self.currentFont:
            self.currentFont.setPointSize(self.currentFontSize)
            self.render_preview()
            self.textEdit.setFont(self.currentFont)

    def apply_style_flags(self):
        if self.currentFont:
            self.currentFont.setBold(self.boldCheck.isChecked())
            self.currentFont.setItalic(self.italicCheck.isChecked())

    def on_text_changed(self):
        if self.textEdit.verticalScrollBar().maximum() > 0:
            self.textEdit.clear()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = FontPreviewer()
    win.show()
    sys.exit(app.exec_())
