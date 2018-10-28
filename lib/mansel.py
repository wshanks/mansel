'''File picker class for selecting multiple files.

CheckablefileSystemModel supports selecting multiple files/directories
from a tree view and also supports creation with a pre-selected set of
paths.
'''
import os
from pathlib import Path
import sys
import typing as t

try:
    from PySide2 import QtCore, QtWidgets, QtGui
    Signal = QtCore.Signal
    Slot = QtCore.Slot
except ImportError:
    try:
        from manselqtshim import QtCore, QtWidgets, QtGui, Signal, Slot
    except ImportError:
        raise ImportError('PySide2 or other Qt binding required!') from None


class PathConflict(Exception):
    'Exception raised by inconsistent paths in a DirTree'
    pass


class DirTree:
    '''Tree of nested dicts modeling a file system

    "root" property points ot root of tree which is a dict point to
    other dicts. Endpoints in the tree are represented by empty dicts.
    '''
    def __init__(self, paths: t.Iterable[str]) -> None:
        self.root = DirTreeItem()
        for path in paths:
            self.insert(Path(path))

    def insert(self, path: Path) -> None:
        'Insert path into the tree'
        parent = self.root
        for index, part in enumerate(path.parts):
            if part not in parent:
                parent[part] = DirTreeItem(parent=parent, name=part)
            elif not parent[part]:
                msg = 'Conflicting paths starting with {}'
                msg = msg.format(os.path.join(*path.parts[:index+1]))
                raise PathConflict(msg)

            parent = parent[part]

    def remove(self, path: Path) -> None:
        'Remove path from the tree'
        pos = self.root
        for part in path.parts:
            pos = pos[part]

        # Delete node and any parents that become empty
        while not pos and pos is not self.root:
            parent = pos.parent
            del parent[pos.name]
            pos = parent

    def check(self, path: Path) -> str:
        '''Check if path is in tree

        Return:
            'leaf': in tree with no elements below
            'parent': in tree with elements nested below
            'unselected': not in tree
        '''
        pos = self.root
        for part in path.parts:
            if part in pos:
                pos = pos[part]
            else:
                return 'unselected'

        if pos:
            return 'parent'
        # else
        return 'leaf'


