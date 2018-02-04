# TODO: keep running tally of selected file size
# TODO: unchecking item removes tristate on siblings
from pathlib import Path

from PyQt5 import QtCore, QtWidgets, QtGui
import os
import sys
import argparse


def debug_trace():
    '''Set a tracepoint in the Python debugger that works with Qt'''
    from PyQt5.QtCore import pyqtRemoveInputHook
    from pudb import set_trace
    pyqtRemoveInputHook()
    set_trace()


_checklist = set()
_partial_checklist = set()


def parseOpt():
    parser = argparse.ArgumentParser(
        description=('Select files and directories below path to be output as '
                     'a list'))
    parser.add_argument('--path', '-p', help='Root path',
                        default='.')
    parser.add_argument('selection', nargs='*')
    return parser.parse_args()


class PathConflict(Exception):
    pass


class DirTree:
    def __init__(self, paths):
        self.root = DirTreeItem()
        for path in paths:
            self.insert(path)

    def insert(self, path):
        path = Path(path)
        parent = self.root
        for index, part in enumerate(path.parts):
            if part not in parent:
                parent[part] = DirTreeItem(parent=parent, name=part)
            elif not parent[part]:
                msg = 'Conflicting paths starting with {}'
                msg = msg.format(os.path.join(*path.parts[:index+1]))
                raise PathConflict(msg)

            parent = parent[part]

    def remove(self, path):
        path = Path(path)
        pos = self.root
        for part in path.parts:
            pos = pos[part]

        # Delete node and any parents that become empty
        while not pos and pos is not self.root:
            parent = pos.parent
            del parent[pos.name]
            pos = parent

    def check(self, path):
        path = Path(path)
        pos = self.root
        for part in path.parts:
            if part in pos:
                pos = pos[part]
            else:
                return 'unselected'

        if pos:
            return 'parent'
        else:
            return 'leaf'


