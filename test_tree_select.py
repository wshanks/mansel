'Test tree_select module'
import os
from pathlib import Path
import sys
import tempfile

import pytest
from PyQt5 import QtCore, QtWidgets, QtGui


sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import tree_select  # NOQA


DIRS = ('d0', 'd1/d0', 'd1/d1')
FILES = ('f0', 'd0/f0', 'd1/d0/f0', 'd1/d0/f1')
FILESIZE = 10000


@pytest.fixture
def tmp_root_dir():
    'Temporary file hierarchy for CheckableFileSystemModel'
    base = Path(tempfile.TemporaryDirectory().name)
    for dir_ in DIRS:
        (base / dir_).mkdir(parents=True)
    for file_ in FILES:
        with open(base / file_, 'wb') as fhandle:
            fhandle.seek(FILESIZE - 1)
            fhandle.write(b'\0')

    yield base


def test_dirtree():
    'Test DirTree class'
    path_strs = ('a', 'b/c', 'b/d')
    tree = tree_select.DirTree(path_strs)

    paths = [Path(p) for p in path_strs]

    assert tree.check(Path('b')) == 'parent'
    for path in paths:
        assert tree.check(path) == 'leaf'

    for path in paths:
        tree.remove(path)
        assert tree.check(path) == 'unselected'

    for path in paths:
        tree.insert(path)
        assert tree.check(path)

    with pytest.raises(tree_select.PathConflict):
        tree.insert(Path('b/c/d'))


def test_model_qtmodeltester(qtmodeltester):
    'Basic checks on CheckableFileSystemModel'
    model = tree_select.CheckableFileSystemModel(preselection=DIRS[:-1],
                                                 track_selection_size=False)
    qtmodeltester.check(model)


def test_preselection(tmp_root_dir, qtbot):
    dialog = QtWidgets.QDialog()
    qtbot.addWidget(dialog)

    preselection = DIRS[:-1]
    model = tree_select.CheckableFileSystemModel(parent=dialog,
                                                 preselection=preselection,
                                                 track_selection_size=False)

    assert all(model.preselection.check(Path(p)) for p in preselection)

    # Wait for preseleciton to be processed
    with qtbot.waitSignal(model.preselectionProcessed, timeout=None):
        model.setRootPath(str(tmp_root_dir))

    assert not model.preselection.root
    # Absolute paths
    selected_paths = [model.filePath(QtCore.QModelIndex(i))
                      for i in model.selected]
    # Relative paths as strings
    selected_paths = [str(Path(p).relative_to(model.rootPath()))
                      for p in selected_paths]
    assert set(selected_paths) == set(preselection)


def set_path(model, path, state):
    index = model.index(str(path))
    model.setData(index, state, QtCore.Qt.CheckStateRole)


def test_selection(tmp_root_dir, qtbot):
    dialog = QtWidgets.QDialog()
    qtbot.addWidget(dialog)

    model = tree_select.CheckableFileSystemModel(parent=dialog,
                                                 track_selection_size=False)
    model.setRootPath(str(tmp_root_dir))
    # Select files
    for file_ in FILES:
        set_path(model, tmp_root_dir / file_, QtCore.Qt.Checked)
    for file_ in FILES:
        index = model.index(str(tmp_root_dir / file_))
        assert model.data(index, QtCore.Qt.CheckStateRole) == QtCore.Qt.Checked
    assert len(model.selected) == len(FILES)

    # Unselect files
    for file_ in FILES:
        set_path(model, tmp_root_dir / file_, QtCore.Qt.Unchecked)
    for file_ in FILES:
        index = model.index(str(tmp_root_dir / file_))
        assert (model.data(index, QtCore.Qt.CheckStateRole) ==
                QtCore.Qt.Unchecked)
    assert not model.selected

    # Test selecting something twice
    for _ in range(2):
        set_path(model, tmp_root_dir / FILES[0], QtCore.Qt.Checked)
    index = model.index(str(tmp_root_dir / FILES[0]))
    assert model.data(index, QtCore.Qt.CheckStateRole) == QtCore.Qt.Checked


def test_partial_selection(tmp_root_dir, qtbot):
    dialog = QtWidgets.QDialog()
    qtbot.addWidget(dialog)

    model = tree_select.CheckableFileSystemModel(parent=dialog,
                                                 track_selection_size=False)
    model.setRootPath(str(tmp_root_dir))

    deep_file = Path(max(FILES, key=lambda x: len(Path(x).parts)))
    assert len(deep_file.parts) >= 3
    paths = [Path('.').joinpath(*deep_file.parts[:depth])
             for depth, _ in enumerate(deep_file.parts, 1)]
    # Check each path part and make sure all parents/children are
    # partially checked
    for depth, part in enumerate(paths):
        set_path(model, str(tmp_root_dir / part), QtCore.Qt.Checked)
        for depth_, part_ in enumerate(paths):
            index = model.index(str(tmp_root_dir / part_))
            if depth == depth_:
                assert (model.data(index, QtCore.Qt.CheckStateRole) ==
                        QtCore.Qt.Checked)
            else:
                assert (model.data(index, QtCore.Qt.CheckStateRole) ==
                        QtCore.Qt.PartiallyChecked)

    # Check and uncheck each path part and make sure all
    # parents/children are unchecked
    for depth, part in enumerate(paths):
        set_path(model, str(tmp_root_dir / part), QtCore.Qt.Checked)
        set_path(model, str(tmp_root_dir / part), QtCore.Qt.Unchecked)
        for depth_, part_ in enumerate(paths):
            index = model.index(str(tmp_root_dir / part_))
            assert (model.data(index, QtCore.Qt.CheckStateRole) ==
                    QtCore.Qt.Unchecked)


def test_main_dialog(tmp_root_dir, qtbot):
    'Test main app does not crash'
    dialog = tree_select.main_dialog(args_in=['-p', str(tmp_root_dir)])
    qtbot.addWidget(dialog)
    with qtbot.waitSignal(dialog.model.tracker_thread.finished, timeout=None):
        dialog.close()
