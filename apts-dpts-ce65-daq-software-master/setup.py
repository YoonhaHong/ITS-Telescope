"""The MLR1 DAQ software package
"""

from setuptools import setup

import subprocess
import os

git_hash = subprocess.check_output(['git','rev-parse','HEAD'],stderr=subprocess.STDOUT,encoding='utf-8').strip()
git_diff = subprocess.check_output(['git','diff'],stderr=subprocess.STDOUT,encoding='utf-8').strip()

pkg_dir = "mlr1daqboard/"
with open(pkg_dir+'git_hash','w') as f:
  f.write(git_hash)
with open(pkg_dir+'git_diff','w') as f:
  f.write(git_diff)

with open(pkg_dir+"_version.py") as f:
  version = f.readline().strip().split('=')[1].strip("'")

setup(
  name='mlr1-daq-software',
  version=version, # https://packaging.python.org/en/latest/single_source_version.html
  description='Software (tools and library) to operate the MLR1 chips using the DAQ board (rev4)',
  url='https://gitlab.cern.ch/alice-its3-wp3/apts-dpts-ce65-daq-software',

  author='ITS3 WP3',
  author_email='alice-its3-wp3@cern.ch',

  # https://pypi.org/classifiers/
  classifiers=[
    'Development Status :: 4 - Beta',
    'Intended Audience :: Developers',
    'Topic :: Scientific/Engineering :: Physics',
    'Topic :: Software Development :: Libraries :: Python Modules',
    'Topic :: System :: Hardware :: Hardware Drivers',
    'Programming Language :: Python :: 3 :: Only',
  ],

  keywords='APTS, DPTS, CE65, ITS3, ALICE',

  packages=['mlr1daqboard'],
  
  package_data={
      'mlr1daqboard': ['git_hash','git_diff','calibration/*.json'],
  },

  python_requires='>=3.7, <4',

  install_requires=['pyusb','tqdm','pyyaml','numpy', 'fire'],

  scripts=[
    'tools/mlr1-daq-program',
    'tools/pico-daq'
  ],
          
  project_urls={
    'ALICE ITS3 TWiki'              :'https://twiki.cern.ch/ALICE/ITS3'                                 ,
    'ALICE ITS3 WP3 TWiki'          :'https://twiki.cern.ch/ALICE/ITS3WP3'                              ,
    'ALICE ITS3 WP3 GitLab'         :'http://gitlab.cern.ch/alice-its3-wp3/'                            ,
    'Source'                        :'https://gitlab.cern.ch/alice-its3-wp3/apts-dpts-ce65-daq-software'         ,
  },
)

os.remove(pkg_dir+'git_hash')
os.remove(pkg_dir+'git_diff')