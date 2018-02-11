'''File picker class for selecting multiple files.

CheckablefileSystemModel supports selecting multiple files/directories
from a tree view and also supports creation with a pre-selected set of
paths.
'''
# TODO: keep running tally of selected file size
from pathlib import Path

from PyQt5 import QtCore, QtWidgets, QtGui
import os
import sys


def debug_trace():
    '''Set a tracepoint in the Python debugger that works with Qt'''
    from PyQt5.QtCore import pyqtRemoveInputHook
    from pudb import set_trace
    pyqtRemoveInputHook()
    set_trace()


class PathConflict(Exception):
    'Exception raised by inconsistent paths in a DirTree'
    pass


class DirTree:
    '''Tree of nested dicts modeling a file system

    "root" property points ot root of tree which is a dict point to
    other dicts. Endpoints in the tree are represented by empty dicts.
    '''
    def __init__(self, paths):
        self.root = DirTreeItem()
        for path in paths:
            self.insert(path)

    def insert(self, path):
        'Insert path into the tree'
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
        'Remove path from the tree'
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
        '''Check if path is in tree

        Return:
            'leaf': in tree with no elements below
            'parent': in tree with elements nested below
            'unselected': not in tree
        '''
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
    '''QFileSystemModel subclass supporting multiple selection and preselection

    Internally, CheckableFileSystemModel stores all checked items in
    the 'selected' preperty. All ancestors are stored in the
    'ancestors' property.
    '''

    selectionChanged = QtCore.pyqtSignal(QtCore.QFileInfo, int)

    def __init__(self, *args, preselection=None, track_selection_size=True,
                 **kwargs):
        'preselection: list of paths relative to rootPath to pre-select'
        super().__init__(*args, **kwargs)
        self.preselection = DirTree(preselection)
        self.selected = set()
        self.ancestors = set()

        self.directoryLoaded.connect(self._handle_preselection)

        if track_selection_size:
            pass

    def _handle_preselection(self, path):
        '''Method for expanding model paths to load pre-selected items

        This method is used as a slot to connect to the directoryLoaded
        siganl. When a path is loaded, it is passed here where all its
        children are checked to see if any are related to the
        pre-selection. Pre-selected patsh are marked as
        checked. Ancestors of pre-selected paths are loaded.
        '''
        relpath = Path(path)
        relpath = relpath.relative_to(self.rootPath())

        index = self.index(path)
        for row in range(self.rowCount(index)):
            child = index.child(row, index.column())
            child_path = os.path.relpath(self.filePath(child),
                                         start=self.rootPath())
            status = self.preselection.check(child_path)
            if status == 'leaf':
                self.setData(child,
                             QtCore.Qt.Checked,
                             QtCore.Qt.CheckStateRole)
                self.preselection.remove(child_path)
                if not self.preselection.root:
                    self.directoryLoaded.disconnect(self._handle_preselection)
            elif status == 'parent' and self.isDir(child):
                self.fetchMore(child)

    def flags(self, index):
        'Enable checkboxes'
        return super().flags(index) | QtCore.Qt.ItemIsUserCheckable

    def data(self, index, role):
        # Override parent class method to handle checkboxes
        if role == QtCore.Qt.CheckStateRole and index.column() == 0:
            return self._data(index)
        else:
            return super().data(index, role)

    def _data(self, index):
        'Get checkbox status data'
        persistent_index = QtCore.QPersistentModelIndex(index)
        if persistent_index in self.selected:
            return QtCore.Qt.Checked
        elif (persistent_index in self.ancestors or
              self._has_checked_ancestor(index)):
            return QtCore.Qt.PartiallyChecked
        else:
            return QtCore.Qt.Unchecked

    def _has_checked_ancestor(self, index):
        parent = index.parent()
        while (parent.isValid() and
                self.filePath(parent) != self.rootPath()):
            if QtCore.QPersistentModelIndex(parent) in self.selected:
                return True
            parent = parent.parent()

        return False

    def setData(self, index, value, role):
        # Override parent class method to handle checkboxes
        if role == QtCore.Qt.CheckStateRole:
            return self._setData(index, value)
        else:
            return super().setData(index, value, role)

    def _setData(self, index, value):
        'Set checkbox status data and update ancestors/descendants'
        if self._data(index) == value:
            return True

        self._set_check_state(index, value)

        if value == QtCore.Qt.Checked:
            self._partially_check_ancestors(index)
            self._uncheck_descendants(index)
        elif value == QtCore.Qt.Unchecked:
            self._uncheck_exclusive_ancestors(index)

        self.selectionChanged.emit(self.fileInfo(index), value)
        self.dataChanged.emit(index, index, [])
        return True

    def _set_check_state(self, index, value):
        'Set checkbox status data with no side effects on other indexes'
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

    def _partially_check_ancestors(self, index):
        'Mark all ancestors of index as checked'
        parent = index.parent()
        while self.filePath(parent) != self.rootPath():
            self._set_check_state(parent, QtCore.Qt.PartiallyChecked)
            parent = parent.parent()

    def _uncheck_descendants(self, index):
        'Mark all descendants of index as unchecked'
        queue = [index.child(i, index.column())
                 for i in range(self.rowCount(index))]
        while queue:
            item = queue.pop()
            self._set_check_state(item, QtCore.Qt.Unchecked)
            queue.extend(item.child(i, index.column())
                         for i in range(self.rowCount(item)))

    def _uncheck_exclusive_ancestors(self, index):
        'Uncheck ancestors of index that have no other checked descendants'
        parent = index.parent()
        while self.filePath(parent) != self.rootPath():
            child_data = (self._data(parent.child(i, index.column()))
                          for i in range(self.rowCount(parent)))
            if all(state == QtCore.Qt.Unchecked for state in child_data):
                self._set_check_state(parent, QtCore.Qt.Unchecked)
            else:
                break
            parent = parent.parent()


class Ui_Dialog(QtWidgets.QDialog):
    def __init__(self, args, parent=None):
        QtWidgets.QDialog.__init__(self, parent)

        self.model = CheckableFileSystemModel(preselection=args.selection)
        self.model.setRootPath(os.path.abspath(args.path))
        self.model.dataChanged.connect(self.update_view)

        self.tree = QtWidgets.QTreeView()
        self.tree.setModel(self.model)
        self.tree.setSortingEnabled(True)
        self.tree.setRootIndex(self.model.index(os.path.abspath(args.path)))

        self.button = QtWidgets.QPushButton("OK")
        self.button.clicked.connect(self.print_path)

        layout = QtWidgets.QVBoxLayout(parent)
        layout.addWidget(self.tree)
        layout.addWidget(self.button)
        self.setLayout(layout)

        self.setObjectName("Dialog")
        self.resize(600, 500)
        self.setWindowTitle('Select files')
        self.tree.resize(400, 480)
        self.tree.setColumnWidth(0, 200)

        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+Q"), self, self.close)
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+W"), self, self.close)

    def update_view(self):
        self.tree.viewport().update()

    def print_path(self):
        for item in self.model.selected:
            print(self.model.filePath(QtCore.QModelIndex(item)))


if __name__ == "__main__":
    def parse_options():
        'Parse command line arguments'
        import argparse
        parser = argparse.ArgumentParser(
            description=('Select files and directories below path to be output '
                         'as a list'))
        parser.add_argument('--path', '-p', help='Root path',
                            default='.')
        parser.add_argument('selection', nargs='*')
        return parser.parse_args()

    args = parse_options()
    app = QtWidgets.QApplication([])
    ui = Ui_Dialog(args)
    ui.show()

    sys.exit(app.exec_())
