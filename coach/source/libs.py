import numpy as np
import cv2
# from google.colab.patches import cv2_imshow
# from google.colab import files
import csv
import os, shutil
# import zipfile
import io
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw
import requests
import tqdm
from mediapipe.python.solutions import drawing_utils as mp_drawing
from mediapipe.python.solutions import pose as mp_pose
import sys
from collections import defaultdict
import json
import socket

from .consts import *