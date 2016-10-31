"""neuropy installation script

to create source distribution and force tar.gz file:
>>> python setup.py sdist --formats=gztar
to create binary distribution:
>>> python setup.py bdist_wininst
"""

from distutils.core import setup
import os
from neuropy import __version__

setup(name='neuropy',
      version=__version__,
      license='BSD',
      description='Neuronal spike data and stimulus analysis in Python',
      author='Martin Spacek',
      author_email='git at mspacek mm st',
      url='http://neuropy.github.io',
      #long_description='',
      #packages=['neuropy', 'neuropy.scripts'])
      packages=['neuropy'])
