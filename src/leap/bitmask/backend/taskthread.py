# Copyright 2013 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
import logging
import threading

__version__ = '1.4'


logger = logging.getLogger(__name__)


class TaskInProcessException(BaseException):
    pass


class TaskThread(threading.Thread):
    """
    A thread object that repeats a task.

    Usage example::

        from taskthread import TaskThread

        import time

        def my_task(*args, **kwargs):
            print args, kwargs

        task_thread = TaskThread(my_task)
        task_thread.start()
        for i in xrange(10):
            task_thread.run_task()
            task_thread.join_task()
        task_thread.join()

    .. note:: If :py:meth:`~TaskThread.run_task` is
        invoked while run_task is in progress,
        :py:class:`~.TaskInProcessException` will
        be raised.

    :param task:
        A ``function``. This param is the task to execute when
         run_task is called.
    :param event:
        A ``threading.Event``. This event will be set when run_task
         is called. The default value is a new event, but may be
         specified for testing purposes.
    """

    daemon = True
    '''
    Threads marked as daemon will be terminated.
    '''
    def __init__(self, task, event=threading.Event(),
                 *args, **kwargs):
        super(TaskThread, self).__init__()
        self.task = task
        self.task_event = event
        self.running = True
        self.running_lock = threading.Lock()
        self.in_task = False
        self.task_complete = threading.Event()
        self.args = args
        self.kwargs = kwargs

    def run(self):
        """
        Called by threading.Thread, this runs in the new thread.
        """
        while True:
            self.task_event.wait()
            if not self.running:
                logger.debug("TaskThread exiting")
                return
            logger.debug("TaskThread starting task")
            with self.running_lock:
                self.task_event.clear()
            self.task_complete.clear()
            self.task(*self.args, **self.kwargs)
            with self.running_lock:
                self.in_task = False
            self.task_complete.set()

    def run_task(self, *args, **kwargs):
        """
        Run an instance of the task.

        :param args:
            The arguments to pass to the task.

        :param kwargs:
            The keyword arguments to pass to the task.
        """
        # Don't allow this call if the thread is currently
        # in a task.
        with self.running_lock:
            if self.in_task:
                raise TaskInProcessException()
            self.in_task = True
        logger.debug("Waking up the thread")
        self.args = args
        self.kwargs = kwargs
        # Wake up the thread to do it's thing
        self.task_event.set()

    def join_task(self, time_out):
        """
        Wait for the currently running task to complete.

        :param time_out:
            An ``int``. The amount of time to wait for the
            task to finish.
        """
        with self.running_lock:
            if not self.in_task:
                return

        success = self.task_complete.wait(time_out)
        if success:
            self.task_complete.clear()
        return success

    def join(self, timeout=None):
        """
        Wait for the task to finish
        """
        self.running = False
        self.task_event.set()
        super(TaskThread, self).join(timeout=timeout)


class TimerTask(object):
    """
    An object that executes a commit function at a given interval.
    This class is driven by a TaskThread. A new TaskThread will be
    created the first time :py:meth:`.~start` is called. All
    subsequent calls to start will reuse the same thread.

    Usage example::

        from taskthread import TimerTask
        import time

        count = 0
        def get_count():
            return count
        def execute():
            print "Count: %d" % count

        task = TimerTask(execute,
                         timeout=10,
                         count_fcn=get_count,
                         threshold=1)

        task.start()

        for i in xrange(100000):
            count += 1
            time.sleep(1)
        task.stop()
        count = 0
        task.start()
        for i in xrange(100000):
            count += 1
            time.sleep(1)
        task.shutdown()

    :param execute_fcn:
        A `function`. This function will be executed on each time interval.

    :param delay:
        An `int`. The delay in **seconds** invocations of
        `execute_fcn`. Default: `10`.

    :param count_fcn:
        A `function`. This function returns a current count. If the count
        has not changed more the `threshold` since the last invocation of
        `execute_fcn`, `execute_fcn` will not be called again. If not
        specified, `execute_fcn` will be called each time the timer fires.
        **Optional**. If count_fcn is specified, ``threshold`` is required.

    :param threshold:
        An `int`. Specifies the minimum delta in `count_fcn` that must be
        met for `execute_fcn` to be invoked. **Optional**. Must be
        specified in conjunction with `count_fcn`.

    """
    def __init__(self, execute_fcn, delay=10, count_fcn=None, threshold=None):
        self.running = True
        self.execute_fcn = execute_fcn
        self.last_count = 0
        self.event = threading.Event()
        self.delay = delay
        self.thread = None
        self.running_lock = threading.RLock()
        if bool(threshold) != bool(count_fcn):
            raise ValueError("Must specify threshold "
                             "and count_fcn, or neither")

        self.count_fcn = count_fcn
        self.threshold = threshold

    def start(self):
        """
        Start the task. This starts a :py:class:`.~TaskThread`, and starts
        running run_threshold_timer on the thread.

        """
        if not self.thread:
            logger.debug('Starting up the taskthread')
            self.thread = TaskThread(self._run_threshold_timer)
            self.thread.start()

        if self.threshold:
            self.last_count = 0

        logger.debug('Running the task')
        self.running = True
        self.thread.run_task()

    def stop(self):
        """
        Stop the task, leaving the :py:class:`.~TaskThread` running
        so start can be called again.

        """
        logger.debug('Stopping the task')
        wait = False
        with self.running_lock:
            if self.running:
                wait = True
                self.running = False
        if wait:
            self.event.set()
            self.thread.join_task(2)

    def shutdown(self):
        """
        Close down the task thread and stop the task if it is running.

        """
        logger.debug('Shutting down the task')
        self.stop()
        self.thread.join(2)

    def _exec_if_threshold_met(self):
        new_count = self.count_fcn()
        logger.debug('new_count: %d' % new_count)
        if new_count >= self.last_count + self.threshold:
            self.execute_fcn()
            self.last_count = new_count

    def _exec(self):
        if self.count_fcn:
            self._exec_if_threshold_met()
        else:
            self.execute_fcn()

    def _wait(self):
        self.event.wait(timeout=self.delay)
        self.event.clear()
        logger.debug('Task woken up')

    def _exit_loop(self):
        """
        If self.running is false, it means the task should shut down.
        """
        exit_loop = False
        with self.running_lock:
            if not self.running:
                exit_loop = True
                logger.debug('Task shutting down')
        return exit_loop

    def _run_threshold_timer(self):
        """
        Main loop of the timer task

        """
        logger.debug('In Task')
        while True:
            self._wait()
            if self._exit_loop():
                return
            self._exec()
