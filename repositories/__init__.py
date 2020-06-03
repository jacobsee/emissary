from git import Repo, Git
import os
import schedule


def configure_repository(repository):
    if not os.path.exists("tmp"):
        os.makedirs("tmp")
    repo_directory = f"tmp/{repository['name']}"

    if "pull_secret" in repository and not repository["url"].startswith("http"):
        env = {
            "GIT_SSH_COMMAND": generate_ssh_command(repository)
        }
    else:
        env = {}

    if not os.path.exists(repo_directory):
        os.makedirs(repo_directory)
        print(f"Cloning {repository['url']}...")
        repo = Repo.clone_from(repository["url"], repo_directory, branch="master", env=env)
        print(f"Cloned {repository['url']}")
    else:
        repo = Repo.init(repo_directory)
        repo.remotes.origin.pull(env=env)

    schedule.every(2).minutes.do(__wrap_repo_pull(repo, env))
    print(f"Configured scheduler for pulling repository {repository['name']}")


def generate_ssh_command(repository):
    if "from_file" in repository["pull_secret"]:
        git_ssh_identity_file = os.path.expanduser(repository["pull_secret"]["from_file"])
        return f"ssh -o 'StrictHostKeyChecking=no' -i {git_ssh_identity_file}"
    else:
        raise Exception("Git pull secret method not recognized.")


def __wrap_repo_pull(repo, env):

    def pull():
        repo.remotes.origin.pull(env=env)

    return pull
