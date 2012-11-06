"""
Provider Info Page, used in First run Wizard
"""

from PyQt4 import QtGui

from leap.gui.constants import APP_LOGO


class ProviderInfoPage(QtGui.QWizardPage):
    def __init__(self, parent=None):
        super(ProviderInfoPage, self).__init__(parent)

        self.setTitle("Provider Info")
        self.setSubTitle("Available information about chosen provider.")

        self.setPixmap(
            QtGui.QWizard.LogoPixmap,
            QtGui.QPixmap(APP_LOGO))

        displayName = QtGui.QLabel("")
        description = QtGui.QLabel("")
        enrollment_policy = QtGui.QLabel("")
        # XXX set stylesheet...
        # prettify a little bit.
        # bigger fonts and so on...
        self.displayName = displayName
        self.description = description
        self.enrollment_policy = enrollment_policy

        layout = QtGui.QGridLayout()
        layout.addWidget(displayName, 0, 1)
        layout.addWidget(description, 1, 1)
        layout.addWidget(enrollment_policy, 2, 1)

        self.setLayout(layout)

    def initializePage(self):
        # XXX move to show info...

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

    def nextId(self):
        wizard = self.wizard()
        next_ = "providersetupvalidation"
        return wizard.get_page_index(next_)


