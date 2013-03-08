# qmake file

# is not there a f*** way of expanding this? other to template with python I mean...

SOURCES += ../src/leap/gui/mainwindow.py \
           ../src/leap/gui/wizardpage.py \
           ../src/leap/gui/wizard.py \
           ../src/leap/config/provider_spec.py \
           ../src/leap/config/pluggableconfig.py \
           ../src/leap/config/providerconfig.py \
           ../src/leap/config/prefixers.py \
           ../src/leap/config/baseconfig.py \
           ../src/leap/app.py \
           ../src/leap/util/checkerthread.py \
           ../src/leap/util/leap_argparse.py \
           ../src/leap/util/check.py \
           ../src/leap/crypto/constants.py \
           ../src/leap/crypto/srpauth.py \
           ../src/leap/crypto/srpregister.py \
           ../src/leap/services/eip/eipbootstrapper.py \
           ../src/leap/services/eip/udstelnet.py \
           ../src/leap/services/eip/eipspec.py \
           ../src/leap/services/eip/vpn.py \
           ../src/leap/services/eip/vpnlaunchers.py \
           ../src/leap/services/eip/providerbootstrapper.py \
           ../src/leap/services/eip/eipconfig.py

FORMS += ../src/leap/gui/ui/mainwindow.ui \
         ../src/leap/gui/ui/wizard.ui

# where to generate ts files -- tx will pick from here

# original file, english

TRANSLATIONS    += ts/en_US.ts

