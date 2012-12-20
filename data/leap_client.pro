# qmake file

# is not there a f*** way of expanding this? other to template with python I mean...

SOURCES += ../src/leap/base/exceptions.py
SOURCES += ../src/leap/gui/firstrun/intro.py
SOURCES	+= ../src/leap/gui/firstrun/last.py
SOURCES	+= ../src/leap/gui/firstrun/login.py
SOURCES	+= ../src/leap/gui/firstrun/providerinfo.py
SOURCES	+= ../src/leap/gui/firstrun/providerselect.py
SOURCES	+= ../src/leap/gui/firstrun/providersetup.py
SOURCES	+= ../src/leap/gui/firstrun/register.py
SOURCES	+= ../src/leap/gui/firstrun/regvalidation.py
SOURCES	+= ../src/leap/gui/firstrun/wizard.py

# where to generate ts files -- tx will pick from here

# original file, english

TRANSLATIONS    += ts/en_US.ts

