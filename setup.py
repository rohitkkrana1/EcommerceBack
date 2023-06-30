from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in ecomm/__init__.py
from ecomm import __version__ as version

setup(
	name="ecomm",
	version=version,
	description="Extends ecommerce ",
	author="Rohit Rana",
	author_email="rohitkkrana@gmail.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
