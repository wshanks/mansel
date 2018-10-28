# mansel

`mansel` is a Python library and command line tool for manually selecting files and directories from a tree view.

## Features

* Graphical user interface with a tree view of the directory structure.
* Support for pre-selection of paths in the directory tree.
* Running total of the size of selected directories and files.
* Running total of selection size calculated in a background thread.

## Installation

`mansel` can be installed with `pip`:

    pip install mansel

The `mansel` package depends on `PySide2` which packages the Qt runtime and Python bindings to it.
Alternatively, the `mansel` command line tool can be installed with

    pip install mansel-pyqt

[mansel-pyqt](https://github.com/willsALMANJ/mansel-pyqt) depends on `PyQt5` and requires that the Qt runtime be installed separately.

Both `mansel` and `mansel-pyqt` depend on the `mansel-lib` package which can be installed directly if you want to use `mansel`'s features in another project without installing the command line tool.

## Usage

`mansel` can be run from the command-line with

    mansel --path PATH --selection SELECTION

where `PATH` is the root path to use for file selection and `SELECTION` is a file containing a newline delimited list of paths relative to `PATH` which should be selected when the file selection window opens. Invoking `mansel` opens a dialog window with the contents of `PATH` shown as an expandable tree view with checkboxes by every file and directory. Individual files and directories can be selected and unselected and directories can be expanded to select individual files on paths below `PATH`.  When `OK` is pressed to exit the window, the list of selected files and directories is printed to `stdout`.

### Usage notes

* If `SELECTION` is `-`, then the selection list is read from `stdin`. 
* A running tally of the current selection size is shown at the bottom of the window. The calculation is performed on a background thread. The size total is followed by "(Calculating)" while the selection size is being re-tallied.
* `Cancel`, `Ctrl+W`, `Ctrl+Q` all close the window without printing to `stdout`.
* `Ctrl+Enter` is equivalent to pressing `OK`.
* `mansel-cli` is a wrapper for `mansel`. Effectively, installing `mansel-cli` instealls `mansel` and `PySide2` (`mansel` does not list `PySide2` as a dependency to allow it to be used with `PyQt5` as well) and sets up a wrapper sript that calls `python -m mansel`.

## API

When using `mansel` in a larger Qt project, there are two main classes for interfaces for working with the manual file selection:

1. `UIDialog(root_path, selection, parent)`: a complete dialog window displaying a tree view of a file system with checkboxes for all entries.

  + `root_path`: top level directory to show in the tree view of the file ssytem.
  + `selection`: list of paths relative to the `root_path` of files that should be selected when the dialog window is first shown.
  + `parent`: parent Qt object for the dialog window.

2. `CheckableFileSystemModel`: a data model of a file system that supports selecting items from a tree view.

## Contributing

`mansel` is distributed under the permissive 0BSD license.
Outside contirubtions are welcome.
Contributions should be licensed under the 0BSD license.
If you want your name added to the contributors list, add it to AUTHORS.md as part of your submission.

While the license does not require acknowledgement, acknowledgement is still appreciated if you use `mansel` in your project.
If you make improvements to `mansel`, please share them if sharing is feasible.

## Related projects

* [treesel](https://github.com/mcchae/treesel) provides a terminal-based tree view of a directory for selecting a file to print to stdout. However, it only allows for a single file to be selected. Before writing `mansel` some effort was spent looking for an existing project that could select and print files but `treesel` was not found. It was found later when doing a search to see if the name `treeselect` was available for a Python package.
* [Urwid](http://urwid.org/) is a Python terminal interface library. One of the example projects in the Urwid documentation is a file browser naemd `browse.py` which allows for multiple selection of files and then prints out the file paths on exit.
* [fzf](https://github.com/junegunn/fzf) is a terminal program that allows for selection of file paths through fuzzy finding of the path strings. There are many similar projects (see `fzf`'s releated projects list). `fzf` does not have a tree view but it does allow selecting and printing multiple file paths to stdout.

## Future directions

`mansel` meets its original design requirements (tree view file selection with the ability to preselect some files and with a running sum of the selected files' sizes). Here are some possible future improvements that could be made:

* Implement a console version. This implementation would likely be based on `treesel` (using the `curses` module) or Urwid's `browse.py`. Alternatively, it could use [Prompt Toolkit](https://github.com/jonathanslenders/python-prompt-toolkit).

* Improve continuous integration:
  - Run tests on new commits
  - Run nightly tests against latest versions of dependencies
  - Add pylint and pycodestyle tests
  - Add UI tests that click on checkboxes and buttons

* Improve packaging:
  - Create PyPI package
  - Create conda package
  - Create other packages (PyInstaller? Linux snap package?)
