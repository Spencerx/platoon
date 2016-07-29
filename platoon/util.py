from __future__ import print_function
import os
import subprocess
import cffi

import numpy as np
try:
    from mpi4py import MPI
except ImportError:
    MPI = None


class PlatoonError(Exception):
    """Exception used for most errors related to Platoon.
    """
    pass

class PlatoonFail(Exception):
    def __init__(self):
        super(PlatoonError, self).__init__("One or more processes in host have "
                                           "exited. Platoon has failed. Check logs.")


def mmap(length=0, prot=0x3, flags=0x1, fd=0, offset=0):
    _ffi = cffi.FFI()
    _ffi.cdef("void *mmap(void *, size_t, int, int, int, size_t);")
    _lib = _ffi.dlopen(None)

    addr = _ffi.NULL

    m = _lib.mmap(addr, length, prot, flags, fd, offset)
    if m == _ffi.cast('void *', -1):
        raise OSError(_ffi.errno, "for mmap")
    return _ffi.buffer(m, length)


def launch_process(logs_folder, experiment_name, args, device, process_type="worker"):
    print("## Starting {0} on {1} ...".format(process_type, device), end=' ')

    log_file = os.path.join(logs_folder, "{0}{1}.{{}}".format(process_type, device))
    with open(log_file.format("out"), 'w') as stdout_file:
        with open(log_file.format("err"), 'w') as stderr_file:
            env = dict(os.environ)
            env['THEANO_FLAGS'] = '{},device={}'.format(env.get('THEANO_FLAGS', ''), device)
            command = ["python", "-u", "{0}_{1}.py".format(experiment_name, process_type)]
            if args is not None:
                command += args
            process = subprocess.Popen(command, bufsize=0, stdout=stdout_file, stderr=stderr_file, env=env)

    print("Done")
    return process

if MPI:
    GA_TO_MPI_OP = {
        '+': MPI.SUM,
        "sum": MPI.SUM,
        "add": MPI.SUM,
        '*': MPI.PROD,
        "prod": MPI.PROD,
        "product": MPI.PROD,
        "max": MPI.MAX,
        "maximum": MPI.MAX,
        "min": MPI.MIN,
        "minimum": MPI.MIN,
        }

    NP_TO_MPI_TYPE = {
        np.dtype('bool'): MPI.C_BOOL,
        np.dtype('int8'): MPI.INT8_T,
        np.dtype('uint8'): MPI.UINT8_T,
        np.dtype('int16'): MPI.INT16_T,
        np.dtype('uint16'): MPI.UINT16_T,
        np.dtype('int32'): MPI.INT32_T,
        np.dtype('uint32'): MPI.UINT32_T,
        np.dtype('int64'): MPI.INT64_T,
        np.dtype('uint64'): MPI.UINT64_T,
        np.dtype('float32'): MPI.FLOAT,
        np.dtype('float64'): MPI.DOUBLE,
        np.dtype('complex64'): MPI.C_FLOAT_COMPLEX,
        np.dtype('complex128'): MPI.C_DOUBLE_COMPLEX,
        # TODO How to handle half types in MPI?
        #  np.dtype('float16'): MPI.HALF,
        }


def op_to_mpi(op):
    if MPI is None:
        raise PlatoonError("mpi4py is not imported")
    res = GA_TO_MPI_OP.get(op.lower())
    if res is not None:
        return res
    raise ValueError("Invalid reduce operation: {}".format(str(op)))


def dtype_to_mpi(dtype):
    if MPI is None:
        raise PlatoonError("mpi4py is not imported")
    res = NP_TO_MPI_TYPE.get(np.dtype(dtype))
    if res is not None:
        return res
    raise ValueError("Conversion from dtype {} is not known".format(dtype)
