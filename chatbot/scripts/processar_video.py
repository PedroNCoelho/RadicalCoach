# -*- coding: utf-8 -*-
"""Skate Prototype 3.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1tnawV67k0bBBX6nELGNzXzg_215jknkT

# Terceiro protótipo da solução para skate

## Bibliotecas
"""

!pip install -q mediapipe

import numpy as np
import cv2
from google.colab.patches import cv2_imshow
from google.colab import files
import csv
import os, shutil
import pandas as pd
import matplotlib.pyplot as plt
import zipfile
import io
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw
import requests
import tqdm
from mediapipe.python.solutions import drawing_utils as mp_drawing
from mediapipe.python.solutions import pose as mp_pose

"""## Definições iniciais

### Constantes
"""

vb_f = 'video_buffer'
output_f = 'output'
reference_csvs_f = 'reference_csvs'
proc_f = 'processed'

video_name = 'video.mp4'
csv_name = 'output.csv'
output_video_name = 'output.mp4'
proc_video_name = 'proc.mp4'

video_path = vb_f+'/'+video_name
csv_path = output_f+'/'+csv_name
output_video_path = output_f+'/'+output_video_name
proc_video_path = proc_f+'/'+proc_video_name

"""### Funções auxiliares"""

def write_landmarks_to_csv(landmarks, frame_number, csv_data):
    for idx, landmark in enumerate(landmarks):
        csv_data.append([frame_number, mp_pose.PoseLandmark(idx).name, landmark.x, landmark.y, landmark.z])

def reset_folder(path):
    if os.path.isdir(path):
      shutil.rmtree(path)
    os.makedirs(path,exist_ok=True)

def landmark_coord(df, landmark_name):
  return df[df['landmark']==landmark_name][['x', 'y', 'z']].to_numpy()

def get_frame_landmarks(input_frame, pose_tracker):
  input_frame = cv2.cvtColor(input_frame, cv2.COLOR_BGR2RGB)
  pose_landmarks = pose_tracker.process(image=input_frame).pose_landmarks
  output_frame = input_frame.copy()

  # Save image with pose prediction (if pose was detected).
  if pose_landmarks is not None:
    mp_drawing.draw_landmarks(
        image=output_frame,
        landmark_list=pose_landmarks,
        connections=mp_pose.POSE_CONNECTIONS)
    # Get landmarks.
    frame_height, frame_width = output_frame.shape[0], output_frame.shape[1]
    pose_landmarks = np.array(
        [[lmk.x * frame_width, lmk.y * frame_height, lmk.z * frame_width]
          for lmk in pose_landmarks.landmark],
        dtype=np.float32)
    assert pose_landmarks.shape == (33, 3), 'Unexpected landmarks shape: {}'.format(pose_landmarks.shape)
  return pose_landmarks, output_frame

def make_reference_csvs(images_in_folder, csvs_out_folder):
  pose_class_names = sorted([n for n in os.listdir(images_in_folder) if not n.startswith('.')])
  # Create output folder for CSVs.
  if not os.path.exists(csvs_out_folder):
    os.makedirs(csvs_out_folder)

  for pose_class_name in pose_class_names:
    # Paths for the pose class.
    images_in_folder = os.path.join(images_in_folder, pose_class_name)
    csv_out_path = os.path.join(csvs_out_folder, pose_class_name + '.csv')

    with open(csv_out_path, 'w') as csv_out_file:
      csv_out_writer = csv.writer(csv_out_file, delimiter=',', quoting=csv.QUOTE_MINIMAL)
      # Get list of images.
      image_names = sorted([n for n in os.listdir(images_in_folder) if not n.startswith('.')])

      # Bootstrap every image.
      for image_name in image_names:
        # Load image.
        pose_tracker = mp_pose.Pose()
        input_frame = cv2.imread(os.path.join(images_in_folder, image_name))
        pose_landmarks, reference_frame = get_frame_landmarks(input_frame, pose_tracker)
        csv_out_writer.writerow([image_name] + pose_landmarks.flatten().astype(str).tolist())
        pose_tracker.close()

