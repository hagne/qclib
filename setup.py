import sys

required_verion = (3,)
if sys.version_info < required_verion:
    raise ValueError('At least python {} needed! You are trying to install under python {}'.format('.'.join(str(i) for i in required_verion), sys.version))

# import ez_setup
# ez_setup.use_setuptools()

from setuptools import setup
# from distutils.core import setup
setup(
    name="qclib",
    version="0.1",
    packages=['qclib'],
    author="Hagen Telg",
    author_email="hagen@hagnet.net",
    description="Tools for data tagging and qc'ing",
    license="MIT",
    keywords="qc",
    url="https://github.com/hagne/qclib",
    # install_requires=['numpy','pandas'],
    # extras_require={'plotting': ['matplotlib'],
    #                 'testing': ['scipy']},
    # test_suite='nose.collector',
    # tests_require=['nose'],
)