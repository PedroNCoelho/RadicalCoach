from ..aux_func import *
from .exceptions import *
from .movement import *
from .pose_classification import *

class Action():
    def __init__(self,movements=[],name="action is not named", pose_classifier = None, label = "", delay_tolerance = 50):
        self._movements = movements
        self._recognised = False
        self._name = name
        self.pose_classifier = pose_classifier
        self.classification_per_frame = []
        self.label = label
        self.delay_tolerance = delay_tolerance
        self.feedback = "(Não foi gerado feedback)"

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

      mv_names = [mv.get_name() for mv in self._movements]

      classification_per_frame = []
      for i, landmark in enumerate(landmark_arr):
        if landmark is not None:
          pose_classification = self.pose_classifier(landmark, mv_names)
        else:
          pose_classification = None
        # print("FRAME", i,":\n", pose_classification)
        classification_per_frame.append(pose_classification)
      self.classification_per_frame = classification_per_frame

      detected_classes = [d['class'] if d is not None else None for d in classification_per_frame]
      # print(detected_classes)
      action_frames = find_gap_seq(detected_classes, mv_names, self.delay_tolerance)
      # print(action_frames)
      if len(action_frames) > 0:
        # self.feedback = "Ação reconhecida com sucesso {} vez(es)!".format(len(action_frames))
        self.feedback = "Ação realizada com sucesso!"
        self._recognised = True
        for i, movement in enumerate(self._movements):
          frame_num = action_frames[0][i]
          movement.verify(classification_per_frame[frame_num], frame_num)
      else:
        self.feedback = "Ação não reconhecida..."
        self._recognised = False
        for i, movement in enumerate(self._movements):
          if mv_names[i] in detected_classes:
            frame_num = detected_classes.index(mv_names[i])
            movement.verify(classification_per_frame[frame_num], frame_num)
          else:
            movement.not_recognised()