import logging
import subprocess
import time
from http import HTTPStatus
import os
from flask import Flask, request
from flask import jsonify
from flask import make_response
from werkzeug.exceptions import NotFound
import sys

if 'LOG_LEVEL' in os.environ:
    log_level = os.environ['LOG_LEVEL']
else:
    log_level = logging.INFO

# Logging configuration.
emulator_manager_port = 21212
logger = logging.getLogger(__name__)
logging.basicConfig(format='%(asctime)s> [%(levelname)s][%(name)s][%(funcName)s()] %(message)s',
                    datefmt='%d/%m/%Y %H:%M:%S', level=log_level, stream=sys.stdout)

logging.getLogger('werkzeug').disabled = True

# Sleep time needed to make sure that a VirtualBox command actually finished (in seconds).
vbox_finish_command_time = 1


def create_app():
    logger.info('Starting the application ')
    return Flask(__name__)


app = create_app()


@app.errorhandler(HTTPStatus.BAD_REQUEST)
def bad_request(error):
    logger.error(f'{error}\nRequest that generated the error: {request}')
    return make_response(jsonify(
        {'error': f'{HTTPStatus.BAD_REQUEST.phrase}: {HTTPStatus.BAD_REQUEST.description}'}),
        HTTPStatus.BAD_REQUEST, {'Content-Type': 'application/json'})


@app.errorhandler(HTTPStatus.NOT_FOUND)
def not_found(error):
    logger.error(f'{error}\nRequest that generated the error: {request}')
    return make_response(jsonify(
        {'error': f'{HTTPStatus.NOT_FOUND.phrase}: {HTTPStatus.NOT_FOUND.description}'}),
        HTTPStatus.NOT_FOUND, {'Content-Type': 'application/json'})


@app.errorhandler(HTTPStatus.INTERNAL_SERVER_ERROR)
def internal_error(error):
    logger.error(f'{error}\nRequest that generated the error: {request}')
    return make_response(jsonify(
        {'error': f'{HTTPStatus.INTERNAL_SERVER_ERROR.phrase}: {HTTPStatus.INTERNAL_SERVER_ERROR.description}'}),
        HTTPStatus.INTERNAL_SERVER_ERROR, {'Content-Type': 'application/json'})


def emulator_exists(emulator_name: str):
    vbox_command = 'VBoxManage list vms'
    virtualbox_output = subprocess.check_output(vbox_command, shell=True).strip().decode()
    # True if the emulator is exists, False otherwise.
    return f'"{emulator_name}"' in virtualbox_output


def is_emulator_running(emulator_name: str):
    vbox_command = 'VBoxManage list runningvms'
    virtualbox_output = subprocess.check_output(vbox_command, shell=True).strip().decode()
    # True if the emulator is running, False otherwise.
    return f'"{emulator_name}"' in virtualbox_output


@app.route('/start/<emulator_name>', methods=['GET'], strict_slashes=False)
def start(emulator_name: str):
    """
        Start the emulator
        This endpoint can be used to start the emulator (restore the last snapshot and power on the emulator).
        ---
        tags:
          - Emulator Manager Endpoint
        produces:
          - application/json
        parameters:
          - name: emulator_name
            in: path
            description: |
              The name of the emulator for which to issue the command
            required: true
            type: string
        responses:
          200:
            description: |
              The emulator was started successfully
            schema:
              type: object
          404:
            description: |
              The specified emulator doesn't exist
            schema:
              type: object
          500:
            description: |
              Server error
            schema:
              type: object
    """

    if not emulator_exists(emulator_name):
        raise NotFound(f'Emulator "{emulator_name}" does not exist')
    if not is_emulator_running(emulator_name):
        # Restore the emulator virtual machine to the last snapshot.
        logger.info(f'Restoring last snapshot for emulator "{emulator_name}"')
        snapshot_command = f'VBoxManage snapshot "{emulator_name}" restorecurrent'
        try:
            command_result = subprocess.check_output(snapshot_command, shell=True, stderr=subprocess.STDOUT)
            logger.debug(f'Command `{snapshot_command}` returned: {command_result.strip().decode()}')
        except Exception as e:
            logger.error("Exception as {}".format(e))
            emulator_command_off = f'VBoxManage controlvm "{emulator_name}" poweroff'
            command_result_off = subprocess.call(emulator_command_off, shell=True, stderr=subprocess.STDOUT)
            command_result_snapshot = subprocess.call(snapshot_command, shell=True, stderr=subprocess.STDOUT)

        # Let the snapshot restore finish gracefully before starting the virtual machine.
        time.sleep(vbox_finish_command_time)

        # Start the emulator virtual machine.
        logger.info(f'Starting "{emulator_name}" emulator')
        emulator_command = f'VBoxManage startvm "{emulator_name}"'
        try:
            command_result = subprocess.check_output(emulator_command, shell=True, stderr=subprocess.STDOUT)
            logger.debug(f'Command `{emulator_command}` returned: {command_result.strip().decode()}')
        except Exception as e:
            logger.error("Exception as {}".format(e))
            emulator_command_on = f'VBoxManage startvm "{emulator_name}"'
            command_result_snapshot = subprocess.call(emulator_command_on, shell=True, stderr=subprocess.STDOUT)

        # Let emulator start command finish gracefully.
        time.sleep(vbox_finish_command_time)

        logger.info(f'Emulator "{emulator_name}" successfully started')

        return make_response(jsonify({'message': f'Emulator "{emulator_name}" started'}))
    else:
        logger.warning(f'Unable to start "{emulator_name}" emulator, another instance of '
                       f'the emulator is already running')
        return make_response(jsonify({'message': f'Emulator "{emulator_name}" already running'}), HTTPStatus.CONFLICT)


