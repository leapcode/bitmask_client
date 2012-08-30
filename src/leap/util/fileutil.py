import errno
from itertools import chain
import logging
import os
import platform
import stat


logger = logging.getLogger()


def is_user_executable(fpath):
    st = os.stat(fpath)
    return bool(st.st_mode & stat.S_IXUSR)


def extend_path():
    ourplatform = platform.system()
    if ourplatform == "Linux":
        return "/usr/local/sbin:/usr/sbin"
    # XXX add mac / win extended search paths?


def which(program, path=None):
    """
    an implementation of which
    that extends the path with
    other locations, like sbin
    (f.i., openvpn binary is likely to be there)
    @param program: a string representing the binary we're looking for.
    """
    def is_exe(fpath):
        """
        check that path exists,
        it's a file,
        and is executable by the owner
        """
        # we would check for access,
        # but it's likely that we're
        # using uid 0 + polkitd

        return os.path.isfile(fpath)\
            and is_user_executable(fpath)

    def ext_candidates(fpath):
        yield fpath
        for ext in os.environ.get("PATHEXT", "").split(os.pathsep):
            yield fpath + ext

    def iter_path(pathset):
        """
        returns iterator with
        full path for a given path list
        and the current target bin.
        """
        for path in pathset.split(os.pathsep):
            exe_file = os.path.join(path, program)
            #print 'file=%s' % exe_file
            for candidate in ext_candidates(exe_file):
                if is_exe(candidate):
                    yield candidate

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        # extended iterator
        # with extra path
        if path is None:
            path = os.environ['PATH']
        extended_path = chain(
            iter_path(path),
            iter_path(extend_path()))
        for candidate in extended_path:
            if candidate is not None:
                return candidate

    # sorry bro.
    return None


def mkdir_p(path):
    """
    implements mkdir -p functionality
    """
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST:
            pass
        else:
            raise


def check_and_fix_urw_only(_file):
    """
    test for 600 mode and try
    to set it if anything different found
    """
    mode = stat.S_IMODE(
        os.stat(_file).st_mode)

    if mode != int('600', 8):
        try:
            logger.warning(
                'bad permission on %s '
                'attempting to set 600',
                _file)
            os.chmod(_file, stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            logger.error(
                'error while trying to chmod 600 %s',
                _file)
            raise
