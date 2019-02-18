from .version import __version__

# shortcuts
from .algorithm.manager import AlgorithmBuilder
from .pipeline.create import PipelineBuilder
from .pipeline.exec import PipelineExecutor
from .pipeline.tracker import TrackerType


name = "hkube_notebook"
