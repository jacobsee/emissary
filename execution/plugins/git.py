import os
from execution.cd import cd
from repositories import generate_ssh_command
from git import Repo


def process(context, params):
    if "action" not in params:
        raise Exception("Git plugin requires `action` to be set as a parameter.")
    if "directory" in params and os.path.exists(params["directory"]):
        with cd(params["directory"]):
            run_action(params)
    else:
        run_action(params)


def run_action(params):
    repo_directory = params["directory"] if "directory" in params else "."
    branch = params["branch"] if "branch" in params else "master"
    message = params["message"] if "message" in params else "Commit message"
    author_name = params["author_name"] if "author_name" in params else "Automated Tool"
    author_email = params["author_email"] if "author_email" in params else "email@email.com"
    url = params["url"] if "url" in params else None

    if "pull_secret" in params and url and not url.startswith("http"):
        env = {
            "GIT_SSH_COMMAND": generate_ssh_command(params)
        }
    else:
        env = {}

    if params["action"] == "clone" or params["action"] == "pull":
        repo = fetch(url, repo_directory, branch, env)
    elif params["action"] == "commit-all-changes":
        repo = add_all()
        commit(repo, message, f"{author_name} <{author_email}>")


def fetch(url, repo_directory, branch, env={}):
    if not os.path.exists(repo_directory):
        os.makedirs(repo_directory)
        print(f"Cloning {url}...")
        repo = Repo.clone_from(url, repo_directory, branch=branch, env=env)
        print(f"Cloned {url}")
    else:
        repo = Repo.init(repo_directory)
        repo.remotes.origin.pull(env=env)
    return repo


def add_all():
    repo = Repo.init(".")
    repo.git.add(all=True)
    print("All files added")
    return repo


def commit(repo, message, author):
    repo.git.commit('-m', message, author=author)
    print("Committed to repository")