def video_with_counter(class_name, classification_per_frame):

  video_cap = cv2.VideoCapture(proc_video_path)
  # Get some video parameters to generate output video with classificaiton.
  video_n_frames = video_cap.get(cv2.CAP_PROP_FRAME_COUNT)
  video_fps = video_cap.get(cv2.CAP_PROP_FPS)
  video_width = int(video_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
  video_height = int(video_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

  # Initialize counter.
  repetition_counter = RepetitionCounter(
      class_name=class_name,
      enter_threshold=0,
      exit_threshold=1)

  # Initialize renderer.
  pose_classification_visualizer = PoseClassificationVisualizer(
      class_name=class_name,
      plot_x_max=video_n_frames,
      # Graphic looks nicer if it's the same as `top_n_by_mean_distance`.
      plot_y_max=10)

  # Open output video.
  out_video = cv2.VideoWriter(output_video_path, cv2.VideoWriter_fourcc(*'mp4v'), video_fps, (video_width, video_height))

  frame_idx = 0
  with tqdm.tqdm(total=video_n_frames, position=0, leave=True) as pbar:
    while True:
      # Get next frame of the video.
      success, input_frame = video_cap.read()
      if not success:
        break

      # Run pose tracker.
      output_frame = cv2.cvtColor(input_frame, cv2.COLOR_BGR2RGB)
      pose_classification = classification_per_frame[frame_idx]
      if pose_classification is not None:
        repetitions_count = repetition_counter(pose_classification)
      else:
        repetitions_count = repetition_counter.n_repeats

      # Draw classification plot and repetition counter.
      output_frame = pose_classification_visualizer(
          frame=output_frame,
          pose_classification=pose_classification,
          repetitions_count=repetitions_count)

      # Save the output frame.
      out_video.write(cv2.cvtColor(np.array(output_frame), cv2.COLOR_RGB2BGR))

      frame_idx += 1
      pbar.update()

  # Close output video.
  out_video.release()

  video_cap.release()

"""### Classes

#### Pose embedding
"""

class FullBodyPoseEmbedder(object):
  """Converts 3D pose landmarks into 3D embedding."""

  def __init__(self, torso_size_multiplier=2.5):
    # Multiplier to apply to the torso to get minimal body size.
    self._torso_size_multiplier = torso_size_multiplier

    # Names of the landmarks as they appear in the prediction.
    self._landmark_names = [
        'nose',
        'left_eye_inner', 'left_eye', 'left_eye_outer',
        'right_eye_inner', 'right_eye', 'right_eye_outer',
        'left_ear', 'right_ear',
        'mouth_left', 'mouth_right',
        'left_shoulder', 'right_shoulder',
        'left_elbow', 'right_elbow',
        'left_wrist', 'right_wrist',
        'left_pinky_1', 'right_pinky_1',
        'left_index_1', 'right_index_1',
        'left_thumb_2', 'right_thumb_2',
        'left_hip', 'right_hip',
        'left_knee', 'right_knee',
        'left_ankle', 'right_ankle',
        'left_heel', 'right_heel',
        'left_foot_index', 'right_foot_index',
    ]

  def __call__(self, landmarks):
    """Normalizes pose landmarks and converts to embedding

    Args:
      landmarks - NumPy array with 3D landmarks of shape (N, 3).

    Result:
      Numpy array with pose embedding of shape (M, 3) where `M` is the number of
      pairwise distances defined in `_get_pose_distance_embedding`.
    """
    assert landmarks.shape[0] == len(self._landmark_names), 'Unexpected number of landmarks: {}'.format(landmarks.shape[0])

    # Get pose landmarks.
    landmarks = np.copy(landmarks)

    # Normalize landmarks.
    landmarks = self._normalize_pose_landmarks(landmarks)

    # Get embedding.
    embedding = self._get_pose_distance_embedding(landmarks)

    return embedding

  def _normalize_pose_landmarks(self, landmarks):
    """Normalizes landmarks translation and scale."""
    landmarks = np.copy(landmarks)

    # Normalize translation.
    pose_center = self._get_pose_center(landmarks)
    landmarks -= pose_center

    # Normalize scale.
    pose_size = self._get_pose_size(landmarks, self._torso_size_multiplier)
    landmarks /= pose_size
    # Multiplication by 100 is not required, but makes it eaasier to debug.
    landmarks *= 100

    return landmarks

  def _get_pose_center(self, landmarks):
    """Calculates pose center as point between hips."""
    left_hip = landmarks[self._landmark_names.index('left_hip')]
    right_hip = landmarks[self._landmark_names.index('right_hip')]
    center = (left_hip + right_hip) * 0.5
    return center

  def _get_pose_size(self, landmarks, torso_size_multiplier):
    """Calculates pose size.

    It is the maximum of two values:
      * Torso size multiplied by `torso_size_multiplier`
      * Maximum distance from pose center to any pose landmark
    """
    # This approach uses only 2D landmarks to compute pose size.
    landmarks = landmarks[:, :2]

    # Hips center.
    left_hip = landmarks[self._landmark_names.index('left_hip')]
    right_hip = landmarks[self._landmark_names.index('right_hip')]
    hips = (left_hip + right_hip) * 0.5

    # Shoulders center.
    left_shoulder = landmarks[self._landmark_names.index('left_shoulder')]
    right_shoulder = landmarks[self._landmark_names.index('right_shoulder')]
    shoulders = (left_shoulder + right_shoulder) * 0.5

    # Torso size as the minimum body size.
    torso_size = np.linalg.norm(shoulders - hips)

    # Max dist to pose center.
    pose_center = self._get_pose_center(landmarks)
    max_dist = np.max(np.linalg.norm(landmarks - pose_center, axis=1))

    return max(torso_size * torso_size_multiplier, max_dist)

  def _get_pose_distance_embedding(self, landmarks):
    """Converts pose landmarks into 3D embedding.

    We use several pairwise 3D distances to form pose embedding. All distances
    include X and Y components with sign. We differnt types of pairs to cover
    different pose classes. Feel free to remove some or add new.

    Args:
      landmarks - NumPy array with 3D landmarks of shape (N, 3).

    Result:
      Numpy array with pose embedding of shape (M, 3) where `M` is the number of
      pairwise distances.
    """
    embedding = np.array([
        # One joint.

        self._get_distance(
            self._get_average_by_names(landmarks, 'left_hip', 'right_hip'),
            self._get_average_by_names(landmarks, 'left_shoulder', 'right_shoulder')),

        self._get_distance_by_names(landmarks, 'left_shoulder', 'left_elbow'),
        self._get_distance_by_names(landmarks, 'right_shoulder', 'right_elbow'),

        self._get_distance_by_names(landmarks, 'left_elbow', 'left_wrist'),
        self._get_distance_by_names(landmarks, 'right_elbow', 'right_wrist'),

        self._get_distance_by_names(landmarks, 'left_hip', 'left_knee'),
        self._get_distance_by_names(landmarks, 'right_hip', 'right_knee'),

        self._get_distance_by_names(landmarks, 'left_knee', 'left_ankle'),
        self._get_distance_by_names(landmarks, 'right_knee', 'right_ankle'),

        # Two joints.

        self._get_distance_by_names(landmarks, 'left_shoulder', 'left_wrist'),
        self._get_distance_by_names(landmarks, 'right_shoulder', 'right_wrist'),

        self._get_distance_by_names(landmarks, 'left_hip', 'left_ankle'),
        self._get_distance_by_names(landmarks, 'right_hip', 'right_ankle'),

        # Four joints.

        self._get_distance_by_names(landmarks, 'left_hip', 'left_wrist'),
        self._get_distance_by_names(landmarks, 'right_hip', 'right_wrist'),

        # Five joints.

        self._get_distance_by_names(landmarks, 'left_shoulder', 'left_ankle'),
        self._get_distance_by_names(landmarks, 'right_shoulder', 'right_ankle'),

        self._get_distance_by_names(landmarks, 'left_hip', 'left_wrist'),
        self._get_distance_by_names(landmarks, 'right_hip', 'right_wrist'),

        # Cross body.

        self._get_distance_by_names(landmarks, 'left_elbow', 'right_elbow'),
        self._get_distance_by_names(landmarks, 'left_knee', 'right_knee'),

        self._get_distance_by_names(landmarks, 'left_wrist', 'right_wrist'),
        self._get_distance_by_names(landmarks, 'left_ankle', 'right_ankle'),

        # Body bent direction.

        # self._get_distance(
        #     self._get_average_by_names(landmarks, 'left_wrist', 'left_ankle'),
        #     landmarks[self._landmark_names.index('left_hip')]),
        # self._get_distance(
        #     self._get_average_by_names(landmarks, 'right_wrist', 'right_ankle'),
        #     landmarks[self._landmark_names.index('right_hip')]),
    ])

    return embedding

  def _get_average_by_names(self, landmarks, name_from, name_to):
    lmk_from = landmarks[self._landmark_names.index(name_from)]
    lmk_to = landmarks[self._landmark_names.index(name_to)]
    return (lmk_from + lmk_to) * 0.5

  def _get_distance_by_names(self, landmarks, name_from, name_to):
    lmk_from = landmarks[self._landmark_names.index(name_from)]
    lmk_to = landmarks[self._landmark_names.index(name_to)]
    return self._get_distance(lmk_from, lmk_to)

  def _get_distance(self, lmk_from, lmk_to):
    return lmk_to - lmk_from

"""##### Panorama dos pontos

Fonte: [MediaPipe - Pose Landmark](https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker)

<div align="center">

![MP](https://ai.google.dev/static/edge/mediapipe/images/solutions/pose_landmarks_index.png)
</div>
"""

# 0 - nose
# 1 - left eye (inner)
# 2 - left eye
# 3 - left eye (outer)
# 4 - right eye (inner)
# 5 - right eye
# 6 - right eye (outer)
# 7 - left ear
# 8 - right ear
# 9 - mouth (left)
# 10 - mouth (right)
# 11 - left shoulder
# 12 - right shoulder
# 13 - left elbow
# 14 - right elbow
# 15 - left wrist
# 16 - right wrist
# 17 - left pinky
# 18 - right pinky
# 19 - left index
# 20 - right index
# 21 - left thumb
# 22 - right thumb
# 23 - left hip
# 24 - right hip
# 25 - left knee
# 26 - right knee
# 27 - left ankle
# 28 - right ankle
# 29 - left heel
# 30 - right heel
# 31 - left foot index
# 32 - right foot index

"""#### Pose classification"""

class PoseSample(object):

  def __init__(self, name, landmarks, class_name, embedding):
    self.name = name
    self.landmarks = landmarks
    self.class_name = class_name

    self.embedding = embedding


class PoseSampleOutlier(object):

  def __init__(self, sample, detected_class, all_classes):
    self.sample = sample
    self.detected_class = detected_class
    self.all_classes = all_classes

class PoseClassifier(object):
  """Classifies pose landmarks."""

  def __init__(self,
               pose_samples_folder,
               pose_embedder,
               file_extension='csv',
               file_separator=',',
               n_landmarks=33,
               n_dimensions=3,
               top_n_by_max_distance=30,
               top_n_by_mean_distance=10,
               axes_weights=(1., 1., 0.2),
               min_dist=5.0):
    self._pose_embedder = pose_embedder
    self._n_landmarks = n_landmarks
    self._n_dimensions = n_dimensions
    self._top_n_by_max_distance = top_n_by_max_distance
    self._top_n_by_mean_distance = top_n_by_mean_distance
    self._axes_weights = axes_weights
    self.min_dist = min_dist

    self._pose_samples = self._load_pose_samples(pose_samples_folder,
                                                 file_extension,
                                                 file_separator,
                                                 n_landmarks,
                                                 n_dimensions,
                                                 pose_embedder)

  def _load_pose_samples(self,
                         pose_samples_folder,
                         file_extension,
                         file_separator,
                         n_landmarks,
                         n_dimensions,
                         pose_embedder):
    """Loads pose samples from a given folder.

    Required CSV structure:
      sample_00001,x1,y1,z1,x2,y2,z2,....
      sample_00002,x1,y1,z1,x2,y2,z2,....
      ...
    """
    # Each file in the folder represents one pose class.
    file_names = [name for name in os.listdir(pose_samples_folder) if name.endswith(file_extension)]

    pose_samples = []
    for file_name in file_names:
      # Use file name as pose class name.
      class_name = file_name[:-(len(file_extension) + 1)]

      # Parse CSV.
      with open(os.path.join(pose_samples_folder, file_name)) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=file_separator)
        for row in csv_reader:
          assert len(row) == n_landmarks * n_dimensions + 1, 'Wrong number of values: {}'.format(len(row))
          landmarks = np.array(row[1:], np.float32).reshape([n_landmarks, n_dimensions])
          pose_samples.append(PoseSample(
              name=row[0],
              landmarks=landmarks,
              class_name=class_name,
              embedding=pose_embedder(landmarks),
          ))

    return pose_samples


  def __call__(self, pose_landmarks, target_classes = None):
    # Check that provided and target poses have the same shape.
    assert pose_landmarks.shape == (self._n_landmarks, self._n_dimensions), 'Unexpected shape: {}'.format(pose_landmarks.shape)

    # Get given pose embedding.
    pose_embedding = self._pose_embedder(pose_landmarks)
    flipped_pose_embedding = self._pose_embedder(pose_landmarks * np.array([-1, 1, 1]))

    if target_classes is not None:
      pose_samples = [sample for sample in self._pose_samples if sample.class_name in target_classes]
    else:
      pose_samples = self._pose_samples

    # Filter by max distance.
    #
    # That helps to remove outliers - poses that are almost the same as the
    # given one, but has one joint bent into another direction and actually
    # represnt a different pose class.

    max_dist_heap = []
    for sample_idx, sample in enumerate(pose_samples):
      max_dist = min(
          np.max(np.abs(sample.embedding - pose_embedding) * self._axes_weights),
          np.max(np.abs(sample.embedding - flipped_pose_embedding) * self._axes_weights),
      )
      max_dist_heap.append([max_dist, sample_idx])

    max_dist_heap = sorted(max_dist_heap, key=lambda x: x[0])
    max_dist_heap = max_dist_heap[:self._top_n_by_max_distance]

    # Filter by mean distance.
    #
    # After removing outliers we can find the nearest pose by mean distance.
    mean_dist_heap = []
    diff_to = lambda x: np.abs(sample.embedding - x) * self._axes_weights
    for _, sample_idx in max_dist_heap:
      sample = pose_samples[sample_idx]
      # mean_dist = min(
      #     np.mean(np.abs(sample.embedding - pose_embedding) * self._axes_weights),
      #     np.mean(np.abs(sample.embedding - flipped_pose_embedding) * self._axes_weights),
      # )
      diff = min(diff_to(pose_embedding), diff_to(flipped_pose_embedding), key=np.mean)
      mean_dist = np.mean(diff)
      if mean_dist <= self.min_dist:
        mean_dist_heap.append([mean_dist, sample_idx, diff])

    mean_dist_heap = sorted(mean_dist_heap, key=lambda x: x[0])
    mean_dist_heap = mean_dist_heap[:self._top_n_by_mean_distance]

    # Collect results into map: (class_name -> n_samples)
    # class_names = [self._pose_samples[sample_idx].class_name for _, sample_idx in mean_dist_heap]
    class_dicts = [{"class":pose_samples[sample_idx].class_name,"mean_dist":mean_dist,"diff":diff} for mean_dist, sample_idx, diff in mean_dist_heap]
    if len(class_dicts) > 0:
      class_names = [d["class"] for d in class_dicts]
      for cd in class_dicts:
        cd["count"] = class_names.count(cd["class"])
      result = min([cd for cd in class_dicts if cd["count"] == max([cd["count"] for cd in class_dicts])], key=lambda cd: cd["mean_dist"])
    else:
      result = {"class": "no_class"}

    return result

"""#### Repetition counter"""

class RepetitionCounter(object):
  """Counts number of repetitions of given target pose class."""

  def __init__(self, class_name, enter_threshold=6, exit_threshold=4):
    self._class_name = class_name

    # If pose counter passes given threshold, then we enter the pose.
    self._enter_threshold = enter_threshold
    self._exit_threshold = exit_threshold

    # Either we are in given pose or not.
    self._pose_entered = False

    # Number of times we exited the pose.
    self._n_repeats = 0

  @property
  def n_repeats(self):
    return self._n_repeats

  def __call__(self, pose_classification):
    # Get pose confidence.
    pose_confidence = 0.0
    if self._class_name in pose_classification["class"]:
      pose_confidence = pose_classification["count"]

    # On the very first frame or if we were out of the pose, just check if we
    # entered it on this frame and update the state.
    if not self._pose_entered:
      self._pose_entered = pose_confidence > self._enter_threshold
      return self._n_repeats

    # If we were in the pose and are exiting it, then increase the counter and
    # update the state.
    if pose_confidence < self._exit_threshold:
      self._n_repeats += 1
      self._pose_entered = False

    return self._n_repeats

"""#### Classification visualizer"""

class PoseClassificationVisualizer(object):
  """Keeps track of claassifcations for every frame and renders them."""

  def __init__(self,
               class_name,
               plot_location_x=0.05,
               plot_location_y=0.05,
               plot_max_width=0.4,
               plot_max_height=0.4,
               plot_figsize=(9, 4),
               plot_x_max=None,
               plot_y_max=None,
               counter_location_x=0.85,
               counter_location_y=0.05,
               counter_font_path='https://github.com/googlefonts/roboto/blob/main/src/hinted/Roboto-Regular.ttf?raw=true',
               counter_font_color='red',
               counter_font_size=0.15):
    self._class_name = class_name
    self._plot_location_x = plot_location_x
    self._plot_location_y = plot_location_y
    self._plot_max_width = plot_max_width
    self._plot_max_height = plot_max_height
    self._plot_figsize = plot_figsize
    self._plot_x_max = plot_x_max
    self._plot_y_max = plot_y_max
    self._counter_location_x = counter_location_x
    self._counter_location_y = counter_location_y
    self._counter_font_path = counter_font_path
    self._counter_font_color = counter_font_color
    self._counter_font_size = counter_font_size

    self._counter_font = None

    self._pose_classification_history = []
    self._pose_classification_filtered_history = []

  def __call__(self,
               frame,
               pose_classification,
               repetitions_count):
    """Renders pose classifcation and counter until given frame."""
    # Extend classification history.
    self._pose_classification_history.append(pose_classification)

    # Output frame with classification plot and counter.
    output_img = Image.fromarray(frame)

    output_width = output_img.size[0]
    output_height = output_img.size[1]

    # Draw the count.
    output_img_draw = ImageDraw.Draw(output_img)
    if self._counter_font is None:
      font_size = int(output_height * self._counter_font_size)
      font_request = requests.get(self._counter_font_path, allow_redirects=True)
      self._counter_font = ImageFont.truetype(io.BytesIO(font_request.content), size=font_size)
    output_img_draw.text((output_width * self._counter_location_x,
                          output_height * self._counter_location_y),
                         str(repetitions_count),
                         font=self._counter_font,
                         fill=self._counter_font_color)

    return output_img

"""#### Exceções"""

class NegativeFramesToConsider(Exception):
    """Exception raised when the frames to consider are negative"""

    def __init__(self,context):
        super().__init__(f"negatives frame to consider in: {context}")

class FrameCantBeFound(Exception):
    """Exception raised when no frame in a sequence of frames implies a movement"""

    def __init__(self,context):
        super().__init__(f"no frames found in: {context}")



class EmptyMovementList(Exception):
    """Exception raised when no movement is present in an action"""

    def __init__(self, context):
        super().__init__(f"tried to verify an empty movement list in: {context}")

class LessFramesThanMovements(Exception):
    """Exception raised when the df has less frames than ammount of movements"""

    def __init__(self, context):
        super().__init__(f"less frames than movements in: {context}")

class EmptyArr(Exception):
    """Exception raised when the arr is empty"""

    def __init__(self,context):
        super().__init__(f"empty arr in: {context}")

"""#### Movement"""

class Movement():
    def __init__(self, name="",feedback="", frames_to_consider = 0, label = ""):
        self._frames_to_consider = frames_to_consider
        self._name = name
        self._feedback = feedback
        self._recognised = False
        self.label = label

    def get_name(self):
        """
        getter
        """
        return self._name

    def get_feedback(self):
        """
        getter
        """
        return self._feedback

    def frames_to_consider(self):
        """
        getter
        """
        return self._frames_to_consider

    def validated(self):
        """
        getter
        """
        return self._recognised


    def verify(self,classification):
      self._recognised = True
      self._feedback = "O movimento está a uma distância de {} unidades do esperado".format(classification["mean_dist"])

"""#### Action"""

class Action():
    def __init__(self,movements=[],name="action is not named", pose_classifier = None, label = ""):
        self._movements = movements
        self._recognised = False
        self._name = name
        self.pose_classifier = pose_classifier
        self.classification_per_frame = []
        self.label = label

    def get_name(self):
        """
        getter
        """
        return self._name

    def _empty_movement_list(self):
        """
        querier
        """
        return len(self._movements) == 0

    def add_movement(self, movement):
        """
        setter
        """
        self._movements.append(movement)

    def rename(self,new_name):
        """
        setter
        """
        if not new_name:
            # check if string is empty, pythonic
            raise ValueError('empty string')
        self._name = new_name


    def remove_movement(self, movement_number=None):
        """
        removes a movement from the movement list.
        if no movement_number is provided removes the last one
        """
        if self._empty_movement_list():
            raise EmptyMovementList(f"{self._name}.remove_movement")

        if movement_number is not None:
            self._movements.pop(movement_number)

        else:
            self._movements.pop()

    def movements(self):
        """
        getter
        """
        return self._movements

    def validated(self):
        """
        getter
        """
        return self._recognised


    def verify(self, landmark_arr):

      classification_per_frame = []
      for landmark in landmark_arr:
        if landmark is not None:
          pose_classification = self.pose_classifier(landmark, [mv.get_name() for mv in self._movements])
        else:
          pose_classification = None
        classification_per_frame.append(pose_classification)

      self.classification_per_frame = classification_per_frame
      self._recognised = True
      for movement in self._movements:
        for classification in classification_per_frame:
          if movement.get_name() in classification["class"]:
            movement.verify(classification)
            break

"""#### Coach"""

class Coach():
    def __init__(self, actions, sport_name, proc_video_path, output_path):
        """
        Inicializa o Coach.
        :param actions: Lista de ações (Action)
        :param sport_name: Nome do esporte
        :param proc_video_path: Caminho do vídeo processado
        :param output_path: Caminho dos arquivos de saída
        """
        self.actions = actions
        self.sport_name = sport_name
        self.proc_video_path = proc_video_path
        self.output_path = output_path
        self.landmarks_arr = None  # Inicializa o array como None

    def update_landmarks(self, landmarks_arr):
        self.landmarks_arr = landmarks_arr

    def get_action_labels(self):
        """Retorna a lista de rótulos das ações que o Coach pode orientar."""
        return [action.label for action in self.actions]

    def process_action(self, action_id):
        """
        Executa a verificação de uma ação específica.
        :param action_id: Índice da ação na lista de actions
        """
        if self.landmarks_arr is None:
            raise ValueError("O vídeo ainda não foi processado.")

        if action_id < 0 or action_id >= len(self.actions):
            raise ValueError("ID da ação inválido.")

        action = self.actions[action_id]
        action.verify(self.landmarks_arr)  # Chama o método de verificação da Action

    def generate_feedback(self, action_id):
        """
        Cria um arquivo de feedback no caminho de saída.
        """
        # feedback_text = "Feedback gerado com sucesso!"  # Placeholder
        action = self.actions[action_id]
        feedback_text = f"Ação: {action.label}\n"
        for movement in action.movements():
            feedback_text += f"  Movimento: {movement.label}\n"
            feedback_text += f"    Feedback: {movement.get_feedback()}\n"

        feedback_path = os.path.join(self.output_path, "feedback.txt")

        with open(feedback_path, "w") as f:
            f.write(feedback_text)

        # Verificar se o arquivo foi salvo corretamente
        if os.path.exists(feedback_path):
            print(f"Feedback salvo em: {feedback_path}")
        else:
            print("Erro: O feedback não foi gerado corretamente!")

        chosen_moviment = action.movements()[0]
        print("Contabilizando em vídeo o movimento", chosen_moviment.label)
        video_with_counter(chosen_moviment.get_name(), action.classification_per_frame)
        print("\nVídeo salvo em", output_video_path)

        return feedback_path

"""## Base de referências"""

from_drive = True

if from_drive:
  !gdown 1GQd6IZJXg61RpyYxj93CjKw31hzNuJIR
  zf = zipfile.ZipFile(reference_csvs_f+".zip", "r")

else:
  uploaded = files.upload()
  file_name = next(iter(uploaded))
  zf = zipfile.ZipFile(io.BytesIO(uploaded[file_name]), "r")

zf.extractall()

if reference_csvs_f not in os.listdir('.'):
  print("\nMaking csvs\n")
  expected_folder = file_name[:-len(".zip")]
  assert expected_folder in os.listdir('.'), 'Error: the zip file and its folder must have the same name {}'.format(expected_folder)
  make_reference_csvs(expected_folder, reference_csvs_f)

"""## Inicializações

#### Classifier e Embedder
"""

pose_embedder = FullBodyPoseEmbedder()

pose_classifier = PoseClassifier(
    pose_samples_folder=reference_csvs_f,
    pose_embedder=pose_embedder,
    top_n_by_max_distance=30,
    top_n_by_mean_distance=1,
    min_dist=3.0)

"""#### Opções de Movement"""

def create_Movement(movement_name):

  file_names = [name for name in os.listdir(reference_csvs_f) if name.endswith("csv")]
  movements_available = []
  for file_name in file_names:
    # Use file name as pose class name.
    movements_available.append(file_name[:-(len(".csv"))])

  if movement_name not in movements_available:
    raise ValueError("Movement has no reference")

  else:

    if movement_name == "prepare_boost":
      return Movement(name=movement_name, frames_to_consider=1, label="Preparação do Impulso")

    else:
      raise ValueError("Undefined Movement")

"""#### Opções de Action"""

def create_Action(action_name):

  if action_name == "push_on":
    return Action(name=action_name, label="Remada", pose_classifier=pose_classifier, movements=[create_Movement("prepare_boost")])

  else:
    raise ValueError("Undefined Action")

"""#### Opções de Coach"""

def create_Coach(sport_name):

  if sport_name == "skate":
    return Coach(sport_name=sport_name, actions=[create_Action("push_on")], proc_video_path=proc_video_path, output_path=output_f)

  else:
    raise ValueError("Undefined Sport")

"""## Upload do vídeo"""

# Commented out IPython magic to ensure Python compatibility.
reset_folder(vb_f)
# %cd $vb_f
uploaded = files.upload()
file_name = next(iter(uploaded))
os.rename(file_name, video_name)
# %cd ..

"""## Processamento do vídeo"""

reset_folder(proc_f)

video_cap = cv2.VideoCapture(video_path)
# Get some video parameters to generate output video with classificaiton.
video_n_frames = video_cap.get(cv2.CAP_PROP_FRAME_COUNT)
video_fps = video_cap.get(cv2.CAP_PROP_FPS)
video_width = int(video_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
video_height = int(video_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

pose_tracker = mp_pose.Pose()
proc_video = cv2.VideoWriter(proc_video_path, cv2.VideoWriter_fourcc(*'mp4v'), video_fps, (video_width, video_height))
landmarks_per_frame = []

with tqdm.tqdm(total=video_n_frames, position=0, leave=True) as pbar:
  while True:
    # Get next frame of the video.
    success, input_frame = video_cap.read()
    if not success:
      break
    pose_landmarks, output_frame = get_frame_landmarks(input_frame, pose_tracker)
    landmarks_per_frame.append(pose_landmarks)
    proc_video.write(cv2.cvtColor(np.array(output_frame), cv2.COLOR_RGB2BGR))
    pbar.update()

# Close output video.
proc_video.release()
# Release MediaPipe resources.
pose_tracker.close()

video_cap.release()

"""## Teste de execução única"""

sport_name = "skate"

skatecoach = create_Coach(sport_name)
skatecoach.update_landmarks(landmarks_per_frame)

print("Ações disponíveis:", skatecoach.get_action_labels())

action_id = 0
skatecoach.process_action(action_id)
reset_folder(output_f)
skatecoach.generate_feedback(action_id)