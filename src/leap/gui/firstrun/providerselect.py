"""
Select Provider Page, used in First Run Wizard
"""
import logging

import requests

from PyQt4 import QtCore
from PyQt4 import QtGui

from leap.base import exceptions as baseexceptions
#from leap.crypto import certs
from leap.eip import exceptions as eipexceptions
from leap.gui.progress import InlineValidationPage
from leap.gui import styles
from leap.gui.utils import delay
from leap.util.web import get_https_domain_and_port

from leap.gui.constants import APP_LOGO

logger = logging.getLogger(__name__)


class SelectProviderPage(InlineValidationPage):

    launchChecks = QtCore.pyqtSignal()

    def __init__(self, parent=None, providers=None):
        super(SelectProviderPage, self).__init__(parent)
        self.current_page = 'providerselection'

        self.setTitle(self.tr("Enter Provider"))
        self.setSubTitle(self.tr(
            "Please enter the domain of the provider you want "
            "to use for your connection.")
        )
        self.setPixmap(
            QtGui.QWizard.LogoPixmap,
            QtGui.QPixmap(APP_LOGO))

        self.did_cert_check = False

        self.done = False

        self.setupSteps()
        self.setupUI()

        self.launchChecks.connect(
            self.launch_checks)

        self.providerNameEdit.editingFinished.connect(
            lambda: self.providerCheckButton.setFocus(True))

    def setupUI(self):
        """
        initializes the UI
        """
        providerNameLabel = QtGui.QLabel("h&ttps://")
        # note that we expect the bare domain name
        # we will add the scheme later
        providerNameEdit = QtGui.QLineEdit()
        providerNameEdit.cursorPositionChanged.connect(
            self.reset_validation_status)
        providerNameLabel.setBuddy(providerNameEdit)

        # add regex validator
        providerDomainRe = QtCore.QRegExp(r"^[a-z1-9_\-\.]+$")
        providerNameEdit.setValidator(
            QtGui.QRegExpValidator(providerDomainRe, self))
        self.providerNameEdit = providerNameEdit

        # Eventually we will seed a list of
        # well known providers here.

        #providercombo = QtGui.QComboBox()
        #if providers:
            #for provider in providers:
                #providercombo.addItem(provider)
        #providerNameSelect = providercombo

        self.registerField("provider_domain*", self.providerNameEdit)
        #self.registerField('provider_name_index', providerNameSelect)

        validationMsg = QtGui.QLabel("")
        validationMsg.setStyleSheet(styles.ErrorLabelStyleSheet)
        self.validationMsg = validationMsg
        providerCheckButton = QtGui.QPushButton(self.tr("chec&k!"))
        self.providerCheckButton = providerCheckButton

        # cert info

        # this is used in the callback
        # for the checkbox changes.
        # tricky, since the first time came
        # from the exception message.
        # should get string from exception too!
        self.bad_cert_status = self.tr(
            "Server certificate could not be verified.")

        self.certInfo = QtGui.QLabel("")
        self.certInfo.setWordWrap(True)
        self.certWarning = QtGui.QLabel("")
        self.trustProviderCertCheckBox = QtGui.QCheckBox(
            "&Trust this provider certificate.")

        self.trustProviderCertCheckBox.stateChanged.connect(
            self.onTrustCheckChanged)
        self.providerNameEdit.textChanged.connect(
            self.onProviderChanged)
        self.providerCheckButton.clicked.connect(
            self.onCheckButtonClicked)

        layout = QtGui.QGridLayout()
        layout.addWidget(validationMsg, 0, 2)
        layout.addWidget(providerNameLabel, 1, 1)
        layout.addWidget(providerNameEdit, 1, 2)
        layout.addWidget(providerCheckButton, 1, 3)

        # add certinfo group
        # XXX not shown now. should move to validation box.
        #layout.addWidget(certinfoGroup, 4, 1, 4, 2)
        #self.certinfoGroup = certinfoGroup
        #self.certinfoGroup.hide()

        # add validation frame
        self.setupValidationFrame()
        layout.addWidget(self.valFrame, 4, 2, 4, 2)
        self.valFrame.hide()

        self.setLayout(layout)

    # certinfo

    def setupCertInfoGroup(self):  # pragma: no cover
        # XXX not used now.
        certinfoGroup = QtGui.QGroupBox(
            self.tr("Certificate validation"))
        certinfoLayout = QtGui.QVBoxLayout()
        certinfoLayout.addWidget(self.certInfo)
        certinfoLayout.addWidget(self.certWarning)
        certinfoLayout.addWidget(self.trustProviderCertCheckBox)
        certinfoGroup.setLayout(certinfoLayout)
        self.certinfoGroup = self.certinfoGroup

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

    @QtCore.pyqtSlot()
    def onDisableCheckButton(self):
        #print 'CHECK BUTTON DISABLED!!!'
        self.providerCheckButton.setDisabled(True)

    @QtCore.pyqtSlot()
    def launch_checks(self):
        self.do_checks()

    def onCheckButtonClicked(self):
        QtCore.QMetaObject.invokeMethod(
            self, "onDisableCheckButton")

        QtCore.QMetaObject.invokeMethod(
            self, "showStepsFrame")

        delay(self, "launch_checks")

    def _do_checks(self):
        """
        generator that yields actual checks
        that are executed in a separate thread
        """

        wizard = self.wizard()
        full_domain = self.providerNameEdit.text()

        # we check if we have a port in the domain string.
        domain, port = get_https_domain_and_port(full_domain)
        _domain = u"%s:%s" % (domain, port) if port != 443 else unicode(domain)

        netchecker = wizard.netchecker()
        providercertchecker = wizard.providercertchecker()
        eipconfigchecker = wizard.eipconfigchecker(domain=_domain)

        yield(("head_sentinel", 0), lambda: None)

        ########################
        # 1) try name resolution
        ########################

        def namecheck():
            """
            in which we check if
            we are able to name resolve
            this domain
            """
            try:
                #import ipdb;ipdb.set_trace()
                netchecker.check_name_resolution(
                    domain)

            except baseexceptions.LeapException as exc:
                logger.error(exc.message)
                return self.fail(exc.usermessage)

            except Exception as exc:
                return self.fail(exc.message)

            else:
                return True

        logger.debug('checking name resolution')
        yield((self.tr("checking domain name"), 20), namecheck)

        #########################
        # 2) try https connection
        #########################

        def httpscheck():
            """
            in which we check
            if the provider
            is offering service over
            https
            """
            try:
                providercertchecker.is_https_working(
                    "https://%s" % _domain,
                    verify=True)

            except eipexceptions.HttpsBadCertError as exc:
                logger.debug('exception')
                return self.fail(exc.usermessage)
                # XXX skipping for now...
                ##############################################
                # We had this validation logic
                # in the provider selection page before
                ##############################################
                #if self.trustProviderCertCheckBox.isChecked():
                    #pass
                #else:
                #fingerprint = certs.get_cert_fingerprint(
                    #domain=domain, sep=" ")

                # it's ok if we've trusted this fgprt before
                #trustedcrts = wizard.trusted_certs
                #if trustedcrts and \
                # fingerprint.replace(' ', '') in trustedcrts:
                    #pass
                #else:
                    # let your user face panick :P
                    #self.add_cert_info(fingerprint)
                    #self.did_cert_check = True
                    #self.completeChanged.emit()
                    #return False

            except baseexceptions.LeapException as exc:
                return self.fail(exc.usermessage)

            except Exception as exc:
                return self.fail(exc.message)

            else:
                return True

        logger.debug('checking https connection')
        yield((self.tr("checking https connection"), 40), httpscheck)

        ##################################
        # 3) try download provider info...
        ##################################

        def fetchinfo():
            try:
                # XXX we already set _domain in the initialization
                # so it should not be needed here.
                eipconfigchecker.fetch_definition(domain=_domain)
                wizard.set_providerconfig(
                    eipconfigchecker.defaultprovider.config)
            except requests.exceptions.SSLError:
                # XXX we should have catched this before.
                # but cert checking is broken.
                return self.fail(self.tr(
                    "Could not get info from provider."))
            except requests.exceptions.ConnectionError:
                return self.fail(self.tr(
                    "Could not download provider info "
                    "(refused conn.)."))

            except Exception as exc:
                return self.fail(
                    self.tr(exc.message))
            else:
                return True

        yield((self.tr("fetching provider info"), 80), fetchinfo)

        # done!

        self.done = True
        yield(("end_sentinel", 100), lambda: None)

    def on_checks_validation_ready(self):
        """
        called after _do_checks has finished.
        """
        self.domain_checked = True
        self.completeChanged.emit()
        # let's set focus...
        if self.is_done():
            self.wizard().clean_validation_error(self.current_page)
            nextbutton = self.wizard().button(QtGui.QWizard.NextButton)
            nextbutton.setFocus()
        else:
            self.providerNameEdit.setFocus()

    # cert trust verification
    # (disabled for now)

    def is_insecure_cert_trusted(self):
        return self.trustProviderCertCheckBox.isChecked()

    def onTrustCheckChanged(self, state):  # pragma: no cover XXX
        checked = False
        if state == 2:
            checked = True

        if checked:
            self.reset_validation_status()
        else:
            self.set_validation_status(self.bad_cert_status)

        # trigger signal to redraw next button
        self.completeChanged.emit()

    def add_cert_info(self, certinfo):  # pragma: no cover XXX
        self.certWarning.setText(
            "Do you want to <b>trust this provider certificate?</b>")
        self.certInfo.setText(
            'SHA-256 fingerprint: <i>%s</i><br>' % certinfo)
        self.certInfo.setWordWrap(True)
        self.certinfoGroup.show()

    def onProviderChanged(self, text):
        self.done = False
        provider = self.providerNameEdit.text()
        if provider:
            self.providerCheckButton.setDisabled(False)
        else:
            self.providerCheckButton.setDisabled(True)
        self.completeChanged.emit()

    def reset_validation_status(self):
        """
        empty the validation msg
        and clean the inline validation widget.
        """
        self.validationMsg.setText('')
        self.steps.removeAllSteps()
        self.clearTable()
        self.domain_checked = False

    # pagewizard methods

    def isComplete(self):
        provider = self.providerNameEdit.text()

        if not self.is_done():
            return False

        if not provider:
            return False
        else:
            if self.is_insecure_cert_trusted():
                return True
            if not self.did_cert_check:
                if self.is_done():
                    # XXX sure?
                    return True
            return False

    def populateErrors(self):
        # XXX could move this to ValidationMixin
        # with some defaults for the validating fields
        # (now it only allows one field, manually specified)

        #logger.debug('getting errors')
        errors = self.wizard().get_validation_error(
            self.current_page)
        if errors:
            bad_str = getattr(self, 'bad_string', None)
            cur_str = self.providerNameEdit.text()
            showerr = self.validationMsg.setText
            markred = lambda: self.providerNameEdit.setStyleSheet(
                styles.ErrorLineEdit)
            umarkrd = lambda: self.providerNameEdit.setStyleSheet(
                styles.RegularLineEdit)
            if bad_str is None:
                # first time we fall here.
                # save the current bad_string value
                self.bad_string = cur_str
                showerr(errors)
                markred()
            else:
                # not the first time
                # XXX hey, this is getting convoluted.
                # roll out this.
                # but be careful about all the possibilities
                # with going back and forth once you
                # enter a domain.
                if cur_str == bad_str:
                    showerr(errors)
                    markred()
                else:
                    if not getattr(self, 'domain_checked', None):
                        showerr('')
                        umarkrd()
                    else:
                        self.bad_string = cur_str
                        showerr(errors)

    def cleanup_errormsg(self):
        """
        we reset bad_string to None
        should be called before leaving the page
        """
        self.bad_string = None
        self.domain_checked = False

    def paintEvent(self, event):
        """
        we hook our populate errors
        on paintEvent because we need it to catch
        when user enters the page coming from next,
        and initializePage does not cover that case.
        Maybe there's a better event to hook upon.
        """
        super(SelectProviderPage, self).paintEvent(event)
        self.populateErrors()

    def initializePage(self):
        self.validationMsg.setText('')
        if hasattr(self, 'certinfoGroup'):
            # XXX remove ?
            self.certinfoGroup.hide()
        self.done = False
        self.providerCheckButton.setDisabled(True)
        self.valFrame.hide()
        self.steps.removeAllSteps()
        self.clearTable()

    def validatePage(self):
        # some cleanup before we leave the page
        self.cleanup_errormsg()

        # go
        return True

    def nextId(self):
        wizard = self.wizard()
        if not wizard:
            return
        return wizard.get_page_index('providerinfo')
