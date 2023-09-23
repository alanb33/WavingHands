import os
import setuptools
from waving_hands import __version__

with open("README.md") as f:
    readme = f.read()

setuptools.setup(
    name="waving_hands",
    version=__version__,
    author="Alan Bailey",
    author_email="",
    description=(
        "P2P Multiplayer Python implementation of Richard Bartle's Waving Hands"
    ),
    long_description=readme,
    long_description_content_type="text/plain",
    license="GNUv3",
    keywords="waving hands turnbased",
    url="https://github.com/alanb33/WavingHands",
    packages=setuptools.find_packages(),
    include_package_data=True,
    entry_points={
        "console_scripts": ["waving-hands = waving_hands.waving_hands:main",],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Framework :: Pytest",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Topic :: Games/Entertainment :: Turn Based Strategy"
    ],
)
