#!/usr/bin/env python
"""
kubernetes deploy plugin
"""
import base64
import json
import logging
import os
import shlex
import subprocess
import sys
import tempfile

import configargparse
import jinja2
import yaml


logger = logging.getLogger()
logging_handler = logging.StreamHandler()
logging_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
logging_handler.setFormatter(logging_formatter)
logger.addHandler(logging_handler)


def run(cmd):
    logger.debug('execute cmd: {}'.format(cmd))
    args = shlex.split(cmd)
    with subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as proc:
        stdout = proc.stdout.read()
        stderr = proc.stderr.read()
        if stdout:
            logger.debug(stdout.decode())
        if stderr:
            logger.error(stderr.decode())


def fatal(msg):
    logger.fatal(msg)
    sys.exit(1)


def main():
    """
    The main entrypoint for the plugin.
    """
    arg_parser = configargparse.ArgParser()
    arg_parser.add('-s', '--server',
                   default='https://kubernetes.default.svc.cluster.local:443',
                   help='kubernetes server address', env_var='PLUGIN_SERVER')

    arg_parser.add('-t', '--token', required=True,
                   help='kubernetes server token', env_var='PLUGIN_TOKEN')

    arg_parser.add('-c', '--ca', required=True,
                   help='kubernetes server certificate-authority', env_var='PLUGIN_CA')

    arg_parser.add('-f', '--file',
                   default='kubernetes.yaml',
                   help='kubernetes template file', env_var='PLUGIN_FILE')

    arg_parser.add('-d', '--debug', action='store_true',
                   help='enable plugin debug mode', env_var='PLUGIN_DEBUG')

    arg_parser.add('-C', '--context',
                   help='template rendering context', env_var='PLUGIN_CONTEXT')

    arg_parser.add('-w', '--workspace', help='drone workspace directory',
                   default='.', env_var='DRONE_WORKSPACE')

    drone_args = dict(
        commit=(
            'author',
            'branch',
            'message',
            'ref',
            'sha',
        ),
        build=(
            'created',
            'event',
            'link',
            'number',
            'started',
            'status',
            'tag',
        ),
        repo=(
            'name',
            'owner',
        ),
        job=(
            'started',
        ),
    )

    def add_drone_arg(section, arg):
        arg_parser.add(
            '--{}_{}'.format(section, arg),
            help='{} {}'.format(section, arg),
            env_var='DRONE_TAG'
            if section == 'build' and arg == 'tag'
            else 'DRONE_{}_{}'.format(section, arg).upper()
        )


    for section, args in drone_args.items():
        for arg in args:
            add_drone_arg(section, arg)

    options = arg_parser.parse_args()

    if options.debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    logger.info('plugin started')
    logger.debug(options)

    # save certificate authority
    open('./ca.crt', 'wb').write(base64.b64decode(options.ca.encode()))

    # configure kubectl
    token = base64.b64decode(options.token.encode()).strip().decode()

    for cmd in (
            'kubectl config set-cluster default --server={server} --embed-certs=true --certificate-authority=./ca.crt'.format(
                server=options.server),
            'kubectl config set-credentials default --token="{token}"'.format(token=token),
    ):
        run(cmd)

    path, filename = os.path.split(options.file)

    if options.context:
        context = json.loads(options.context)
        args_intersection = set(context.keys()) & set(drone_args.keys())
        if args_intersection:
            fatal('You can not use drone builtin args in context: {}'.format(args_intersection))
    else:
        context = {}

    for section, args in drone_args.items():
        context[section] = {}
        for arg in args:
            context[section][arg] = getattr(options, '{}_{}'.format(section, arg))

    logger.debug('rendering context: {}'.format(context))

    template = jinja2.Environment(
        loader=jinja2.FileSystemLoader(os.path.join(options.workspace, path))
    ).get_template(filename)

    rendered = template.render(context)
    logger.debug('rendered template:\n{}'.format(rendered))

    # yaml validation
    yaml.load_all(rendered)

    with tempfile.NamedTemporaryFile('w', encoding='utf-8', suffix='.yaml') as file:
        file.write(rendered)
        file.flush()
        run('kubectl --cluster=default --user=default apply -f {file_name}'.format(file_name=file.name))


if __name__ == "__main__":
    main()
