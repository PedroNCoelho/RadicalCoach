from ..libs import *

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