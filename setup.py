#!/usr/bin/python2

import os
import distutils.core

try:
    import py2exe
except:
    pass

def read(filename):
    return open(os.path.join(os.path.dirname(__file__), filename)).read()

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
    scripts=['schoollibrary-client'],
    data_files=[
        ("/usr/share/schoollibrary", [
            "usr/share/schoollibrary/add-book.png",
            "usr/share/schoollibrary/basket-go.png",
            "usr/share/schoollibrary/basket.png",
            "usr/share/schoollibrary/schoollibrary.png",
            "usr/share/schoollibrary/search-books.png",
            "usr/share/schoollibrary/basket-back.png"
        ])
    ],
    windows=["schoollibrary-client"]
)
