from scoreinterface import ScoreInterface
from efficientnet.keras import EfficientNetB4
from efficientnet.keras import preprocess_input


class Scoring(ScoreInterface):
    def __init__(self):
        super(Scoring, self).__init__()
        self.model = EfficientNetB4(weights='imagenet')

    def predict(self, batch, explain=False):
        return self.model.predict(batch)

    def get_target_size(self):
        return (380, 380)

    def get_input_preprocessor(self):
        return preprocess_input

