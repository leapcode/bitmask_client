import inspect

from PyQt4.QtCore import QCoreApplication

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
# It HAS to be explicit due  to how the pylupdate parser
# works.


qtTranslate = QCoreApplication.translate


class LEAPTr:
    pass


def translate(*args):
    """
    translate(Context, text, comment)
    """
    print 'translating...'
    klsname = None
    try:
        # get class value from instance
        # using live object inspection
        prev_frame = inspect.stack()[1][0]
        self = inspect.getargvalues(prev_frame).locals.get('self')
        if self:
            # XXX will this work with QObject wrapper??
            if isinstance(LEAPTr, self) and hasattr(self, 'tr'):
                print "we got a self in base class"
                return self.tr(*args)

            # Trying to  get the class name
            # but this is useless, the parser
            # has already got the context.
            klsname = self.__class__.__name__
            print 'KLSNAME  -- ', klsname
    except:
        print 'error getting stack frame'

    if klsname:
        nargs = (klsname,) + args
        return qtTranslate(*nargs)

    else:
        nargs = ('default', ) + args
        return qtTranslate(*nargs)
