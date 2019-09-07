from setuptools import setup, find_packages

setup(
    name='OpenIDM',
    version='1.0.0',
    url='https://github.com/nikhil-nk/OpenIDM.git',
    license='MIT',
    author='Nikhil',
    description='A command-line tool to boost download speed.',
    packages=find_packages(),
    install_requires=['requests>=2.19.0'],
)
