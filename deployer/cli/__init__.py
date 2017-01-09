import boto3
from botocore.exceptions import ClientError
import click
import json
import os

from deployer import deploy


INIT_CONTENT = '''{
  "FunctionName": "SomeFunctionName",
  "Description": "Some function description",
  "Handler": "handler.handle",
  "Timeout": 5,
  "MemorySize": 128,
  "Runtime": "python2.7",
  "Publish": true,
  "Role": "arn:? for the iam role",
  "KMSKeyArn": "arn:? that ecrypted the environment variables",
  "Environment": {
    "Variables": {
      "Key": "encrypted value"
      }
    },
  "DeadLetterConfig": {
    "TargetArn": "arn:? to SQS or SNS queue"
    }
}
'''


@click.group()
@click.version_option(version='0.1.0', message='%(prog)s %(version)s')
@click.option('--project-dir',
              help='The project directory.  Defaults to CWD')
@click.option('--debug/--no-debug',
              default=False,
              help='Print debug logs to stderr.')
@click.pass_context
def cli(ctx, project_dir, debug=False):
    if project_dir is None:
        project_dir = os.getcwd()
    ctx.obj['project_dir'] = project_dir
    ctx.obj['debug'] = debug
    os.chdir(project_dir)


@cli.command('init')
@click.pass_context
def init_command(ctx):
    project_dir = ctx.obj['project_dir']
    function_config_file = os.path.join(project_dir, 'function.json')
    if os.path.isfile(function_config_file):
        click.echo("function.json already exists!")
    else:
        with open(function_config_file, 'w') as f:
            f.write(INIT_CONTENT)
        click.echo("function.json created")


@cli.command('deploy')
@click.option('--config', help='Override default config file location')
@click.argument('config', nargs=1, required=False)
@click.pass_context
def deploy_command(ctx, config):
    project_dir = ctx.obj['project_dir']
    if config is None:
        config = 'function.json'

    click.echo("Reading configuration at " + config + "...")
    with open(os.path.join(project_dir, config), 'r') as c:
        config_content = json.loads(c.read())

    click.echo("Validating config...")
    # TODO: Validate the config
    click.echo("Config valid!")

    click.echo("Creating deployment package...")
    deployment_package_filename = deploy.create_deploy_artifact(project_dir)
    click.echo("Deployment package created!")

    click.echo("Checking for existing lambda function '" + config_content['FunctionName'] + "'...")
    lambda_client = boto3.client('lambda')
    try:
        existing_function = lambda_client.get_function(FunctionName=config_content['FunctionName'])
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            existing_function = None
        else:
            raise e

    if existing_function is None:
        click.echo("No existing function found, deploying new function...")
        deploy.deploy_new_function(config_content, deployment_package_filename)
    else:
        click.echo("Existing function found!")
        click.echo("Deploying...")
        deploy.deploy_existing_function(config_content, deployment_package_filename, existing_function)

def main():
    return cli(obj={})
