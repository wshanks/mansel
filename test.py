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
        self.selected = set()
        self.ancestors = set()

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
        return (super().flags(index) | QtCore.Qt.ItemIsUserCheckable)

    def data(self, index, role):
        if role != QtCore.Qt.CheckStateRole or index.column() != 0:
            return super().data(index, role)

        persistent_index = QtCore.QPersistentModelIndex(index)
        if persistent_index in self.selected:
            return QtCore.Qt.Checked
        elif persistent_index in self.ancestors:
            return QtCore.Qt.PartiallyChecked
        else:
            parent = index.parent()
            while (parent.isValid() and
                    self.filePath(parent) != self.rootPath()):
                if QtCore.QPersistentModelIndex(parent) in self.selected:
                    return QtCore.Qt.PartiallyChecked
                parent = parent.parent()
            return QtCore.Qt.Unchecked

    def _data(self, index):
        return self.data(index, QtCore.Qt.CheckStateRole)

    def hasAllSiblingsUnchecked(self, index):
        for i in range(self.rowCount(index.parent())):
            sibling = index.sibling(i, index.column())
            if sibling.isValid():
                if sibling == index:
                    continue
                if self._data(sibling) != QtCore.Qt.Unchecked:
                    return False
        return True

    def setData(self, index, value, role):
        if role != QtCore.Qt.CheckStateRole:
            return super().setData(index, value, role)

        self.setDataInternal(index, value)
        self.selection_changed.emit(index, index)
        self.dataChanged.emit(index, index, [])
        return True

    def setCheckStatus(self, index, value):
        persistent_index = QtCore.QPersistentModelIndex(index)

        if value == QtCore.Qt.Checked:
            self.ancestors.discard(persistent_index)
            self.selected.add(persistent_index)
        elif value == QtCore.Qt.PartiallyChecked:
            self.selected.discard(persistent_index)
            self.ancestors.add(persistent_index)
        elif value == QtCore.Qt.Unchecked:
            self.ancestors.discard(persistent_index)
            self.selected.discard(persistent_index)

    def setDataInternal(self, index, value):
        if self._data(index) == value:
            return

        self.setCheckStatus(index, value)

        if value == QtCore.Qt.Checked:
            parent = index.parent()
            while self.filePath(parent) != self.rootPath():
                self.setCheckStatus(parent, QtCore.Qt.PartiallyChecked)
                parent = parent.parent()

            # Make sure no checked descendants
            queue = [index.child(i, index.column())
                     for i in range(self.rowCount(index))]
            while queue:
                item = queue.pop()
                self.setCheckStatus(item, QtCore.Qt.Unchecked)
                queue.extend([item.child(i, index.column())
                              for i in range(self.rowCount(item))])

        elif value == QtCore.Qt.Unchecked:
            child = index
            while self.filePath(child.parent()) != self.rootPath():
                if self.hasAllSiblingsUnchecked(child):
                    self.setCheckStatus(child.parent(), QtCore.Qt.Unchecked)
                else:
                    break
                child = child.parent()


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
        self.model.dataChanged.connect(self.update_view)

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
        for item in self.model.selected:
            print(self.model.filePath(QtCore.QModelIndex(item)))


if __name__ == "__main__":
    args = parseOpt()
    app = QtWidgets.QApplication(sys.argv)
    ui = Ui_Dialog(args)
    ui.show()

    sys.exit(app.exec_())