class DirTreeItem(dict):
    '''dict for nesting in other dicts

    Keeps reference to parent dict and its key in that parent. This
    allows one to traverse a tree of nested dicts from bottom to top
    and delete branches when no longer needed.
    '''
    def __init__(self, *args,
                 name: str = '',
                 parent: t.Optional['DirTreeItem'] = None,
                 **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.name = name
        self.parent = parent


class CheckableFileSystemModel(QtWidgets.QFileSystemModel):
    '''QFileSystemModel subclass supporting multiple selection and preselection

    Internally, CheckableFileSystemModel stores all checked items in
    the 'selected' preperty. All ancestors are stored in the
    'ancestors' property.
    '''

    preselectionProcessed = Signal()
    newDirSelected = Signal(str)
    recalculatingSize = Signal()
    newSelectionSize = Signal(int)

    def __init__(self,
                 parent: QtCore.QObject = None,
                 preselection: t.Optional[t.Iterable[str]] = None,
                 track_selection_size: bool = True) -> None:
        'preselection: list of paths relative to rootPath to pre-select'
        super().__init__(parent=parent)
        if preselection is not None:
            self.preselection = DirTree(preselection)
            self.directoryLoaded.connect(self._handle_preselection)
        else:
            self.preselection = None
        self.selected: t.Set[QtCore.QPersistentModelIndex] = set()
        self.ancestors: t.Set[QtCore.QPersistentModelIndex] = set()

        self.track_selection_size = track_selection_size
        self.tracker_thread = None
        self.tracker = None
        self.dir_size_cache: t.Dict[str, int] = {}
        if track_selection_size:
            self.tracker = DirSizeFetcher(self)
            self.tracker_thread = QtCore.QThread()
            self.tracker.moveToThread(self.tracker_thread)
            self.newDirSelected.connect(self.tracker.fetch_size)
            self.tracker.resultReady.connect(self._update_dir_size_cache)
            if hasattr(parent, 'finished'):
                parent.finished.connect(self.tracker_thread.quit)
            else:
                print('CheckableFileSystemModel parent has no "finished" '
                      'signal. Tracker thread must be shut down cleanly.',
                      file=sys.stderr)
            self.tracker_thread.start()

    def _handle_preselection(self, path: str) -> None:
        '''Method for expanding model paths to load pre-selected items

        This method is used as a slot to connect to the directoryLoaded
        siganl. When a path is loaded, it is passed here where all its
        children are checked to see if any are related to the
        pre-selection. Pre-selected patsh are marked as
        checked. Ancestors of pre-selected paths are loaded.
        '''
        index = self.index(path)
        for row in range(self.rowCount(index)):
            child = index.child(row, index.column())
            child_path = (Path(self.filePath(child)).
                          relative_to(self.rootPath()))
            status = self.preselection.check(child_path)
            if status == 'leaf':
                self.setData(child,
                             QtCore.Qt.Checked,
                             QtCore.Qt.CheckStateRole)
                self.preselection.remove(child_path)
                if not self.preselection.root:
                    self.directoryLoaded.disconnect(self._handle_preselection)
                    self.preselectionProcessed.emit()
            elif status == 'parent' and self.isDir(child):
                print('yes!')
                self.fetchMore(child)

    def flags(self, index: QtCore.QModelIndex) -> int:
        'Enable checkboxes'
        if not index.isValid():
            return super().flags(index)

        return super().flags(index) | QtCore.Qt.ItemIsUserCheckable

    def data(self, index: QtCore.QModelIndex, role: int) -> t.Any:
        'Data for given model index and role'
        # Override parent class method to handle checkboxes
        if role == QtCore.Qt.CheckStateRole and index.column() == 0:
            return self._data(index)
        # else
        return super().data(index, role)

    def _data(self, index: QtCore.QModelIndex) -> int:
        'Get checkbox status data'
        persistent_index = QtCore.QPersistentModelIndex(index)
        if persistent_index in self.selected:
            return QtCore.Qt.Checked
        elif (persistent_index in self.ancestors or
              self._has_checked_ancestor(index)):
            return QtCore.Qt.PartiallyChecked
        # else
        return QtCore.Qt.Unchecked

    def _has_checked_ancestor(self, index: QtCore.QModelIndex) -> bool:
        parent = index.parent()
        while (parent.isValid() and
               self.filePath(parent) != self.rootPath()):
            if QtCore.QPersistentModelIndex(parent) in self.selected:
                return True
            parent = parent.parent()

        return False

    def setData(self,  # pylint: disable=invalid-name
                index: QtCore.QModelIndex, value: t.Any,
                role: int) -> bool:
        'Set model data for index'
        # Override parent class method to handle checkboxes
        if role == QtCore.Qt.CheckStateRole:
            return self._setData(index, value)
        # else
        return super().setData(index, value, role)

    def _setData(self,  # pylint: disable=invalid-name
                 index: QtCore.QModelIndex, value: int) -> bool:
        'Set checkbox status data and update ancestors/descendants'
        if self._data(index) == value:
            return True

        self._set_check_state(index, value)

        if value == QtCore.Qt.Checked:
            self._partially_check_ancestors(index)
            self._uncheck_descendants(index)
            if self.isDir(index):
                self.newDirSelected.emit(self.filePath(index))
        elif value == QtCore.Qt.Unchecked:
            self._uncheck_exclusive_ancestors(index)

        self.calculate_selection_size()
        self.dataChanged.emit(index, index, [])
        return True

    def _set_check_state(self, index: QtCore.QModelIndex, value: int) -> None:
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

    def _partially_check_ancestors(self, index: QtCore.QModelIndex) -> None:
        'Mark all ancestors of index as checked'
        parent = index.parent()
        while self.filePath(parent) != self.rootPath():
            self._set_check_state(parent, QtCore.Qt.PartiallyChecked)
            parent = parent.parent()

    def _uncheck_descendants(self, index: QtCore.QModelIndex) -> None:
        'Mark all descendants of index as unchecked'
        queue = [index.child(i, index.column())
                 for i in range(self.rowCount(index))]
        while queue:
            item = queue.pop()
            self._set_check_state(item, QtCore.Qt.Unchecked)
            queue.extend(item.child(i, index.column())
                         for i in range(self.rowCount(item)))

    def _uncheck_exclusive_ancestors(self, index: QtCore.QModelIndex) -> None:
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

    def calculate_selection_size(self) -> None:
        '''Sum size of all selected items and emit signal

        Emit recalculatingsize if directory is selected that is not cached.
        '''
        if not self.track_selection_size:
            return

        size = 0
        for index in self.selected:
            index = QtCore.QModelIndex(index)
            if self.isDir(index):
                path = self.filePath(index)
                if path in self.dir_size_cache:
                    size += self.dir_size_cache[path]
                else:
                    # Waiting for directory size to be calculated
                    self.recalculatingSize.emit()
                    return
            else:
                size += self.size(index)

        self.newSelectionSize.emit(size)

    @Slot(str, int)
    def _update_dir_size_cache(self, path: str, size: int) -> None:
        'Update cache entry for path'
        self.dir_size_cache[path] = size
        self.calculate_selection_size()


class DirFetcherNode(dict):
    'Container used by DirSizefetcher to cache item size in directory tree'
    size = 0
    walked = False


class DirSizeFetcher(QtCore.QObject):
    'Class to track size of file system selection'
    resultReady = Signal(str, int)

    def __init__(self, model: CheckableFileSystemModel) -> None:
        super().__init__()
        self.dir_tree = DirFetcherNode()

        self.root_path = Path(model.rootPath())
        model.rootPathChanged.connect(self.update_root_path)

    def update_root_path(self, new_path: str) -> None:
        'Change the root path'
        self.root_path = Path(new_path)
        # Invalidate the cache
        self.dir_tree = DirFetcherNode()

    def _track_item_size(self, top_path: Path, path: Path, size: int) -> None:
        'Add size to all the parents of path up to top_path'
        mid_path = path.parent
        while mid_path != top_path.parent:
            pointer = self._get_pointer(mid_path)
            pointer.size += size
            mid_path = mid_path.parent

    def _get_pointer(self, path: Path) -> DirFetcherNode:
        'Get pointer in nested self.dir_tree for path'
        rel_path = path.relative_to(self.root_path)

        pointer = self.dir_tree
        for part in rel_path.parts:
            if part not in pointer:
                pointer[part] = DirFetcherNode()
            pointer = pointer[part]

        return pointer

    @Slot(str)
    def fetch_size(self, path: str) -> None:
        'Determine the size of directory path and emit resultReady signal'
        pointer = self._get_pointer(Path(path))
        if pointer.walked:
            self.resultReady.emit(path, pointer.size)
            return

        paths = [path]
        while paths:
            ipath = Path(paths.pop())
            with os.scandir(ipath) as path_iter:
                for subpath in path_iter:
                    if subpath.is_dir():
                        pointer = self._get_pointer(ipath / subpath)
                        if pointer.walked:
                            self._track_item_size(Path(path), ipath / subpath,
                                                  pointer.size)
                        else:
                            paths.append(subpath)
                    else:
                        self._track_item_size(Path(path), ipath / subpath,
                                              subpath.stat().st_size)

            if ipath.is_dir():
                pointer = self._get_pointer(ipath)
                pointer.walked = True

        pointer = self._get_pointer(Path(path))
        self.resultReady.emit(path, pointer.size)


class UIDialog(QtWidgets.QDialog):
    'Dialog window illustrating use of Checkablefilesystemmodel class'
    def __init__(self, root_path: str, selection: t.List[str] = None,
                 parent: QtCore.QObject = None) -> None:
        QtWidgets.QDialog.__init__(self, parent)

        self.model = CheckableFileSystemModel(self,
                                              preselection=selection)
        self.model.setRootPath(os.path.abspath(root_path))
        self.model.dataChanged.connect(self.update_view)

        self.tree = QtWidgets.QTreeView()
        self.tree.setModel(self.model)
        self.tree.setSortingEnabled(True)
        self.tree.setRootIndex(self.model.index(os.path.abspath(root_path)))

        self.button = QtWidgets.QPushButton("OK")
        self.button.clicked.connect(self.print_selection_and_close)

        self.cancel_button = QtWidgets.QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.close)

        b_layout = QtWidgets.QHBoxLayout(parent)
        b_layout.addWidget(self.cancel_button)
        b_layout.addWidget(self.button)
        button_box = QtWidgets.QGroupBox()
        button_box.setLayout(b_layout)

        self.size_box = QtWidgets.QLabel()
        self.size_box.setAlignment(QtCore.Qt.AlignHCenter)
        self.size_box.setText('Selection size: 0 bytes')
        self.selection_size = 0
        self.model.recalculatingSize.connect(self.indicate_calculating)
        self.model.newSelectionSize.connect(self.update_size)

        layout = QtWidgets.QVBoxLayout(parent)
        layout.addWidget(self.tree)
        layout.addWidget(button_box)
        layout.addWidget(self.size_box)
        self.setLayout(layout)

        self.setObjectName("Dialog")
        self.resize(600, 500)
        self.setWindowTitle('Select files')
        self.tree.resize(400, 480)
        self.tree.setColumnWidth(0, 200)

        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+Q"), self, self.close)
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+W"), self, self.close)
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+Return"), self,
                            self.print_selection_and_close)

    @Slot()
    def indicate_calculating(self) -> None:
        'Indicate that selection size is being recalculated'
        locale = QtCore.QLocale()
        human_size = locale.formattedDataSize(self.selection_size,
                                              format=locale.DataSizeSIFormat)
        fmt = 'Selection size: {}...(Calculating)'
        self.size_box.setText(fmt.format(human_size))
        self.size_box.repaint()

    @Slot(int)
    def update_size(self, size: int) -> None:
        'Update label showing selection size'
        self.selection_size = size

        locale = QtCore.QLocale()
        human_size = locale.formattedDataSize(size,
                                              format=locale.DataSizeSIFormat)
        msg = 'Selection size: {}'.format(human_size)
        self.size_box.setText(msg)
        self.size_box.repaint()

    @Slot()
    def update_view(self) -> None:
        'Refresh UI'
        self.tree.viewport().update()

    @Slot()
    def print_selection_and_close(self) -> None:
        'Print newline delimited paths of selected items and close dialog'
        for item in self.model.selected:
            path = self.model.filePath(QtCore.QModelIndex(item))
            print(Path(path).relative_to(self.model.rootPath()))
        self.close()


def parse_options(args_in=None):
    'Parse command line arguments'
    import argparse
    parser = argparse.ArgumentParser(
        description=('Select files and directories below path to be '
                     'output as a list'))
    parser.add_argument('--path', '-p', help='Root path',
                        default='.')
    parser.add_argument('--selection', '-s', type=str, default='',
                        help='File with paths to select on startup')
    args = parser.parse_args(args_in)

    if args.selection == '-':  # pragma: no cover
        selection = sys.stdin.read().splitlines()
    elif args.selection:
        with open(args.selection, 'r') as file_:
            selection = file_.read().splitlines()
    else:
        selection = None

    return args.path, selection


def main_dialog(args_in=None):
    'Main function'
    path, selection = parse_options(args_in)
    dialog = UIDialog(root_path=path,
                      selection=selection)
    dialog.show()
    return dialog


def main():
    'Main function when run as a sript'
    app = QtWidgets.QApplication([])
    # Need to store dialog in variable the dialog widget gets garbage collected
    dialog_handle = main_dialog()
    sys.exit(app.exec_())


if __name__ == "__main__":  # pragma: no cover
    main()
