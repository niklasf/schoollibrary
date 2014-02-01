from distutils.core import setup
import py2exe

# Microsoft Visual C++ 2008 Redistributable Package published 29-11-2007
# http://www.microsoft.com/downloads/en/details.aspx?FamilyID=9b2da534-3e03-4391-8a4d-074b9f2bc1bf&displaylang=en
import sys
sys.path.append('C:\\WINDOWS\\WinSxS\\x86_microsoft.vc90.crt_1fc8b3b9a1e18e3b_9.0.30729.4148_none_5090ab56bcba71c2')

setup(
    data_files = [
        ("usr/share/schoollibrary", ["usr/share/schoollibrary/add-book.png"]),
        ("usr/share/schoollibrary", ["usr/share/schoollibrary/basket.png"]),
        ("usr/share/schoollibrary", ["usr/share/schoollibrary/basket-back.png"]),
        ("usr/share/schoollibrary", ["usr/share/schoollibrary/basket-go.png"]),
        ("usr/share/schoollibrary", ["usr/share/schoollibrary/schoollibrary.png"]),
        ("usr/share/schoollibrary", ["usr/share/schoollibrary/search-books.png"]),
        ("", ["schoollibrary.ico"]),
        ("", ["README.md"])
    ],
    windows=[
        {
            "script": "schoollibrary-client"
        }
    ]
)