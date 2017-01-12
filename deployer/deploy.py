# global imports
import hashlib
import os
import subprocess
import sys
import zipfile

import boto3
import virtualenv
from botocore.exceptions import ClientError

# deployer imports
import compat


def has_at_least_one_package(filename):
    if not os.path.isfile(filename):
        return False

    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                return True

    return False


def create_deploy_artifact(project_dir):
    # Create virtualenv
    venv_dir = os.path.join(project_dir, '.deploy', 'venv')
    original = sys.argv
    sys.argv = ['', venv_dir, '--quiet']
    try:
        virtualenv.main()
    finally:
        sys.argv = original

    # Make sure pip is available independent of platform
    pip_exe = compat.pip_script_in_venv(venv_dir)
    assert os.path.isfile(pip_exe)

    # Process requirements file
    requirements_file = os.path.join(project_dir, 'requirements.txt')
    if not os.path.isfile(requirements_file):
        hash_content = ''
    else:
        with open(requirements_file, 'r') as f:
            hash_content = f.read()
    requirements_hash = hashlib.md5(hash_content).hexdigest()
    deployment_package_filename = os.path.join(
        project_dir, '.deploy', 'deployments', requirements_hash + '.zip')
    if has_at_least_one_package(requirements_file) and not \
            os.path.isfile(deployment_package_filename):
        p = subprocess.Popen([pip_exe, 'install', '-r', requirements_file],
                             stdout=subprocess.PIPE)
        p.communicate()

    # Handle new virtualenv dependencies
    deps_dir = compat.site_packages_dir_in_venv(venv_dir)
    assert os.path.isdir(deps_dir)

    if not os.path.isdir(os.path.dirname(deployment_package_filename)):
        os.makedirs(os.path.dirname(deployment_package_filename))

    with zipfile.ZipFile(deployment_package_filename, 'w',
                         compression=zipfile.ZIP_DEFLATED) as z:
        # add dependencies
        prefix_len = len(deps_dir) + 1
        for root, dirnames, filenames in os.walk(deps_dir):
            if root == deps_dir and 'lambda-deployer' in dirnames:
                # we don't want to deploy the deployer, just the project deps
                dirnames.remove('lambda-deployer')
            for filename in filenames:
                full_path = os.path.join(root, filename)
                zip_path = full_path[prefix_len:]
                z.write(full_path, zip_path)

        # add project files
        sources_directory = os.path.join(project_dir, 'src')
        prefix_len = len(sources_directory) + 1
        for root, dirnames, filenames in os.walk(sources_directory):
            for filename in filenames:
                full_path = os.path.join(root, filename)
                zip_path = full_path[prefix_len:]
                z.write(full_path, zip_path)

    return deployment_package_filename


def deploy_new_function(config, code_file):
    with open(code_file, 'rb') as c:
        code = c.read()

    client = boto3.client('lambda')
    try:
        response = client.create_function(Code={'ZipFile': code}, **config)
    except ClientError as c:
        # In the future, create handler to retry
        print "There was a problem:"
        print c
        return None
    return response['FunctionArn']


def deploy_existing_function(config, code_file, existing_function):
    client = boto3.client('lambda')

    # update configuration without the Publish key
    configuration = {k: v for k, v in config.iteritems() if k != 'Publish'}
    if 'VpcConfig' not in configuration.keys():
        configuration['VpcConfig'] = {
            'SubnetIds': [],
            'SecurityGroupIds': []
        }

    client.update_function_configuration(**configuration)

    # update code
    with open(code_file, 'rb') as c:
        code = c.read()

    client.update_function_code(
        FunctionName=config['FunctionName'],
        ZipFile=code)
