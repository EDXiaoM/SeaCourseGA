"""Background threads of the desktop application.

Loading the dataset, building the graph and running the genetic algorithm take
from a fraction of a second to tens of seconds. They are executed in a
:class:`TaskThread` so that the window stays responsive; results and progress
reach the GUI through Qt signals, which Qt delivers in the GUI thread.
"""
from __future__ import annotations

import traceback
from typing import Any, Callable

from PyQt5.QtCore import QThread, pyqtSignal


class TaskThread(QThread):
    """Runs ``function(thread)`` in a worker thread.

    The function receives the thread object so that it can emit progress
    (``thread.progress.emit(message, fraction)``), report GA generations
    (``thread.generation.emit(generation, best, median)``) and poll
    :meth:`stop_requested`.

    Signals
    -------
    progress(str, float):
        Text and completion fraction 0..1.
    generation(int, float, float):
        Generation number, best and median cost (genetic algorithm only).
    succeeded(object):
        Return value of the function.
    failed(str):
        Error message and traceback.
    """

    progress = pyqtSignal(str, float)
    generation = pyqtSignal(int, float, float)
    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, function: Callable[["TaskThread"], Any], parent=None) -> None:
        super().__init__(parent)
        self._function = function
        self._stop = False

    def request_stop(self) -> None:
        """Ask a long task (the genetic algorithm) to finish early."""
        self._stop = True

    def stop_requested(self) -> bool:
        """True after :meth:`request_stop` was called."""
        return self._stop

    def run(self) -> None:  # executed in the worker thread
        try:
            result = self._function(self)
        except Exception as error:  # reported to the user, never re-raised
            self.failed.emit(f"{error}\n\n{traceback.format_exc()}")
        else:
            self.succeeded.emit(result)
