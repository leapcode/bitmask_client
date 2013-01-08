import inspect
import logging

from PyQt4.QtCore import QCoreApplication
from PyQt4.QtCore import QLocale

logger = logging.getLogger(__name__)

"""
here I could not do all that I wanted.
the context is not getting passed to the xml file.
Looks like pylupdate4 is somehow a hack that does not
parse too well the python ast.
I guess we could generate the xml for ourselves as a last recourse.
"""

# XXX BIG NOTE:
# RESIST the temptation to get the translate function
# more compact, or have the Context argument passed as a variable
# Its name HAS to be explicit due  to how the pylupdate parser
# works.


qtTranslate = QCoreApplication.translate


def translate(*args, **kwargs):
    """
    our magic function.
    translate(Context, text, comment)
    """
    if len(args) == 1:
        obj = args[0]
        if isinstance(obj, LEAPTranslatable) and hasattr(obj, 'tr'):
            return obj.tr()

    klsname = None
    try:
        # get class value from instance
        # using live object inspection
        prev_frame = inspect.stack()[1][0]
        locals_ = inspect.getargvalues(prev_frame).locals
        self = locals_.get('self')
        if self:

            # Trying to  get the class name
            # but this is useless, the parser
            # has already got the context.
            klsname = self.__class__.__name__
            #print 'KLSNAME  -- ', klsname
    except:
        logger.error('error getting stack frame')

    if klsname:
        nargs = (klsname,) + args
        return qtTranslate(*nargs)

    else:
        nargs = ('default', ) + args
        return qtTranslate(*nargs)


class LEAPTranslatable(dict):
    """
    An extended dict that implements a .tr method
    so it can be translated on the fly by our
    magic  translate method
    """

    try:
        locale = str(QLocale.system().name()).split('_')[0]
    except:
        logger.warning("could not get system locale!")
        print "could not get system locale!"
        locale = "en"

    def tr(self, to=None):
        if not to:
            to = self.locale
        _tr = self.get(to, None)
        if not _tr:
            _tr = self.get("en", None)
        return _tr
