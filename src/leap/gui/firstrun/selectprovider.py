"""
Select Provider Page, used in First Run Wizard
"""
from PyQt4 import QtCore
from PyQt4 import QtGui

from leap.base import exceptions as baseexceptions
from leap.crypto import certs
from leap.eip import exceptions as eipexceptions

from leap.gui.constants import APP_LOGO
from leap.gui.styles import ErrorLabelStyleSheet


class SelectProviderPage(QtGui.QWizardPage):
    def __init__(self, parent=None, providers=None):
        super(SelectProviderPage, self).__init__(parent)

        self.setTitle("Enter Provider")
        self.setSubTitle(
            "Please enter the domain of the provider you want "
            "to use for your connection."
        )
        self.setPixmap(
            QtGui.QWizard.LogoPixmap,
            QtGui.QPixmap(APP_LOGO))

        self.did_cert_check = False

        providerNameLabel = QtGui.QLabel("h&ttps://")
        # note that we expect the bare domain name
        # we will add the scheme later
        providerNameEdit = QtGui.QLineEdit()
        providerNameEdit.cursorPositionChanged.connect(
            self.reset_validation_status)
        providerNameLabel.setBuddy(providerNameEdit)

        # add regex validator
        providerDomainRe = QtCore.QRegExp(r"^[a-z\d_-.]+$")
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

        self.registerField('provider_domain*', self.providerNameEdit)
        #self.registerField('provider_name_index', providerNameSelect)

        validationMsg = QtGui.QLabel("")
        validationMsg.setStyleSheet(ErrorLabelStyleSheet)
        self.validationMsg = validationMsg

        # cert info

        # this is used in the callback
        # for the checkbox changes.
        # tricky, since the first time came
        # from the exception message.
        # should get string from exception too!
        self.bad_cert_status = "Server certificate could not be verified."

        self.certInfo = QtGui.QLabel("")
        self.certInfo.setWordWrap(True)
        self.certWarning = QtGui.QLabel("")
        self.trustProviderCertCheckBox = QtGui.QCheckBox(
            "&Trust this provider certificate.")

        self.trustProviderCertCheckBox.stateChanged.connect(
            self.onTrustCheckChanged)

        layout = QtGui.QGridLayout()
        layout.addWidget(validationMsg, 0, 2)
        layout.addWidget(providerNameLabel, 1, 1)
        layout.addWidget(providerNameEdit, 1, 2)

        # XXX get a groupbox or something....
        certinfoGroup = QtGui.QGroupBox("Certificate validation")
        certinfoLayout = QtGui.QVBoxLayout()
        certinfoLayout.addWidget(self.certInfo)
        certinfoLayout.addWidget(self.certWarning)
        certinfoLayout.addWidget(self.trustProviderCertCheckBox)
        certinfoGroup.setLayout(certinfoLayout)

        layout.addWidget(certinfoGroup, 4, 1, 4, 2)
        self.certinfoGroup = certinfoGroup
        self.certinfoGroup.hide()

        self.setLayout(layout)

    def is_insecure_cert_trusted(self):
        return self.trustProviderCertCheckBox.isChecked()

    def onTrustCheckChanged(self, state):
        checked = False
        if state == 2:
            checked = True

        if checked:
            self.reset_validation_status()
        else:
            self.set_validation_status(self.bad_cert_status)

        # trigger signal to redraw next button
        self.completeChanged.emit()

    def reset_validation_status(self):
        """
        empty the validation msg
        """
        self.validationMsg.setText('')

    def set_validation_status(self, status):
        self.validationMsg.setText(status)

    def add_cert_info(self, certinfo):
        self.certWarning.setText(
            "Do you want to <b>trust this provider certificate?</b>")
        self.certInfo.setText(
            'SHA-256 fingerprint: <i>%s</i><br>' % certinfo)
        self.certInfo.setWordWrap(True)
        self.certinfoGroup.show()

    # pagewizard methods

    def isComplete(self):
        if not self.did_cert_check:
            return True
        if self.is_insecure_cert_trusted():
            return True
        return False

    def initializePage(self):
        self.certinfoGroup.hide()

    def validatePage(self):
        ##################################
        # XXX FIXME!
        ##################################
        ##################################
        ##################################
        ##################################
        ##### validation skipped !!! #####
        ##################################
        ##################################
        return True
        ##################################
        ##################################
        ##################################

        # XXX move to ProviderInfo...

        wizard = self.wizard()
        netchecker = wizard.netchecker()
        providercertchecker = wizard.providercertchecker()
        eipconfigchecker = wizard.eipconfigchecker()

        domain = self.providerNameEdit.text()

        # try name resolution
        try:
            netchecker.check_name_resolution(
                domain)

        except baseexceptions.LeapException as exc:
            self.set_validation_status(exc.usermessage)
            return False

        # try https connection
        try:
            providercertchecker.is_https_working(
                "https://%s" % domain,
                verify=True)

        except eipexceptions.HttpsBadCertError as exc:
            if self.trustProviderCertCheckBox.isChecked():
                pass
            else:
                self.set_validation_status(exc.usermessage)
                fingerprint = certs.get_cert_fingerprint(
                    domain=domain, sep=" ")

                # it's ok if we've trusted this fgprt before
                trustedcrts = self.wizard().trusted_certs
                if trustedcrts and fingerprint.replace(' ', '') in trustedcrts:
                    pass
                else:
                    # let your user face panick :P
                    self.add_cert_info(fingerprint)
                    self.did_cert_check = True
                    self.completeChanged.emit()
                    return False

        except baseexceptions.LeapException as exc:
            self.set_validation_status(exc.usermessage)
            return False

        # try download provider info...
        eipconfigchecker.fetch_definition(domain=domain)
        wizard.set_providerconfig(
            eipconfigchecker.defaultprovider.config)

        # all ok, go on...
        return True

    def nextId(self):
        wizard = self.wizard()
        if not wizard:
            return
        return wizard.get_page_index('providerinfo')
