"""
classes used in progress pages
from first run wizard
"""
try:
    from collections import OrderedDict
except ImportError:
    # We must be in 2.6
    from leap.util.dicts import OrderedDict

import logging

from PyQt4 import QtCore
from PyQt4 import QtGui

from leap.gui.threads import FunThread

from leap.gui import mainwindow_rc

ICON_CHECKMARK = ":/images/Dialog-accept.png"
ICON_FAILED = ":/images/Dialog-error.png"
ICON_WAITING = ":/images/Emblem-question.png"

logger = logging.getLogger(__name__)


# XXX import this from threads
def delay(obj, method_str=None, call_args=None):
    """
    this is a hack to get responsiveness in the ui
    """
    if callable(obj) and not method_str:
        QtCore.QTimer().singleShot(
            50,
            lambda: obj())
        return

    if method_str:
        QtCore.QTimer().singleShot(
            50,
            lambda: QtCore.QMetaObject.invokeMethod(
                obj, method_str))


class ImgWidget(QtGui.QWidget):

    # XXX move to widgets

    def __init__(self, parent=None, img=None):
        super(ImgWidget, self).__init__(parent)
        self.pic = QtGui.QPixmap(img)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.drawPixmap(0, 0, self.pic)


class ProgressStep(object):
    """
    Data model for sequential steps
    to be used in a progress page in
    connection wizard
    """
    NAME = 0
    DONE = 1

    def __init__(self, stepname, done, index=None):
        """
        @param step: the name of  the step
        @type step: str
        @param done: whether is completed or not
        @type done: bool
        """
        self.index = int(index) if index else 0
        self.name = unicode(stepname)
        self.done = bool(done)

    @classmethod
    def columns(self):
        return ('name', 'done')


class ProgressStepContainer(object):
    """
    a container for ProgressSteps objects
    access data in the internal dict
    """

    def __init__(self):
        self.dirty = False
        self.steps = {}

    def step(self, identity):
        return self.step.get(identity)

    def addStep(self, step):
        self.steps[step.index] = step

    def removeStep(self, step):
        del self.steps[step.index]
        del step
        self.dirty = True

    def removeAllSteps(self):
        for item in iter(self):
            self.removeStep(item)

    @property
    def columns(self):
        return ProgressStep.columns()

    def __len__(self):
        return len(self.steps)

    def __iter__(self):
        for step in self.steps.values():
            yield step


class StepsTableWidget(QtGui.QTableWidget):
    """
    initializes a TableWidget
    suitable for our display purposes, like removing
    header info and grid display
    """

    def __init__(self, parent=None):
        super(StepsTableWidget, self).__init__(parent)

        # remove headers and all edit/select behavior
        self.horizontalHeader().hide()
        self.verticalHeader().hide()
        self.setEditTriggers(
            QtGui.QAbstractItemView.NoEditTriggers)
        self.setSelectionMode(
            QtGui.QAbstractItemView.NoSelection)
        width = self.width()
        # WTF? Here init width is 100...
        # but on populating is 456... :(

        # XXX do we need this initial?
        logger.debug('init table. width=%s' % width)
        self.horizontalHeader().resizeSection(0, width * 0.7)

        # this disables the table grid.
        # we should add alignment to the ImgWidget (it's top-left now)
        self.setShowGrid(False)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        #self.setStyleSheet("QTableView{outline: 0;}")

        # XXX change image for done to rc

        # Note about the "done" status painting:
        #
        # XXX currently we are setting the CellWidget
        # for the whole table on a per-row basis
        # (on add_status_line method on ValidationPage).
        # However, a more generic solution might be
        # to implement a custom Delegate that overwrites
        # the paint method (so it paints a checked tickmark if
        # done is True and some other thing if checking or false).
        # What we have now is quick and works because
        # I'm supposing that on first fail we will
        # go back to previous wizard page to signal the failure.
        # A more generic solution could be used for
        # some failing tests if they are not critical.


