# TODO: keep running tally of selected file size
# TODO: unchecking child tristates parents
# TODO: pre-populate from input list
from PyQt5 import QtCore, QtWidgets, QtGui
from pathlib import Path
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
_prechecklist = {}
_partial_checklist = set()


def parseOpt():
    parser = argparse.ArgumentParser(
        description=('Select files and directories below path to be output as '
                     'a list'))
    parser.add_argument('--path', '-p', help='Root path',
                        default='.')
    parser.add_argument('selection', nargs='*')
    return parser.parse_args()


class CheckableFileSystemModel(QtWidgets.QFileSystemModel):
    selection_changed = QtCore.pyqtSignal(QtCore.QModelIndex,
                                          QtCore.QModelIndex,
                                          name='selectionChanged')

    def checkedIndexes(self):
        return [QtCore.QModelIndex(i) for i in _checklist]

    def flags(self, index):
        return (QtWidgets.QFileSystemModel.flags(self, index) |
                QtCore.Qt.ItemIsUserCheckable)

    def data(self, index, role):
        persistent_index = QtCore.QPersistentModelIndex(index)
        if role == QtCore.Qt.CheckStateRole and index.column() == 0:
            if self.filePath(index) in _prechecklist:
                self.setDataInternal(index, QtCore.Qt.Checked)
                del _prechecklist[self.filePath(index)]
                return QtCore.Qt.Checked
            elif persistent_index in _checklist:
                return QtCore.Qt.Checked
            elif persistent_index in _partial_checklist:
                return QtCore.Qt.PartiallyChecked
            else:
                parent = index.parent()
                while parent.isValid():
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

    def setIndexCheckState(self, index, state):
        if self.dataInternal(index) != state:
            self.setDataInternal(index, state)

    def hasAllSiblingsUnchecked(self, index):
        for i in range(self.rowCount(index.parent())):
            sibling = index.sibling(i, index.column())
            if sibling.isValid():
                if sibling == index:
                    continue
                if self.dataInternal(sibling) != QtCore.Qt.Unchecked:
                    return False
        return True

    def hasCheckedAncestor(self, index):
        ancestor = index.parent()
        while ancestor.isValid():
            if self.dataInternal(ancestor) == QtCore.Qt.Checked:
                return True
            ancestor = ancestor.parent()
        return False

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
        persistent_index = QtCore.QPersistentModelIndex(index)
        if value == QtCore.Qt.Checked:
            _partial_checklist.discard(persistent_index)
            _checklist.add(persistent_index)

            parent = index.parent()
            previous_parent = index
            while parent.isValid():
                self.setIndexCheckState(parent, QtCore.Qt.PartiallyChecked)

                for ii in range(self.rowCount(parent)):
                    child = parent.child(ii, index.column())
                    if child.isValid():
                        if child == previous_parent:
                            continue
                        if (self.dataInternal(child) ==
                                QtCore.Qt.PartiallyChecked):
                            self.setIndexCheckState(child, QtCore.Qt.Unchecked)

                previous_parent = parent
                parent = parent.parent()

            self.setUncheckedRecursive(index)
        elif value == QtCore.Qt.PartiallyChecked:
            _checklist.discard(persistent_index)
            _partial_checklist.add(persistent_index)

            # Should the parent be partially checked?
            parent = index.parent()
            if (parent.isValid() and
                    (self.dataInternal(parent) == QtCore.Qt.Unchecked)):
                self.setIndexCheckState(parent, QtCore.Qt.PartiallyChecked)
        elif value == QtCore.Qt.Unchecked:
            _partial_checklist.discard(persistent_index)
            _checklist.discard(persistent_index)

            # Should the parent be unchecked?
            parent = index.parent()
            if (parent.isValid() and
                    (self.dataInternal(parent) != QtCore.Qt.Checked)):
                if self.hasAllSiblingsUnchecked(index):
                    self.setIndexCheckState(parent, QtCore.Qt.Unchecked)


class Ui_Dialog(QtWidgets.QDialog):
    def __init__(self, args, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.setObjectName("Dialog")
        self.resize(600, 500)

        self.llayout = QtWidgets.QVBoxLayout(parent)

        self.model = CheckableFileSystemModel()
        self.model.directoryLoaded.connect(print)
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


def populate_prechecklist(checklist, paths):
    """Store items to be checked at start time"""
    for path in paths:
        if os.path.exists(path):
            checklist[os.path.abspath(path)] = os.path.getsize(path)


def populate_dict_tree(tree, paths):
    for path in paths:
        path = Path(path)
        pos = tree
        for index, part in enumerate(path.parts[:-1]):
            if not isinstance(pos, dict):
                msg = 'Conflicting paths starting with {}'
                msg = msg.format(os.path.join(*path.parts[:index+1]))
                raise Exception(msg)
            elif part not in pos:
                pos[part] = {}

            pos = pos[part]

        if path.parts[-1] not in pos:
            pos[path.parts[-1]] = None
        else:
            msg = 'Conflicting paths starting with {}'.format(path)
            raise Exception(msg)


if __name__ == "__main__":
    args = parseOpt()
    populate_prechecklist(_prechecklist, args.selection)
    app = QtWidgets.QApplication(sys.argv)
    ui = Ui_Dialog(args)
    ui.show()

    sys.exit(app.exec_())