@app.route('/stop/<emulator_name>', methods=['GET'], strict_slashes=False)
def stop(emulator_name: str):
    """
        Stop the emulator
        This endpoint can be used to stop the emulator (power off the emulator).
        ---
        tags:
          - Emulator Manager Endpoint
        produces:
          - application/json
        parameters:
          - name: emulator_name
            in: path
            description: |
              The name of the emulator for which to issue the command
            required: true
            type: string
        responses:
          200:
            description: |
              The emulator was stopped successfully
            schema:
              type: object
          404:
            description: |
              The specified emulator doesn't exist
            schema:
              type: object
          500:
            description: |
              Server error
            schema:
              type: object
    """

    if not emulator_exists(emulator_name):
        raise NotFound(f'Emulator "{emulator_name}" does not exist')
    if is_emulator_running(emulator_name):
        # Stop the emulator virtual machine.
        logger.info(f'Stopping "{emulator_name}" emulator')
        try:
            emulator_command = f'VBoxManage controlvm "{emulator_name}" poweroff'
            command_result = subprocess.check_output(emulator_command, shell=True, stderr=subprocess.STDOUT)
            logger.debug(f'Command `{emulator_command}` returned: {command_result.strip().decode()}')
            logger.info(f'Emulator "{emulator_name}" successfully stopped')

        except Exception as e:
            logger.error("Exception as {}".format(e))
            emulator_command = f'VBoxManage controlvm "{emulator_name}" poweroff'
            command_result = subprocess.call(emulator_command, shell=True, stderr=subprocess.STDOUT)

        return make_response(jsonify({'message': f'Emulator "{emulator_name}" stopped'}))
    else:
        logger.warning(f'Unable to stop "{emulator_name}" emulator, there is no instance of '
                       f'the emulator currently running')
        return make_response(jsonify({'message': f'Emulator "{emulator_name}" not running'}), HTTPStatus.CONFLICT)


# This has to be used when the emulator crashes in unexpected ways.
@app.route('/reset/<emulator_name>', methods=['GET'], strict_slashes=False)
def reset(emulator_name: str):
    """
        Reset the emulator
        This endpoint can be used to reset the emulator (power off the emulator and restore the last snapshot).
        ---
        tags:
          - Emulator Manager Endpoint
        produces:
          - application/json
        parameters:
          - name: emulator_name
            in: path
            description: |
              The name of the emulator for which to issue the command
            required: true
            type: string
        responses:
          200:
            description: |
              The emulator was reset successfully
            schema:
              type: object
          404:
            description: |
              The specified emulator doesn't exist
            schema:
              type: object
          500:
            description: |
              Server error
            schema:
              type: object
    """

    if not emulator_exists(emulator_name):
        raise NotFound(f'Emulator "{emulator_name}" does not exist')
    if is_emulator_running(emulator_name):
        logger.info(f'Resetting "{emulator_name}" emulator')

        emulator_command = f'VBoxManage controlvm "{emulator_name}" poweroff'
        command_result = subprocess.check_output(emulator_command, shell=True, stderr=subprocess.STDOUT)
        logger.debug(f'Command `{emulator_command}` returned: {command_result.strip().decode()}')

        # Let the power off finish gracefully before restoring the last snapshot.
        time.sleep(vbox_finish_command_time)

        # Restore the emulator virtual machine to the last snapshot.
        snapshot_command = f'VBoxManage snapshot "{emulator_name}" restorecurrent'
        command_result = subprocess.check_output(snapshot_command, shell=True, stderr=subprocess.STDOUT)
        logger.debug(f'Command `{snapshot_command}` returned: {command_result.strip().decode()}')
    return make_response(jsonify({'message': f'Emulator "{emulator_name}" reset'}))


if __name__ == '__main__':
    # It's important to bind the port on all interfaces, this way the emulators can be managed from any
    # network on the host machine (this is useful for Docker containers).
    app.run(host='0.0.0.0', port=emulator_manager_port)
