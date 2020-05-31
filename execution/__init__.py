import tempfile
import shutil
import importlib
import threading
import os
from execution.cd import cd
from threading import Lock


def initialize(task):
    for step in task["steps"]:
        plugin = importlib.import_module('execution.plugins.' + step["plugin"])
        if hasattr(plugin, "initialize") and callable(plugin.initialize):
            print(f"Initializing plugin {step['plugin']}")
            if "repository" in step and "path" in step and os.path.isdir(step["repository"] + "/" + step["path"]):
                with cd(step["repository"] + "/" + step["path"]):
                    plugin.initialize(step["params"])
            elif "repository" in step and os.path.isdir(step["repository"]):
                with cd(step["repository"]):
                    plugin.initialize(step["params"])
            else:
                plugin.initialize(step["params"])


def build_task(task):

    @multithread
    @lock
    @handle_errors(task)
    def task_function(params={}, context={}):
        with tempfile.TemporaryDirectory() as temp_dir:
            required_repositories = {step["repository"] for step in task["steps"] if "repository" in step}
            for repository in required_repositories:
                shutil.copytree("tmp/" + repository, temp_dir + "/" + repository)
            with cd(temp_dir):
                for step in task["steps"]:
                    # Load necessary execution plugin
                    plugin = importlib.import_module('execution.plugins.' + step["plugin"])
                    # Construct actual params (params from config file + runtime-set params taking precedent)
                    constructed_params = {}
                    if "params" in step:
                        constructed_params.update(step["params"])
                    constructed_params.update(params)
                    # Set runtime directory properly for the step to execute
                    if "repository" in step and "path" in step:
                        with cd(step["repository"] + "/" + step["path"]):
                            result = plugin.process(context, constructed_params)
                    elif "repository" in step:
                        with cd(step["repository"]):
                            result = plugin.process(context, constructed_params)
                    else:
                        result = plugin.process(context, constructed_params)

                    if (isinstance(result, bool) and result is False) or (isinstance(result, dict) and result["pass"] is False):
                        print("Step has broken execution - halting task")
                        break

    return task_function


def multithread(fn):
    def run_threaded(*args, **kwargs):
        job_thread = threading.Thread(target=fn, args=args, kwargs=kwargs)
        job_thread.start()
    return run_threaded


def lock(fn):
    mutex = Lock()

    def locker(*args, **kwargs):
        if mutex.acquire(False):
            try:
                return fn(*args, **kwargs)
            finally:
                mutex.release()
        else:
            print("Task aborted - unable to acquire thread lock (is it already running?)")

    return locker


def handle_errors(task):

    if "disable_error_handling" in task and task["disable_error_handling"]:
        def handler(fn):
            def f(*args, **kwargs):
                fn(*args, **kwargs)
            return f
    else:
        def handler(fn):
            def f(*args, **kwargs):
                try:
                    fn(*args, **kwargs)
                except Exception as e:
                    print(f"ERROR EXECUTING TASK {task['name']}:")
                    print(str(e))

            return f
    return handler
