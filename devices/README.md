# Terraserver device controller code

This code provides local on-site monitoring and control software for Terraformation hardware systems 
(seed banks, power generation, desalination, irrigation, etc.).

## Installation

First, make sure the rhizo client library's submodule is cloned and checked out.

    git submodule update rhizo

Next, install dependencies for both terranode itself and the rhizo client.

    pip install -r requirements-prebuild.txt -r requirements.txt
    pip install -r rhizo/requirements.txt -r rhizo/rhizo/extensions/requirements.txt

Then clone the the `terraware/sites` repo to get site-specific configuration files:

    git clone git@github.com:terraware/sites

## Configuration

rhizo-server must be running with WebSockets enabled.

1.  In the rhizo-server UI, create a controller folder called `controller` (top navbar New -> Controller).
2.  Copy `sample_local.yaml` to `local.yaml` and place it in the site directory (e.g. `sites/pac-flight`); adjust settings as needed.
3.  Run the device controller program: `python ../../terraserver/devices/src/main.py`
4.  Enter the PIN in the rhizo-server user interface (clicking the drop-down menu on the controller folder).

## Set up for automatic startup

1.  From the `devices` directory, run `sudo cp terra.service /etc/systemd/system`
2.  Edit `/etc/systemd/system/terra.service` so that it runs from the site directory.
2.  Run `sudo systemctl daemon-reload`
3.  Run `sudo systemctl enable terra`
4.  Run `sudo systemctl start terra`
5.  Run `sudo systemctl status terra`; check that the service is running.

## Testing

If `local.yaml` has a config setting `sim: 1`, the server will use a simulated data source.

A simple modbus test server is provided in the `test` folder.

## Working on the rhizo client

This project includes the rhizo client as a submodule so it can be included as part of the Docker image that gets distributed by Balena. You can work in the `rhizo` directory if you want to change the client and terranode code at the same time.

If you prefer to use a different copy of the client, just point the `src/rhizo` symlink to it; make sure not to commit your updated symlink.

## Docker and Balena

The application is deployed to the field using Balena, which requires it to be packaged in a Docker image. The Docker image needs to be built using the Balena build system, but you can run the build locally using the Balena command-line tool.

Quickstart (for OS X):

    brew install balena-cli
    balena login
    balena build -d amd64 -A amd64
    docker run --rm \
        -e RHIZO_DEVICE_DIAGNOSTICS=0 \
        -e RHIZO_ENABLE_SERVER=1 \
        -e RHIZO_SECRET_KEY=YOUR_RHIZO_SERVER_KEY_HERE \
        -e RHIZO_SECURE_SERVER=false \
        -e RHIZO_SERVER_NAME=\"host.docker.internal:5000\" \
        -e RHIZO_SIM=1
        terranode_terranode

To push a new release to the Balena service (this will deploy it to any devices that are set to run the latest release, which currently they all are):

    balena push terranode
