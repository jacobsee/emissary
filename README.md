# TODO: Write a good README

This is a workflow engine for integrating systems by acting as a higher-order automation and triggering system around existing tools and scripts.

## Currently supports 

Triggering:
* Scheduled
* Webhook

Plugins:
* Ansible
* Python scripting

## Coming next

Plugins:
* Read/write of Kubernetes objects in-cluster

## Repository Support

Resources are fetched from git repositories as-needed and do not need to be bundled in with this system.

## Example Workflow

```yaml
repositories:
  - name: gitlab-to-argo-repo
    url: https://github.com/jacobsee/gitlab_to_argo.git

tasks:
  - name: gitlab-to-argo
    description: Ensures that all repositories in a GitLab group are being watched by an Argo CD instance
    triggers:
      - type: scheduled
        every: 10 seconds
      - type: scheduled
        every: thursday
        at: "15:30"
      - type: webhook
        route: /do_stuff
    steps:
      - plugin: ansible
        repository: gitlab-to-argo-repo
        params:
          playbook_path: site.yml
          inventory_path: inventory
          extra_vars:
            gitlab_base_url: https://gitlab.com
            gitlab_group: 1234
            gitlab_private_token: ABCDEFABCDEFABCDEF
      - plugin: script
        repository: gitlab-to-argo-repo
        path: output
        params:
          script: |
            from os import listdir
            files = [f for f in listdir(".")]
            print("We're inside of a script now!")
            print("Found the following files in the output dir of the repository:")
            print(files)
      - plugin: kubernetes
        repository: gitlab-to-argo-repo
        path: output
        params:
          mode: in-cluster
          apply_objects:
            from_dir: "."
```