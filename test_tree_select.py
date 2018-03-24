'Test tree_select module'
# TODO: Could add UI level tests that click checkboxes, buttons, etc.
from collections import Counter
import os
from pathlib import Path
import sys
import tempfile

import pytest
from PyQt5 import QtCore, QtWidgets


sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import tree_select  # NOQA


FILES = ('f0', 'd0/f1', 'd1/d2/d3/f2', 'd1/d2/d3/f3', 'd1/d4/d5/f4')
FILESIZE = 10000
DIRS = tuple(set([str(Path(p).parent)
                  for p in FILES
                  if len(Path(p).parts) > 1]))


def set_path(model, path, state):
    index = model.index(str(path))
    model.setData(index, state, QtCore.Qt.CheckStateRole)


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
    selection = tempfile.NamedTemporaryFile('w')
    selection.write(FILES[0])
    selection.seek(0)
    dialog = tree_select.main_dialog(args_in=['-p', str(tmp_root_dir),
                                              '-s', selection.name])
    qtbot.addWidget(dialog)
    with qtbot.waitSignal(dialog.model.preselectionProcessed, timeout=None):
        dialog.model.setRootPath(str(tmp_root_dir))
    # Absolute paths
    selected_paths = [dialog.model.filePath(QtCore.QModelIndex(i))
                      for i in dialog.model.selected]
    # Relative paths as strings
    selected_paths = [str(Path(p).relative_to(dialog.model.rootPath()))
                      for p in selected_paths]
    assert set(selected_paths) == set([FILES[0]])

    with qtbot.waitSignal(dialog.model.tracker_thread.finished, timeout=None):
        # Run through main methods to make sure they don't crash
        # (i.e. this doesn't validate that they do the right thing!)
        dialog.indicate_calculating()
        dialog.update_size(0)
        dialog.update_view()
        dialog.print_selection_and_close()


def test_model_no_parent(tmp_root_dir, qtbot):
    'Test no error for model without parent if shut down cleanly'
    model = tree_select.CheckableFileSystemModel()
    model.setRootPath(str(tmp_root_dir))

    with qtbot.waitSignal(model.tracker_thread.finished, timeout=None):
        model.tracker_thread.quit()


def test_track_size(tmp_root_dir, qtbot):
    'Test no error for model without parent if shut down cleanly'
    model = tree_select.CheckableFileSystemModel()
    model.setRootPath(str(tmp_root_dir))

    for file_ in FILES:
        set_path(model, tmp_root_dir / file_, QtCore.Qt.Checked)
    with qtbot.waitSignal(model.newSelectionSize, timeout=None) as blocker:
        model.calculate_selection_size()
    files_size = blocker.args[0]
    assert files_size == FILESIZE * len(FILES)

    for path in tmp_root_dir.iterdir():
            set_path(model, path, QtCore.Qt.Checked)
    with qtbot.waitSignal(model.newSelectionSize, timeout=None) as blocker:
        model.calculate_selection_size()
    total_size = blocker.args[0]
    assert total_size == files_size

    with qtbot.waitSignal(model.tracker_thread.finished, timeout=None):
        model.tracker_thread.quit()


def test_dir_size_fetcher(tmp_root_dir, qtbot):
    # Find top level directory with most files below it
    dirs = Counter(Path(f).parts[0] for f in FILES)
    dir_, count = dirs.most_common(1)[0]

    # Find an intermediate dir to select first, to test cached lookup
    # during higher level lookup
    for path in FILES:
        path = Path(path)
        if path.parts[0] == dir_ and len(path.parts) >= 3:
            inter_dir = path.parent
            break
    inter_dir_count = 0
    for path in FILES:
        try:
            Path(path).relative_to(inter_dir)
        except ValueError:
            continue
        inter_dir_count += 1

    model = tree_select.CheckableFileSystemModel(track_selection_size=False)
    model.setRootPath(str(tmp_root_dir))
    qtbot.addWidget(model)

    set_path(model, tmp_root_dir / dir_, QtCore.Qt.Checked)

    fetcher = tree_select.DirSizeFetcher(model)
    qtbot.addWidget(fetcher)
    # Test intermediate dir
    # import pudb; pudb.set_trace()
    with qtbot.waitSignal(fetcher.resultReady, timeout=None) as blocker:
        fetcher.fetch_size(str(tmp_root_dir / inter_dir))
    assert blocker.args[1] == inter_dir_count * FILESIZE

    # Test top level dir
    # Test twice to test initial lookup and cached lookup
    for _ in range(2):
        with qtbot.waitSignal(fetcher.resultReady, timeout=None) as blocker:
            fetcher.fetch_size(str(tmp_root_dir / dir_))
        assert blocker.args[1] == count * FILESIZE


def test_output(tmp_root_dir, qtbot, capsys):
    'Test dialog prints out the right selection at end'
    dialog = tree_select.main_dialog(args_in=['-p', str(tmp_root_dir)])
    qtbot.addWidget(dialog)
    with qtbot.waitSignal(dialog.model.tracker_thread.finished, timeout=None):
        for file_ in FILES:
            set_path(dialog.model, tmp_root_dir / file_, QtCore.Qt.Checked)
        dialog.print_selection_and_close()

    captured = capsys.readouterr()
    assert set(captured.out.splitlines()) == set(FILES)
