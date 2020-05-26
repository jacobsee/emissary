from git import Repo
import os
import schedule


def configure_repository(repository):
    if not os.path.exists("tmp"):
        os.makedirs("tmp")
    repo_directory = f"tmp/{repository['name']}"
    if not os.path.exists(repo_directory):
        os.makedirs(repo_directory)
        print(f"Cloning {repository['url']}...")
        repo = Repo.clone_from(repository["url"], repo_directory, branch="master")
        print(f"Cloned {repository['url']}")
    else:
        repo = Repo.init(repo_directory)
        repo.remotes.origin.pull()

    schedule.every(1).minutes.do(__wrap_repo_pull(repo))
    print(f"Configured scheduler for pulling repository {repository['name']}")


def __wrap_repo_pull(repo):

    def pull():
        repo.remotes.origin.pull()

    return pull
