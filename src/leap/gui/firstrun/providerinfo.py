"""
Provider Info Page, used in First run Wizard
"""
import logging

from PyQt4 import QtCore
from PyQt4 import QtGui

import requests

from leap.base import exceptions as baseexceptions
#from leap.crypto import certs
from leap.eip import exceptions as eipexceptions

from leap.gui.progress import ValidationPage
from leap.util.web import get_https_domain_and_port

from leap.gui.constants import APP_LOGO, pause_for_user

logger = logging.getLogger(__name__)


class ProviderInfoPage(ValidationPage):
    def __init__(self, parent=None):
        super(ProviderInfoPage, self).__init__(parent)

        self.setTitle("Provider Info")
        #self.setSubTitle("Available information about chosen provider.")

        self.setPixmap(
            QtGui.QWizard.LogoPixmap,
            QtGui.QPixmap(APP_LOGO))

        self.prev_page = "providerselection"
        self.infoWidget = None
        #self.current_page = "providerinfo"

    def create_info_panel(self):
        # Use stacked widget instead
        # of reparenting the layout.

        self.infoWidget = QtGui.QStackedWidget()

        info = QtGui.QWidget()
        layout = QtGui.QVBoxLayout()

        displayName = QtGui.QLabel("")
        description = QtGui.QLabel("")
        enrollment_policy = QtGui.QLabel("")
        # XXX set stylesheet...
        # prettify a little bit.
        # bigger fonts and so on...

        layout.addWidget(displayName)
        layout.addWidget(description)
        layout.addWidget(enrollment_policy)
        layout.addStretch(1)

        info.setLayout(layout)
        self.infoWidget.addWidget(info)

        self.layout.addWidget(self.infoWidget)

        # add refs to self to allow for
        # updates.
        # Watch out! Have to get rid of these references!
        # this should be better handled with signals !!
        self.displayName = displayName
        self.description = description
        self.enrollment_policy = enrollment_policy

    def show_provider_info(self):

        # XXX get multilingual objects
        # directly from the config object

        lang = "en"
        pconfig = self.wizard().providerconfig

        dn = pconfig.get('display_name')
        display_name = dn[lang] if dn else ''
        domain_name = self.field('provider_domain')

        self.displayName.setText(
            "<b>%s</b> https://%s" % (display_name, domain_name))

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
        finish = lambda: update_signal.emit("end_sentinel", 100)

        def pause_and_finish():
            # only for local debug
            finish()
            pause_for_user()

        wizard = self.wizard()
        prevpage = "providerselection"

        full_domain = self.field('provider_domain')

        # we check if we have a port in the domain string.
        domain, port = get_https_domain_and_port(full_domain)
        _domain = u"%s:%s" % (domain, port) if port != 443 else unicode(domain)

        netchecker = wizard.netchecker()
        providercertchecker = wizard.providercertchecker()
        eipconfigchecker = wizard.eipconfigchecker(domain=_domain)

        update_signal.emit("head_sentinel", 0)
        pause_for_user()

        ########################
        # 1) try name resolution
        ########################
        update_signal.emit("Checking that server is reachable", 20)
        logger.debug('checking name resolution')
        try:
            netchecker.check_name_resolution(
                domain)

        except baseexceptions.LeapException as exc:
            logger.error(exc.message)
            wizard.set_validation_error(
                prevpage, exc.usermessage)
            pause_and_finish()
            return False

        #########################
        # 2) try https connection
        #########################
        update_signal.emit("Checking secure connection to provider", 40)
        logger.debug('checking https connection')
        try:
            providercertchecker.is_https_working(
                "https://%s" % _domain,
                verify=True)

        except eipexceptions.HttpsBadCertError as exc:
            logger.debug('exception')
            # XXX skipping for now...
            ##############################################
            # We had this validation logic
            # in the provider selection page before
            ##############################################
            #if self.trustProviderCertCheckBox.isChecked():
                #pass
            #else:
            wizard.set_validation_error(
                prevpage, exc.usermessage)
            #fingerprint = certs.get_cert_fingerprint(
                #domain=domain, sep=" ")

            # it's ok if we've trusted this fgprt before
            #trustedcrts = wizard.trusted_certs
            #if trustedcrts and fingerprint.replace(' ', '') in trustedcrts:
                #pass
            #else:
                # let your user face panick :P
                #self.add_cert_info(fingerprint)
                #self.did_cert_check = True
                #self.completeChanged.emit()
                #return False
            finish()
            return False

        except baseexceptions.LeapException as exc:
            wizard.set_validation_error(
                prevpage, exc.usermessage)
            finish()
            return False

        ##################################
        # 3) try download provider info...
        ##################################

        update_signal.emit("Downloading provider info", 70)
        try:
            # XXX we already set _domain in the initialization
            # so it should not be needed here.
            eipconfigchecker.fetch_definition(domain=_domain)
            wizard.set_providerconfig(
                eipconfigchecker.defaultprovider.config)
        except requests.exceptions.SSLError:
            # XXX we should have catched this before.
            # but cert checking is broken.
            wizard.set_validation_error(
                prevpage,
                "Could not get info from provider.")
            finish()
            return False
        except requests.exceptions.ConnectionError:
            wizard.set_validation_error(
                prevpage,
                "Could not download provider info "
                "(refused conn.).")
            finish()
            return False
        # XXX catch more errors...

        # We're done!
        self.set_done()
        finish()

    def _do_validation(self):
        """
        called after _do_checks has finished
        (connected to checker thread finished signal)
        """
        print 'validation...'
        prevpage = "providerselection"
        errors = self.wizard().get_validation_error(prevpage)

        if not errors:
            self.hide_progress()
            self.create_info_panel()
            self.show_provider_info()

        else:
            logger.debug('going back with errors')
            logger.debug('ERRORS: %s' % errors)
            self.go_back()

    def nextId(self):
        wizard = self.wizard()
        next_ = "providersetupvalidation"
        return wizard.get_page_index(next_)

    #def isComplete(self):
        #return self.is_done()

    def initializePage(self):
        super(ProviderInfoPage, self).initializePage()
        self.show_progress()
        self.set_undone()
        self.completeChanged.emit()

    def cleanupPage(self):
        del self.wizard().providerconfig

        if self.infoWidget:
            QtCore.QObjectCleanupHandler().add(
                self.infoWidget)

        # refactor this into some kind of destructor
        del self.displayName
        del self.description
        del self.enrollment_policy
