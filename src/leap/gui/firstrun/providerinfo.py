"""
Provider Info Page, used in First run Wizard
"""

from PyQt4 import QtCore
from PyQt4 import QtGui

from leap.gui.progress import ValidationPage

from leap.gui.constants import APP_LOGO


class ProviderInfoPage(ValidationPage):
    def __init__(self, parent=None):
        super(ProviderInfoPage, self).__init__(parent)

        self.setTitle("Provider Info")
        #self.setSubTitle("Available information about chosen provider.")

        self.setPixmap(
            QtGui.QWizard.LogoPixmap,
            QtGui.QPixmap(APP_LOGO))

    def create_info_panel(self):
        displayName = QtGui.QLabel("")
        description = QtGui.QLabel("")
        enrollment_policy = QtGui.QLabel("")
        # XXX set stylesheet...
        # prettify a little bit.
        # bigger fonts and so on...
        self.displayName = displayName
        self.description = description
        self.enrollment_policy = enrollment_policy

        # this trick allows us to reparent
        QtCore.QObjectCleanupHandler().add(self.layout)
        layout = QtGui.QGridLayout()

        layout.addWidget(displayName, 0, 1)
        layout.addWidget(description, 1, 1)
        layout.addWidget(enrollment_policy, 2, 1)

        self.setLayout(layout)
        self.update()

    def show_provider_info(self):

        # XXX get multilingual objects
        # directly from the config object

        lang = "en"
        pconfig = self.wizard().providerconfig

        dn = pconfig.get('display_name')
        display_name = dn[lang] if dn else ''
        self.displayName.setText(
            "<b>%s</b>" % display_name)

        desc = pconfig.get('description')
        description_text = desc[lang] if desc else ''
        self.description.setText(
            "<i>%s</i>" % description_text)

        enroll = pconfig.get('enrollment_policy')
        if enroll:
            self.enrollment_policy.setText(
                'enrollment policy: %s' % enroll)

    def _do_checks(self, update_signal=None):
        """
        executes actual checks in a separate thread
        """
        import time
        update_signal.emit("head_sentinel", 0)
        time.sleep(0.5)
        update_signal.emit("something", 10)
        time.sleep(0.5)
        update_signal.emit("done", 90)
        time.sleep(1)
        update_signal.emit("end_sentinel", 100)
        time.sleep(1)

    def _do_validation(self):
        """
        called after _do_checks has finished
        (connected to checker thread finished signal)
        """
        print 'validation...'
        self.progress.hide()
        self.stepsTableWidget.hide()
        self.create_info_panel()
        self.show_provider_info()

    def nextId(self):
        wizard = self.wizard()
        next_ = "providersetupvalidation"
        return wizard.get_page_index(next_)
