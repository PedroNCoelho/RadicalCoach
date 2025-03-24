from .classes.pose_embedding import *
from .classes.coach import *


pose_embedder = FullBodyPoseEmbedder()

pose_classifier = PoseClassifier(
    pose_samples_folder=reference_csvs_f,
    pose_embedder=pose_embedder,
    top_n_by_max_distance=30,
    top_n_by_mean_distance=1,
    min_dist=3.0)



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



def create_Action(action_name):

  if action_name == "push_on":
    return Action(name=action_name, label="Remada", pose_classifier=pose_classifier, movements=[create_Movement("prepare_boost")])

  else:
    raise ValueError("Undefined Action")
  


def create_Coach(sport_name):

  if sport_name == "skate":
    return Coach(sport_name=sport_name, actions=[create_Action("push_on")], proc_video_path=proc_video_path, output_path=output_f)

  else:
    raise ValueError("Undefined Sport")


