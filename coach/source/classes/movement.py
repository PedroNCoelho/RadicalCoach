
class Movement():
    def __init__(self, name="",feedback="(Não foi gerado feedback)", frames_to_consider = 0, label = ""):
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


    def verify(self,classification, frame_num):
      self._recognised = True
      self._feedback = "Movimento executado corretamente no instante {:.1f}s!\n".format(frame_num/30.)
    #   self._feedback = "Movimento reconhecido no frame {}\n".format(frame_num)
    #   self._feedback += "O movimento está a uma distância de {} unidades do esperado\n".format(classification["mean_dist"])
