# mansel-cli

`mansel-cli` is a command line tool for manually selecting files and directories from a tree view.

## Features

* Graphical user interface with a tree view of the directory structure.
* Support for pre-selection of paths in the directory tree.
* Running total of the size of selected directories and files.
* Running total of selection size calculated in a background thread.

## Installation

`mansel-cli` can be installed with `pip`:

    pip install mansel-cli

This will install [mansel](https://pypi.org/project/mansel/) along with PySide2.

## Usage

`mansel-cli` provides an executable script called `mansel` which should be installed into the environment's path. It can be invoked as

    mansel --path PATH --selection SELECTION

where `PATH` is the root path to use for file selection and `SELECTION` is a file containing a newline delimited list of paths relative to `PATH` which should be selected when the file selection window opens. Invoking `mansel` opens a dialog window with the contents of `PATH` shown as an expandable tree view with checkboxes by every file and directory. Individual files and directories can be selected and unselected and directories can be expanded to select individual files on paths below `PATH`.  When `OK` is pressed to exit the window, the list of selected files and directories is printed to `stdout`.

### Usage notes

* If `SELECTION` is `-`, then the selection list is read from `stdin`. 
* A running tally of the current selection size is shown at the bottom of the window. The calculation is performed on a background thread. The size total is followed by "(Calculating)" while the selection size is being re-tallied.
* `Cancel`, `Ctrl+W`, `Ctrl+Q` all close the window without printing to `stdout`.
* `Ctrl+Enter` is equivalent to pressing `OK`.
* `mansel-cli` is a wrapper for `mansel`. Effectively, installing `mansel-cli` instealls `mansel` and `PySide2` (`mansel` does not list `PySide2` as a dependency to allow it to be used with `PyQt5` as well) and sets up a wrapper sript that calls `python -m mansel`.

## Contributing

`mansel-cli` is distributed under the permissive 0BSD license.
Outside contirubtions are welcome.
Contributions should be licensed under the 0BSD license.
If you want your name added to the contributors list, add it to AUTHORS.md as part of your submission.

While the license does not require acknowledgement, acknowledgement is still appreciated if you use `mansel` in your project.
If you make improvement to `mansel`, please share them if sharing is feasible.
