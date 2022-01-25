# -*- coding: utf-8 -*-

# Global configuration variables. The approach is adapted
# from Numba's config.py

import os

# Number of VkFFTApp to cache through the pyvkfft.fft interface
# This must be modified *before* importing pyvkfft.fft
FFT_CACHE_NB = 32

# Force using a LUT for single-precision transforms ?
# If None, this will be activated automatically for some GPU (Intel)
# Use only to improve the accuracy by a factor 3 or 4
# If useLUT is passed directly to a VkFFTApp, this is ignored
# Valid values: either None or 1
USE_LUT = None


def process_environ(environ):
    if "PYVKFFT_FFT_CACHE_NB" in environ:
        FFT_CACHE_NB = eval(environ["PYVKFFT_FFT_CACHE_NB"])
    else:
        FFT_CACHE_NB = 32

    if "PYVKFFT_USE_LUT" in environ:
        USE_LUT = eval(environ["PYVKFFT_USE_LUT"])
    else:
        USE_LUT = None

    # Inject values into the module globals
    for name, value in locals().copy().items():
        if name.isupper():
            globals()[name] = value


class _EnvReloader(object):

    def __init__(self):
        self.reset()
        self.old_environ = {}

    def reset(self):
        self.old_environ = {}
        self.update(force=True)

    def update(self, force=False):
        new_environ = {}

        for name, value in os.environ.items():
            if name.startswith('PYVKFFT_'):
                print(name, value)
                new_environ[name] = value
        if force or self.old_environ != new_environ:
            process_environ(new_environ)
            self.old_environ = new_environ


_env_reloader = _EnvReloader()


def _reload_config():
    """
    Reload the configuration from environment variables, if necessary.
    """
    _env_reloader.update()
