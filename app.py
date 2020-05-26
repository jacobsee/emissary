from configuration import get_config
from repositories import configure_repository
from execution import build_task
from triggering import configure_triggers, start


def main():
    config = get_config()

    for repository in config["repositories"]:
        configure_repository(repository)

    for task in config["tasks"]:
        task_function = build_task(task)
        configure_triggers(task, task_function)

    start()


if __name__ == "__main__":
    main()
