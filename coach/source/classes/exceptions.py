
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

class FileNotReadableError(Exception):
    def __init__(self,context):
        super().__init__(f"tried to read a non readable file in {context}")