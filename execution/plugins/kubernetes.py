from kubernetes import client, config
from os import listdir, path
import yaml
import re


def initialize(params):
    if "mode" not in params:
        raise Exception("The Kubernetes plugin requires 'mode' to be set in the params.")
    load_config(params)


def process(context, params):
    if "apply_objects" in params:
        apply_objects(context, params)
    pass


def load_config(params):
    if params["mode"] == "in-cluster":
        try:
            config.load_incluster_config()
        except Exception as e:
            raise Exception(f"Unable to load in-cluster Kubernetes config: {e}")


def apply_objects(context, params):
    load_config(params)
    if "from_dir" in params["apply_objects"]:
        namespace = params["apply_objects"]["namespace"] if "namespace" in params["apply_objects"] else "default"
        yaml_dir = params["apply_objects"]["from_dir"]
        files = [f for f in listdir(yaml_dir) if f.endswith(".yml") or f.endswith(".yaml")]
        for file in files:
            with open(path.abspath(file)) as f:
                resource = yaml.load(f, Loader=yaml.FullLoader)
                create_from_dict(client, resource, verbose=True, namespace=namespace)


def create_from_dict(k8s_client, data, verbose=False, namespace='default', **kwargs):
    api_exceptions = []

    if "List" in data["kind"]:
        # This is a list type. iterate within its items
        kind = data["kind"].replace("List", "")
        for yml_object in data["items"]:
            # Mitigate cases when server returns a xxxList object
            # See kubernetes-client/python#586
            if kind != "":
                yml_object["apiVersion"] = data["apiVersion"]
                yml_object["kind"] = kind
            try:
                create_from_yaml_single_item(
                    k8s_client, yml_object, verbose, namespace=namespace,
                    **kwargs)
            except client.rest.ApiException as api_exception:
                api_exceptions.append(api_exception)
    else:
        # This is a single object. Call the single item method
        try:
            create_from_yaml_single_item(
                k8s_client, data, verbose, namespace=namespace, **kwargs)
        except client.rest.ApiException as api_exception:
            api_exceptions.append(api_exception)

    if api_exceptions:
        raise FailToCreateError(api_exceptions)


def create_from_yaml_single_item(k8s_client, yml_object, verbose=False, **kwargs):
    group, _, version = yml_object["apiVersion"].partition("/")
    if version == "":
        version = group
        group = "core"
    # Take care for the case e.g. api_type is "apiextensions.k8s.io"
    # Only replace the last instance
    group = "".join(group.rsplit(".k8s.io", 1))
    # convert group name from DNS subdomain format to
    # python class name convention
    group = "".join(word.capitalize() for word in group.split('.'))
    fcn_to_call = "{0}{1}Api".format(group, version.capitalize())
    try:
        k8s_api = getattr(client, fcn_to_call)(k8s_client)
    except:
        k8s_api = client.CustomObjectsApi(k8s_client)
    # Replace CamelCased action_type into snake_case
    kind = yml_object["kind"]
    kind = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', kind)
    kind = re.sub('([a-z0-9])([A-Z])', r'\1_\2', kind).lower()
    # Expect the user to create namespaced objects more often
    if hasattr(k8s_api, "create_namespaced_{0}".format(kind)):
        # Decide which namespace we are going to put the object in,
        # if any
        if "namespace" in yml_object["metadata"]:
            namespace = yml_object["metadata"]["namespace"]
            kwargs['namespace'] = namespace
        resp = getattr(k8s_api, "create_namespaced_{0}".format(kind))(
            body=yml_object, **kwargs)
    elif hasattr(k8s_api, "create_{0}".format(kind)):
        kwargs.pop('namespace', None)
        resp = getattr(k8s_api, "create_{0}".format(kind))(
            body=yml_object, **kwargs)
    else:
        kwargs.pop('namespace', None)
        k8s_client.create_namespaced_custom_object(
            body=yml_object, **kwargs)
    if verbose:
        msg = "{0} created.".format(kind)
        if hasattr(resp, 'status'):
            msg += " status='{0}'".format(str(resp.status))
        print(msg)
