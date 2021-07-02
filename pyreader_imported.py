import os
import sys
from pathlib import Path

pyreader_path = str(Path(__file__).parent.parent / 'out/bin')
os.environ['PATH'] = pyreader_path + os.pathsep + os.environ['PATH']
sys.path.insert(0, pyreader_path)

from pyreader import readpdf