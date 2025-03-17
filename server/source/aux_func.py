from .libs import *
from .classes.repetition_counter import *
from .classes.classification_visualizer import *

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



def find_gap_seq(seq, matches, gap_range):
  # ocl = [{'class': 'a'}, {'class': 'b'}, {'class': 'no_class'}, {'class': 'no_class'}, {'class': 'b'}, {'class': 'c'}, None, None, {'class': 'a'}, {'class': 'b'}, {'class': 'no_class'}, {'class': 'c'}, None, None]
  # cl = [d['class'] if d is not None else None for d in ocl]
  # print(cl)
  # matches = ['a', 'b', 'c']
  # gap_range = 3

  # zip_m = list(zip(matches, matches[1:]))
  indices = defaultdict(list)
  # possible_ids = defaultdict(list)
  for i, j in enumerate(seq):
      indices[j].append(i)
  # print(indices)

  possible_ids = [[ind] for ind in indices[matches[0]]]
  for matche in matches[1:]:
    up_possible_ids = []
    for id in indices[matche]:
      for p_ids in possible_ids:
        if 0 <= id - p_ids[-1] - 1 <= gap_range:
          up_possible_ids.append(p_ids + [id])
    possible_ids = up_possible_ids.copy()
  # print(possible_ids)
  return possible_ids