class DirTreeItem(dict):
    '''dict for nesting in other dicts

    Keeps reference to parent dict and its key in that parent. This
    allows one to traverse a tree of nested dicts from bottom to top
    and delete branches when no longer needed.
    '''
    def __init__(self, *args, name='', parent=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.name = name
        self.parent = parent


class CheckableFileSystemModel(QtWidgets.QFileSystemModel):
    selection_changed = QtCore.pyqtSignal(QtCore.QModelIndex,
                                          QtCore.QModelIndex,
                                          name='selectionChanged')

    def __init__(self, *args, preselection=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.preselection = DirTree(preselection)

    def handle_preselection(self, path):
        print('loaded', path)
        relpath = Path(path)
        relpath = relpath.relative_to(self.rootPath())

        index = self.index(path)
        for row in range(self.rowCount(index)):
            child = index.child(row, index.column())
            child_path = os.path.relpath(self.filePath(child),
                                         start=self.rootPath())
            status = self.preselection.check(child_path)
            if status == 'leaf':
                print('leaf', path)
                self.setData(child,
                             QtCore.Qt.Checked,
                             QtCore.Qt.CheckStateRole)
                self.preselection.remove(child_path)
                if not self.preselection.root:
                    self.directoryLoaded.disconnect(self.handle_preselection)
            elif status == 'parent' and self.isDir(child):
                self.fetchMore(child)

    def flags(self, index):
        return (QtWidgets.QFileSystemModel.flags(self, index) |
                QtCore.Qt.ItemIsUserCheckable)

    def data(self, index, role):
        persistent_index = QtCore.QPersistentModelIndex(index)
        if role == QtCore.Qt.CheckStateRole and index.column() == 0:
            if persistent_index in _checklist:
                return QtCore.Qt.Checked
            elif persistent_index in _partial_checklist:
                return QtCore.Qt.PartiallyChecked
            else:
                parent = index.parent()
                while (parent.isValid() and
                       self.filePath(parent) != self.rootPath()):
                    if QtCore.QPersistentModelIndex(parent) in _checklist:
                        return QtCore.Qt.PartiallyChecked
                    parent = parent.parent()
            return QtCore.Qt.Unchecked
        return super().data(index, role)

    def dataInternal(self, index):
        persistent_index = QtCore.QPersistentModelIndex(index)
        if persistent_index in _checklist:
            return QtCore.Qt.Checked
        elif persistent_index in _partial_checklist:
            return QtCore.Qt.PartiallyChecked
        else:
            return QtCore.Qt.Unchecked

    def hasAllSiblingsUnchecked(self, index):
        for i in range(self.rowCount(index.parent())):
            sibling = index.sibling(i, index.column())
            if sibling.isValid():
                if sibling == index:
                    continue
                if self.dataInternal(sibling) != QtCore.Qt.Unchecked:
                    return False
        return True

    def setUncheckedRecursive(self, index):
        if self.isDir(index):
            for i in range(self.rowCount(index)):
                child = index.child(i, index.column())
                if child.isValid():
                    # Only alter a child if it was previously Checked or
                    # PartiallyChecked.
                    if self.dataInternal(child) != QtCore.Qt.Unchecked:
                        self.setDataInternal(child, QtCore.Qt.Unchecked)
                        if self.isDir(child):
                            self.setUncheckedRecursive(child)

    def setData(self, index, value, role):
        if role == QtCore.Qt.CheckStateRole:
            self.setDataInternal(index, value)
            self.selection_changed.emit(index, index)
            self.dataChanged.emit(index, index, [])
            return True

        return super().setData(index, value, role)

    def setDataInternal(self, index, value):
        if self.dataInternal(index) == value:
            return

        persistent_index = QtCore.QPersistentModelIndex(index)
        if value == QtCore.Qt.Checked:
            _partial_checklist.discard(persistent_index)
            _checklist.add(persistent_index)

            parent = index.parent()
            if parent.isValid() and self.filePath(parent) != self.rootPath():
                self.setDataInternal(parent, QtCore.Qt.PartiallyChecked)

            self.setUncheckedRecursive(index)
        elif value == QtCore.Qt.PartiallyChecked:
            _checklist.discard(persistent_index)
            _partial_checklist.add(persistent_index)

            parent = index.parent()
            if parent.isValid():
                self.setDataInternal(parent, QtCore.Qt.PartiallyChecked)
        elif value == QtCore.Qt.Unchecked:
            _partial_checklist.discard(persistent_index)
            _checklist.discard(persistent_index)

            parent = index.parent()
            if (parent.isValid() and
                    self.filePath(parent) != self.rootPath() and
                    self.dataInternal(parent) != QtCore.Qt.Checked):
                if self.hasAllSiblingsUnchecked(index):
                    self.setDataInternal(parent, QtCore.Qt.Unchecked)


class Ui_Dialog(QtWidgets.QDialog):
    def __init__(self, args, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.setObjectName("Dialog")
        self.resize(600, 500)

        self.llayout = QtWidgets.QVBoxLayout(parent)

        self.model = CheckableFileSystemModel(preselection=args.selection)
        self.model.directoryLoaded.connect(self.model.handle_preselection)
        self.model.setRootPath(os.path.abspath(args.path))

        self.tree = QtWidgets.QTreeView()
        self.tree.setModel(self.model)
        self.tree.setSortingEnabled(True)
        self.tree.setRootIndex(self.model.index(os.path.abspath(args.path)))
        self.model.selection_changed.connect(self.update_view)

        self.setWindowTitle('Select files')
        self.tree.resize(400, 480)
        self.tree.setColumnWidth(0, 200)

        self.but = QtWidgets.QPushButton("OK")

        self.llayout.addWidget(self.tree)
        self.llayout.addWidget(self.but)

        self.setLayout(self.llayout)

        self.but.clicked.connect(self.print_path)

        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+Q"), self, self.close)
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+W"), self, self.close)

    def update_view(self):
        self.tree.viewport().update()

    def print_path(self):
        for item in _checklist:
            print(self.model.filePath(QtCore.QModelIndex(item)))


if __name__ == "__main__":
    args = parseOpt()
    app = QtWidgets.QApplication(sys.argv)
    ui = Ui_Dialog(args)
    ui.show()

    sys.exit(app.exec_())
