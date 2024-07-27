from api.dependencyinjector import global_injector
from api.arahlauncher import create_app

app = create_app(global_injector)