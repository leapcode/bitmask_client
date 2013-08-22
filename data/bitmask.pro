# qmake file

# is not there a f*** way of expanding this? other to template with python I mean...

# to get a list of python files we can use:
# find . -iname "*.py" | grep -Ev "__init__.py|/build/|/docs/|/gui/ui_[a-z]*.py|/gui/[a-z]*_rc.py|./.venv/|/tests/"
# and remove by hand the few files that we do not want.

SOURCES += ../src/leap/bitmask/app.py \
           ../src/leap/bitmask/config/leapsettings.py \
           ../src/leap/bitmask/config/providerconfig.py \
           ../src/leap/bitmask/crypto/srpauth.py \
           ../src/leap/bitmask/crypto/srpregister.py \
           ../src/leap/bitmask/gui/loggerwindow.py \
           ../src/leap/bitmask/gui/login.py \
           ../src/leap/bitmask/gui/mainwindow.py \
           ../src/leap/bitmask/gui/statuspanel.py \
           ../src/leap/bitmask/gui/twisted_main.py \
           ../src/leap/bitmask/gui/wizardpage.py \
           ../src/leap/bitmask/gui/wizard.py \
           ../src/leap/bitmask/platform_init/initializers.py \
           ../src/leap/bitmask/platform_init/locks.py \
           ../src/leap/bitmask/provider/supportedapis.py \
           ../src/leap/bitmask/services/abstractbootstrapper.py \
           ../src/leap/bitmask/services/eip/eipbootstrapper.py \
           ../src/leap/bitmask/services/eip/eipconfig.py \
           ../src/leap/bitmask/services/eip/providerbootstrapper.py \
           ../src/leap/bitmask/services/eip/udstelnet.py \
           ../src/leap/bitmask/services/eip/vpnlaunchers.py \
           ../src/leap/bitmask/services/eip/vpnprocess.py \
           ../src/leap/bitmask/services/mail/smtpbootstrapper.py \
           ../src/leap/bitmask/services/mail/smtpconfig.py \
           ../src/leap/bitmask/services/soledad/soledadbootstrapper.py \
           ../src/leap/bitmask/services/soledad/soledadconfig.py \
           ../src/leap/bitmask/services/tx.py \
           ../src/leap/bitmask/util/constants.py \
           ../src/leap/bitmask/util/keyring_helpers.py \
           ../src/leap/bitmask/util/leap_argparse.py \
           ../src/leap/bitmask/util/leap_log_handler.py \
           ../src/leap/bitmask/util/privilege_policies.py \
           ../src/leap/bitmask/util/pyside_tests_helper.py \
           ../src/leap/bitmask/util/request_helpers.py \
           ../src/leap/bitmask/util/requirement_checker.py

FORMS += ../src/leap/bitmask/gui/ui/loggerwindow.ui \
         ../src/leap/bitmask/gui/ui/login.ui \
         ../src/leap/bitmask/gui/ui/mainwindow.ui \
         ../src/leap/bitmask/gui/ui/statuspanel.ui \
         ../src/leap/bitmask/gui/ui/wizard.ui \

# where to generate ts files -- tx will pick from here

# original file, english

TRANSLATIONS    += ts/en_US.ts
