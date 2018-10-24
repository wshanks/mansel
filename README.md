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

However, `mansel` needs Python Qt bindings in order to be useful. It is compatible with both PyQt5 and PySide2 so either

    pip install mansel PySide2

or

    pip install mansel PyQt5

will do. A Python Qt binding library is the only explicit dependency, though obviously that will have its own dependency on Qt itself.

## Usage

`mansel` can be run from the command-line with

    python -m mansel --path PATH --selection SELECTION

In this case, it behaves similarly to the `mansel` command provided by the [mansel-cli](https://pypi.org/project/mansel-cli/) distribution.

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
