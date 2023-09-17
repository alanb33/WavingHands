import os
import setuptools

setuptools.setup(
    name="waving_hands",
    version="0.1.0",
    author="Alan Bailey",
    author_email="",
    description=(
        "P2P Multiplayer Python implementation of Richard Bartle's Waving Hands"
    ),
    license="GNUv3",
    keywords="waving hands turnbased",
    url="https://github.com/alanb33/WavingHands",
    packages=setuptools.find_packages(),
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