class WithStepsMixIn(object):

    # worker threads for checks

    def setupStepsProcessingQueue(self):
        self.steps_queue = Queue.Queue()
        self.stepscheck_timer = QtCore.QTimer()
        self.stepscheck_timer.timeout.connect(self.processStepsQueue)
        self.stepscheck_timer.start(100)
        # we need to keep a reference to child threads
        self.threads = []

    def do_checks(self):

        # yo dawg, I heard you like checks
        # so I put a __do_checks in your do_checks
        # for calling others' _do_checks

        def __do_checks(fun=None, queue=None):

            for checkcase in fun():
                checkmsg, checkfun = checkcase

                queue.put(checkmsg)
                if checkfun() is False:
                    queue.put("failed")
                    break

        t = FunThread(fun=partial(
            __do_checks,
            fun=self._do_checks,
            queue=self.steps_queue))
        t.finished.connect(self.on_checks_validation_ready)
        t.begin()
        self.threads.append(t)

    def fail(self, err=None):
        """
        return failed state
        and send error notification as
        a nice side effect
        """
        wizard = self.wizard()
        senderr = lambda err: wizard.set_validation_error(
            self.current_page, err)
        self.set_undone()
        if err:
            senderr(err)
        return False

    @QtCore.pyqtSlot()
    def launch_checks(self):
        self.do_checks()

    # slot
    #@QtCore.pyqtSlot(str, int)
    def onStepStatusChanged(self, status, progress=None):
        if status not in ("head_sentinel", "end_sentinel"):
            self.add_status_line(status)
        if status in ("end_sentinel"):
            self.checks_finished = True
            self.set_checked_icon()
        if progress and hasattr(self, 'progress'):
            self.progress.setValue(progress)
            self.progress.update()

    def processStepsQueue(self):
        """
        consume steps queue
        and pass messages
        to the ui updater functions
        """
        while self.steps_queue.qsize():
            try:
                status = self.steps_queue.get(0)
                if status == "failed":
                    self.set_failed_icon()
                else:
                    self.onStepStatusChanged(*status)
            except Queue.Empty:
                pass

    def setupSteps(self):
        self.steps = ProgressStepContainer()
        # steps table widget
        self.stepsTableWidget = StepsTableWidget(self)
        zeros = (0, 0, 0, 0)
        self.stepsTableWidget.setContentsMargins(*zeros)
        self.errors = OrderedDict()

    def set_error(self, name, error):
        self.errors[name] = error

    def pop_first_error(self):
        return list(reversed(self.errors.items())).pop()

    def clean_errors(self):
        self.errors = OrderedDict()

    def clean_wizard_errors(self, pagename=None):
        if pagename is None:
            pagename = getattr(self, 'prev_page', None)
        if pagename is None:
            return
        logger.debug('cleaning wizard errors for %s' % pagename)
        self.wizard().set_validation_error(pagename, None)

    def populateStepsTable(self):
        # from examples,
        # but I guess it's not needed to re-populate
        # the whole table.
        table = self.stepsTableWidget
        table.setRowCount(len(self.steps))
        columns = self.steps.columns
        table.setColumnCount(len(columns))

        for row, step in enumerate(self.steps):
            item = QtGui.QTableWidgetItem(step.name)
            item.setData(QtCore.Qt.UserRole,
                         long(id(step)))
            table.setItem(row, columns.index('name'), item)
            table.setItem(row, columns.index('done'),
                          QtGui.QTableWidgetItem(step.done))
        self.resizeTable()
        self.update()

    def clearTable(self):
        # ??? -- not sure what's the difference
        #self.stepsTableWidget.clear()
        self.stepsTableWidget.clearContents()

    def resizeTable(self):
        # resize first column to ~80%
        table = self.stepsTableWidget
        FIRST_COLUMN_PERCENT = 0.70
        width = table.width()
        logger.debug('populate table. width=%s' % width)
        table.horizontalHeader().resizeSection(0, width * FIRST_COLUMN_PERCENT)

    def set_item_icon(self, img=ICON_CHECKMARK, current=True):
        """
        mark the last item
        as done
        """
        # setting cell widget.
        # see note on StepsTableWidget about plans to
        # change this for a better solution.
        index = len(self.steps)
        table = self.stepsTableWidget
        _index = index - 1 if current else index - 2
        table.setCellWidget(
            _index,
            ProgressStep.DONE,
            ImgWidget(img=img))
        table.update()

    def set_failed_icon(self):
        self.set_item_icon(img=ICON_FAILED, current=True)

    def set_checking_icon(self):
        self.set_item_icon(img=ICON_WAITING, current=True)

    def set_checked_icon(self, current=True):
        self.set_item_icon(current=current)

    def add_status_line(self, message):
        """
        adds a new status line
        and mark the next-to-last item
        as done
        """
        index = len(self.steps)
        step = ProgressStep(message, False, index=index)
        self.steps.addStep(step)
        self.populateStepsTable()
        self.set_checking_icon()
        self.set_checked_icon(current=False)

    # Sets/unsets done flag
    # for isComplete checks

    def set_done(self):
        self.done = True
        self.completeChanged.emit()

    def set_undone(self):
        self.done = False
        self.completeChanged.emit()

    def is_done(self):
        return self.done

    def go_back(self):
        self.wizard().back()

    def go_next(self):
        self.wizard().next()


