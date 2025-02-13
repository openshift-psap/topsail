import tempfile
import os

__keep_open = []
def get_tmp_fd():
    # generate a fd-only temporary file
    fd, file_path = tempfile.mkstemp()

    # using only the FD. Ensures that the file disappears when this
    # process terminates
    os.remove(file_path)

    py_file = os.fdopen(fd, 'w')
    # this makes sure the FD isn't closed when the var goes out of
    # scope
    __keep_open.append(py_file)

    return f"/proc/{os.getpid()}/fd/{fd}", py_file
