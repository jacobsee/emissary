# Steps & Parameters

Each task is made up of at least one _step_. A step is an individual invocation of a plugin with certain parameters.

## Configuration

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

However, note that steps may also make use of the task's [_context_](context.md) as input.

> :exclamation: **While there is filesystem persistence between steps in a task, there is _no filesystem persistence_ between separate task executions!** Each execution runs in an environment representative of a fresh clone of the Git repository, even if previous executions have written/modified/deleted any files.

## Repository Scoping

If a step does not specify a `repository`, it is run in a working directory with _every repository_ available to it. For example, the task defined by the above YAML spec, with the following repository definition in the config file:

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
