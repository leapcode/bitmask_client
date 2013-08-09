# qmake file

# is not there a f*** way of expanding this? other to template with python I mean...

# to get a list of python files we can use:
# find . -iname "*.py" | grep -Ev "__init__.py|/build/|/docs/|/gui/ui_[a-z]*.py|/gui/[a-z]*_rc.py|./.venv/|/tests/"
# and remove by hand the few files that we do not want.

SOURCES += ../src/leap/app.py \
           ../src/leap/config/leapsettings.py \
           ../src/leap/config/providerconfig.py \
           ../src/leap/crypto/srpauth.py \
           ../src/leap/crypto/srpregister.py \
           ../src/leap/gui/loggerwindow.py \
           ../src/leap/gui/login.py \
           ../src/leap/gui/mainwindow.py \
           ../src/leap/gui/statuspanel.py \
           ../src/leap/gui/twisted_main.py \
           ../src/leap/gui/wizardpage.py \
           ../src/leap/gui/wizard.py \
           ../src/leap/platform_init/initializers.py \
           ../src/leap/platform_init/locks.py \
           ../src/leap/provider/supportedapis.py \
           ../src/leap/services/abstractbootstrapper.py \
           ../src/leap/services/eip/eipbootstrapper.py \
           ../src/leap/services/eip/eipconfig.py \
           ../src/leap/services/eip/providerbootstrapper.py \
           ../src/leap/services/eip/udstelnet.py \
           ../src/leap/services/eip/vpnlaunchers.py \
           ../src/leap/services/eip/vpnprocess.py \
           ../src/leap/services/mail/smtpbootstrapper.py \
           ../src/leap/services/mail/smtpconfig.py \
           ../src/leap/services/soledad/soledadbootstrapper.py \
           ../src/leap/services/soledad/soledadconfig.py \
           ../src/leap/services/tx.py \
           ../src/leap/util/constants.py \
           ../src/leap/util/keyring_helpers.py \
           ../src/leap/util/leap_argparse.py \
           ../src/leap/util/leap_log_handler.py \
           ../src/leap/util/privilege_policies.py \
           ../src/leap/util/pyside_tests_helper.py \
           ../src/leap/util/request_helpers.py \
           ../src/leap/util/requirement_checker.py

FORMS += ../src/leap/gui/ui/loggerwindow.ui \
         ../src/leap/gui/ui/login.ui \
         ../src/leap/gui/ui/mainwindow.ui \
         ../src/leap/gui/ui/statuspanel.ui \
         ../src/leap/gui/ui/wizard.ui \

# where to generate ts files -- tx will pick from here

# original file, english

TRANSLATIONS    += ts/en_US.ts

