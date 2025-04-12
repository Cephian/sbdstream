from setuptools import setup, find_packages

setup(
    name="sbdstream",
    version="0.1.0",
    packages=["src"],
    package_dir={"src": "src"},
    install_requires=[
        "pyside6>=6.0.0",
        "python-dateutil>=2.8.2",
    ],
    entry_points={
        "console_scripts": [
            "sbdstream=src.main:main",
        ],
    },
    include_package_data=True,
) 