# Emissary [working title]

A higher-order workflow composition and triggering mechanism designed to take advantage of existing tools and scripts.

<hr>

* [How Does It Work?](#hdiw)
* [Configuration](#config)
  * [Introduction](#config-introduction)
  * [Repositories](#config-repositories)
  * [Triggers](#config-triggers)
  * [Steps & Parameters](#config-steps-parameters)
  * [Context](#config-context)
  * [Concurrency](#config-concurrency)
* [Available Plugins](#plugins)
  * [Ansible](#plugins-ansible)
  * [Kubernetes](#plugins-kubernetes)
  * [Script](#plugins-script)
* [Deployment](#deployment)

### <a name="hdiw"></a>How Does It Work?

It would be helpful to think of this tool as a _workflow orchestrator_.

It takes a single configuration file containing:

* A number of tasks
* A list of repositories that those tasks depend on
* A set of triggers defining when those tasks should be run

Here is simple workflow demonstrating all of these things:

```yaml
repositories:
  - name: automation-repo
    url: https://github.com/my-org/some-ansible-playbooks.git

tasks:
  - name: Run my Ansible playbook
    description: Runs an Ansible playbook under a number of trigger scenarios
    triggers:
      - type: scheduled
        every: 2 hours
      - type: scheduled
        every: thursday
        at: "15:30"
      - type: webhook
        route: /do_a_thing
    steps:
      - plugin: ansible
        repository: automation-repo
        params:
          playbook_path: site.yml
          inventory_path: inventory
```

In this case, we have pulled in one repository (`https://github.com/my-org/some-ansible-playbooks.git`) and scheduled a task which executes a playbook in that repository every 2 hours, every Thursday at 3:30PM, and every time a webhook at the route `/do_a_thing` is called by some other service.

> :exclamation: **There is _no filesystem persistence_ between task executions!** Each execution runs in an environment representative of a fresh clone of the Git repository, even if previous executions have written/modified/deleted any files.

This is a very simple example of a task definition. We'll see later in this document how task definitions can be used to string together more complicated logic.

### <a name="config"></a>Configuration

#### <a name="config-introduction"></a>Introduction

The configuration YAML file described in surrounding sections should be somewhere on the filesystem accessible by the Python application. If you are running this application standalone, you will need to set the environment variable `CONFIG_FILE` to the path of the config file to use.

If you use the included Helm chart to deploy to an OpenShift cluster and supply a `ConfigMap` containing a `config.yml` key, you do not have to worry about this.

#### <a name="config-repositories"></a>Repositories

Unless you compose task workflow entirely out of plugins with inline configuration/scripts, you will likely need to pull in existing resources to accomplish your goals, for example: an Ansible playbook & inventory are required to use the Ansible plugin.

These repositories are defined in the config file like this:

```yaml
repositories:
  - name: automation-repo-1
    url: https://github.com/my-org/some-ansible-playbooks.git
  - name: automation-repo-2
    url: https://github.com/my-org/some-ansible-playbooks-2.git
```

Upon application startup, these repositories are cloned. They can be referenced from that point forward by their name as defined here, _not_ by any part of their Git URL.

**The same scheduling mechanism used to trigger tasks is _automatically configured_ to pull new changes from these repositories every two minutes, so updates to these dependencies should be picked up _without any user intervention required_.**

TODO: Private repository support & documentation

#### <a name="config-triggers"></a>Triggers

All tasks definitions require a `triggers` block, else the task would never be able to execute and thus the definition would be useless. Multiple triggers can be defined for the same task. Two kinds of triggers are currently supported: Schedule, and Webhook.

##### Schedule

Schedule triggers execute a task periodically based on a time condition, and can take a number of forms:

```yaml
tasks:
  ...
    triggers:
      - type: scheduled
        every: minute
```

```yaml
tasks:
  ...
    triggers:
      - type: scheduled
        every: 3 hours
```

```yaml
tasks:
  ...
    triggers:
      - type: scheduled
        every: thursday
        at: "15:30"
```

The following interval keywords are available to use in the `every` statement:


* second
* seconds
* minute
* minutes
* hour
* hours
* day
* days
* week
* weeks
* monday
* tuesday
* wednesday
* thursday
* friday
* saturday
* sunday

##### Webhook

Webhook triggers configure the app to listen for a `GET` request on a certain route. Whenever a request is encountered, the task is run. For example:
 
```yaml
tasks:
  ...
    triggers:
      - type: webhook
        route: /run_task_x
``` 
 
Webhook triggers allow for slightly more advanced execution, in that **webhook-triggered tasks can receive external inputs**. Any URL parameters received as a part of a webhook call are parsed and added to the _task execution context_. 

Ex. `https://my-app-url/run_task_x?param1=stuff&param2=things`

See [context](#configuration-context) below.

> :exclamation: **The internal webserver is only started if at least one task defines a webhook trigger.** If no tasks have a webhook trigger defined, server initialization is skipped entirely.

#### <a name="config-steps-parameters"></a>Steps & Parameters

Each task is made up of at least one _step_. A step is an individual invocation of a plugin with certain parameters. 

Step definitions almost always make use of a `params` input to tell them what to do:

```yaml
tasks:
  ...
    steps:
      - plugin: script
        params:
          script: |
            from os import listdir
            listdir(".")
```

However, note that steps may also make use of the [_context_](#config-context) as input.

If a step does not specify a `repository`, it is run in a working directory with _every repository_ available to it. For example, the task defined by the above YAML, with the following repository definition in the config file:

```yaml
repositories:
  - name: automation-repo-1
    url: https://github.com/my-org/some-ansible-playbooks.git
  - name: automation-repo-2
    url: https://github.com/my-org/some-ansible-playbooks-2.git
```

Would see a directory structure like this:

```text
<current working directory>
├── automation-repo-1
│   ├── repo-file-1
│   ├── repo-file-2
├── automation-repo-2
│   ├── repo-file-1
│   ├── repo-file-2
```

<hr>

However, a step _scoped_ to a certain repository: 

```yaml
tasks:
  ...
    steps:
      - plugin: script
        repository: automation-repo-2
        params:
          script: |
            from os import listdir
            listdir(".")
```

Would be executed inside of that repository directory:

```text
<current working directory (inside automation-repo-2)>
├── repo-file-1
├── repo-file-2
```

Steps may also make use of an additional `path` input to scope the execution of that step to a subdirectory of the repository: 

```yaml
tasks:
  ...
    steps:
      - plugin: script
        repository: automation-repo-2
        path: some-subdirectory
        params:
          script: |
            from os import listdir
            listdir(".")
```

#### <a name="config-context"></a>Context

Each step in a task run occurs with one single, mutable _context_. The context is initialized as empty at the start of a task run, unless the task is triggered from a webhook with parameters - in which case, the context is initialized with those parameters. 

It is up to each individual plugin how the context should be used, and whether it is writable in any way, or read-only. The context is the only way (aside from writing to the filesystem) for a step to pass data to later steps.

Some examples of using context:

```yaml
tasks:
  - name: test
    triggers:
      - type: webhook
        route: /test
    steps:
      - plugin: script
        params:
          script: |
            context["stuff"] = "setting a context var"
      - plugin: script
        params:
          script: |
            print(f"The previous step told me: {context['stuff']}")
```

or:

```yaml
tasks:
  - name: test
    triggers:
      - type: webhook
        route: /test
    steps:
      - plugin: script
        params:
          script: |
            print(f"The webhook told me: {context['stuff']}")
```

```shell script
curl http://this-app/test?stuff=context_data
```

or:

```yaml
tasks:
  - name: test
    triggers:
      - type: webhook
        route: /test
    steps:
      - plugin: script
        params:
          script: |
            context["var_one"] = "input to an Ansible playbook"
      - plugin: ansible
        repository: automation-repo
        params:
          playbook_path: site.yml
          inventory_path: inventory
          extra_vars:
            # note that var_one is not defined here
            var_two: stuff
```

(since the `ansible` plugin automatically imports context vars as extra vars if they're not overridden by an explicit declaration in `extra_vars`)

#### <a name="config-Concurrency"></a>Concurrency

Two different tasks are able to run concurrently without interfering with each other (even if they depend on the same repositories).

Multiple runs of _the same task_ are not currently allowed, since this is probably undesirable. If a task is running and a second execution of that task is queued by the scheduler or by a webhook call, the second execution is immediately terminated (with a warning in the console) and no plugins are executed.

TODO: Make this configurable per-task since it's not really a technical limitation at all.

### <a name="plugins"></a>Plugins

#### <a name="plugins-ansiblet"></a>Ansible

#### <a name="plugins-kubernetes"></a>Kubernetes

#### <a name="plugins-script"></a>Script

### <a name="deployment"></a>Deployment

This is fundamentally just a Python project that versions dependencies in `Pipenv` & `Pipenv.lock` files. Any system that can run projects using Pipenv should be able to run this application. That said, there is a Helm chart available to get up and running quickly on OpenShift.

The Helm chart is available in `/helm` and has a few input parameters:

| Parameter | Description | Default |
|---|---|---|
| `setupConfigMap` | Create a ConfigMap which contains a workflow definition file. Requires `configFileContents` to also be set. | `false` |
| `configFileContents` | The contents of the config file for `setupConfigMap` to create. | `""` |
| `configMapName` | The pre-existing ConfigMap to use (if you don't use `setupConfigMap`) | `emissary-config` |
| `giveClusterAdmin` | Setup a `ClusterRoleBinding` giving the deployment `cluster-admin` privileges if you would like to use it to manage cluster resources. | `false` |
| `specifyServiceAccount` | If you don't want to use `giveClusterAdmin` but you _do_ want to specify your own service account to run as, enable this option. | `false` |
| `serviceAccount` | The service account to use if you've enabled `specifyServiceAccount` | `""` |

The Helm chart can be used as shown:

```shell script
cd helm
helm template my-deployment-name . | oc apply -f -
```

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