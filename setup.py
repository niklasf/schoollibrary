#!/usr/bin/python2

import os
import distutils.core
import sys

try:
    import py2exe
    sys.path.append('C:\\WINDOWS\\WinSxS\\x86_microsoft.vc90.crt_1fc8b3b9a1e18e3b_9.0.30729.4148_none_5090ab56bcba71c2')
except:
    pass

def read(filename):
    return open(os.path.join(os.path.dirname(__file__), filename)).read()

def get_data_files():
    image_files = [
        "usr/share/schoollibrary/add-book.png",
        "usr/share/schoollibrary/basket-go.png",
        "usr/share/schoollibrary/basket.png",
        "usr/share/schoollibrary/pdf.png",
        "usr/share/schoollibrary/schoollibrary.png",
        "usr/share/schoollibrary/search-books.png",
        "usr/share/schoollibrary/basket-back.png"
    ]
    
    if "py2exe" in sys.argv:
        return [
            ("usr/share/schoollibrary", image_files),
            ("", [
                "schoollibrary.ico"
            ])
        ]

    if os.name == "nt":
        return [
            ("usr/share/schoollibrary", image_files)
        ]
    else:
        return [
            ("/usr/share/schoollibrary", image_files)
        ]

distutils.core.setup(
    name="Schoollibrary",
    version="0.0.1",
    description="Manage a school library",
    long_description=read("README.rst"),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Win32 (MS Windows)",
        "Environment :: X11 Applications :: Qt",
        "Intended Audience :: Education",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Natural Language :: German",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2 :: Only",
        "Topic :: Education"
    ],
    license="GPL3+",
    author="Niklas Fiekas",
    author_email="niklas.fiekas@tu-clausthal.de",
    packages=["schoollibrary"],
    data_files=get_data_files(),
    scripts=['schoollibrary-client'],
    windows=["schoollibrary-client"]
)