"""
We will use one base class for the intermediate pages
and another one for the in-page validations, both sharing the creation
of the tablewidgets.
The logic of this split comes from where I was trying to solve
the ui update using signals, but now that it's working well with
queues I could join them again.
"""

import Queue
from functools import partial


class InlineValidationPage(QtGui.QWizardPage, WithStepsMixIn):

    def __init__(self, parent=None):
        super(InlineValidationPage, self).__init__(parent)
        self.setupStepsProcessingQueue()
        self.done = False

    # slot

    @QtCore.pyqtSlot()
    def showStepsFrame(self):
        self.valFrame.show()
        self.update()

    # progress frame

    def setupValidationFrame(self):
        qframe = QtGui.QFrame
        valFrame = qframe()
        valFrame.setFrameStyle(qframe.NoFrame)
        valframeLayout = QtGui.QVBoxLayout()
        zeros = (0, 0, 0, 0)
        valframeLayout.setContentsMargins(*zeros)

        valframeLayout.addWidget(self.stepsTableWidget)
        valFrame.setLayout(valframeLayout)
        self.valFrame = valFrame


class ValidationPage(QtGui.QWizardPage, WithStepsMixIn):
    """
    class to be used as an intermediate
    between two pages in a wizard.
    shows feedback to the user and goes back if errors,
    goes forward if ok.
    initializePage triggers a one shot timer
    that calls do_checks.
    Derived classes should implement
    _do_checks and
    _do_validation
    """

    # signals
    stepChanged = QtCore.pyqtSignal([str, int])

    def __init__(self, parent=None):
        super(ValidationPage, self).__init__(parent)
        self.setupSteps()
        #self.connect_step_status()

        layout = QtGui.QVBoxLayout()
        self.progress = QtGui.QProgressBar(self)
        layout.addWidget(self.progress)
        layout.addWidget(self.stepsTableWidget)

        self.setLayout(layout)
        self.layout = layout

        self.timer = QtCore.QTimer()
        self.done = False

        self.setupStepsProcessingQueue()

    def isComplete(self):
        return self.is_done()

    ########################

    def show_progress(self):
        self.progress.show()
        self.stepsTableWidget.show()

    def hide_progress(self):
        self.progress.hide()
        self.stepsTableWidget.hide()

    # pagewizard methods.
    # if overriden, child classes should call super.

    def initializePage(self):
        self.clean_errors()
        self.clean_wizard_errors()
        self.steps.removeAllSteps()
        self.clearTable()
        self.resizeTable()
        self.timer.singleShot(0, self.do_checks)
