"""
Provider Info Page, used in First run Wizard
"""
import logging

from PyQt4 import QtGui

from leap.gui.constants import APP_LOGO
from leap.util.translations import translate

logger = logging.getLogger(__name__)


class ProviderInfoPage(QtGui.QWizardPage):

    def __init__(self, parent=None):
        super(ProviderInfoPage, self).__init__(parent)

        self.setTitle(self.tr("Provider Info"))
        self.setSubTitle(self.tr(
            "This is what provider says."))

        self.setPixmap(
            QtGui.QWizard.LogoPixmap,
            QtGui.QPixmap(APP_LOGO))

        self.create_info_panel()

    def create_info_panel(self):
        # Use stacked widget instead
        # of reparenting the layout.

        infoWidget = QtGui.QStackedWidget()

        info = QtGui.QWidget()
        layout = QtGui.QVBoxLayout()

        displayName = QtGui.QLabel("")
        description = QtGui.QLabel("")
        enrollment_policy = QtGui.QLabel("")

        # XXX set stylesheet...
        # prettify a little bit.
        # bigger fonts and so on...

        # We could use a QFrame here

        layout.addWidget(displayName)
        layout.addWidget(description)
        layout.addWidget(enrollment_policy)
        layout.addStretch(1)

        info.setLayout(layout)
        infoWidget.addWidget(info)

        pageLayout = QtGui.QVBoxLayout()
        pageLayout.addWidget(infoWidget)
        self.setLayout(pageLayout)

        # add refs to self to allow for
        # updates.
        # Watch out! Have to get rid of these references!
        # this should be better handled with signals !!
        self.displayName = displayName
        self.description = description
        self.description.setWordWrap(True)
        self.enrollment_policy = enrollment_policy

    def show_provider_info(self):

        # XXX get multilingual objects
        # directly from the config object

        lang = "en"
        pconfig = self.wizard().providerconfig

        dn = pconfig.get('name')
        display_name = dn[lang] if dn else ''
        domain_name = self.field('provider_domain')

        self.displayName.setText(
            "<b>%s</b> https://%s" % (display_name, domain_name))

        desc = pconfig.get('description')

        #description_text = desc[lang] if desc else ''
        description_text = translate(desc) if desc else ''

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

    def initializePage(self):
        self.show_provider_info()
