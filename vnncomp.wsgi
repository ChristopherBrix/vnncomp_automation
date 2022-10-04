import sys

sys.path.insert(0, '/var/www/html/vnncomp')
sys.path.insert(0, '/var/www/html/vnncomp/venv/lib/python3.8/site-packages')
from app.main import app as application
#from app.utils.task import Task, BenchmarkTask, ToolkitTask, TaskState, TaskType
#from app.utils.aws_instance import AwsInstance
import app.views, app.auth