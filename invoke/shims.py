import sys


if sys.platform == "win32":
    from ctypes import (
        windll,
        wintypes,
        create_unicode_buffer,
    )

    def _get_short_path_name(long_path: str) -> str:
        # Access `GetShortPathNameW()` function from `kernel32.dll`.
        GetShortPathNameW = windll.kernel32.GetShortPathNameW
        GetShortPathNameW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.LPWSTR,
            wintypes.DWORD,
        ]
        GetShortPathNameW.restype = wintypes.DWORD
        # Call function to get short path form.
        buffer_size = 0
        while True:
            buffer_array = create_unicode_buffer(buffer_size)
            required_size = GetShortPathNameW(
                long_path,
                buffer_array,
                buffer_size,
            )
            if required_size > buffer_size:
                buffer_size = required_size
            else:
                return buffer_array.value

else:

    def _get_short_path_name(long_path: str) -> str:
        return long_path


def get_short_path_name(long_path: str) -> str:
    """
    Get short path form for long path.

    Only applies to Windows-based systems; on Unix this is a pass-thru.

    .. note::
        This API converts path strings to the 8.3 format used by earlier
        tools on the Windows platform.  This format has no spaces.

    :param long_path: Long path such as `shutil.which()` results.

    :returns: `str` Short path form of the long path.
    """
    return _get_short_path_name(long_path)
