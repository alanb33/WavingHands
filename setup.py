import os
import setuptools

with open("README.md") as f:
    readme = f.read()

setuptools.setup(
    name="waving_hands",
    version="0.1.0",
    author="Alan Bailey",
    author_email="",
    description=(
        "P2P Multiplayer Python implementation of Richard Bartle's Waving Hands"
    ),
    long_description=readme,
    long_descritpion_content_type="text/plain",
    license="GNUv3",
    keywords="waving hands turnbased",
    url="https://github.com/alanb33/WavingHands",
    packages=setuptools.find_packages(),
    entry_points={
        "console_scripts": ["waving-hands = waving_hands.waving_hands:main",],
    },
    classifiers=[],
)
