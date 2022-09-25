"""
from score.scoreinterface import ScoreInterface
import tensorflow.keras as keras


class Scoring(ScoreInterface):
    def __init__(self):
        super(Scoring, self).__init__()
        self.model = keras.applications.resnet.ResNet152()

    def predict(self, batch, explain=False):
        return self.model.predict(batch)

    def get_target_size(self):
        return (224, 224)

    def get_input_preprocessor(self):
        return keras.applications.resnet.preprocess_input
"""

from score.scoreinterface import ScoreInterface
from torchvision.models import resnet152, ResNet152_Weights


class Scoring(ScoreInterface):
    def __init__(self):
        super(Scoring, self).__init__()
        weights = ResNet152_Weights.DEFAULT
        self.model = resnet152(weights=weights)
        self.model.eval()

        self.preprocess = weights.transforms()

    def predict(self, batch, explain=False):
        return self.model(batch)

    def get_target_size(self):
        return (224, 224)

    def get_input_preprocessor(self):
        return self.preprocess
