# Home Assistant Python typer Install guide <!-- omit in toc -->

### Table of contents

- [🚂 AppDaemon](#-appdaemon)
- [📜 Editor](#-editor)
  - [Install Python extension](#install-python-extension)
  - [Python configuration \& venv](#python-configuration--venv)
  - [Install and run homeassistant\_python\_typer](#install-and-run-homeassistant_python_typer)
  - [Typer configuration](#typer-configuration)
  - [Note about auto-reload (for VSCode addon users)](#note-about-auto-reload-for-vscode-addon-users)
- [🐣 First app](#-first-app)
- [⚡️ Running directly on your computer](#️-running-directly-on-your-computer)


## 🚂 AppDaemon

Of course this requires AppDaemon to be installed on HomeAssistant.

You may install the [AppDaemon add-on of HomeAssistant](https://github.com/hassio-addons/repository/blob/master/appdaemon/DOCS.md) for this.

By default `appdaemon.yaml` and `apps` will be stored in `/addon_configs/a0d7b954_appdaemon`, so those are the files you should edit.

<details>
<summary>
<b>Storing AppDaemon config in `/homeassistant`</b>
</summary>

The default storage path may not be super practical if e.g. you track your `/homeassistant` config folder with git and edit on your local machine, or regularly edit things in `/homeassistant` from the VSCode addon and you don't want to switch folders all the time.

By putting your `appdaemon.yaml` in your [Home Assistant config folder](https://www.home-assistant.io/docs/configuration/#to-find-the-configuration-directory) in an `appdaemon` directory, under a different name, (I use `appdaemon-prod.yaml`, [needs different name because](https://github.com/hassio-addons/addon-appdaemon/blob/6d7b6dd287f5aa9dc75d59c69c2713c3a7f22538/appdaemon/rootfs/etc/s6-overlay/s6-rc.d/init-appdaemon/run#L10-L15)), [putting](https://appdaemon.readthedocs.io/en/latest/CONFIGURE.html#appdaemon) `app_dir: /homeassistant/appdaemon/apps` in `appdaemon.yaml`, and using `cp /homeassistant/appdaemon/appdaemon-prod.yml /config/appdaemon.yaml` as "init command" in the add-on configuration, it would indeed start AppDaemon using `/homeassistant/appdaemon` as source directory instead of `/addon_configs/a0d7b954_appdaemon`.

Note that if running AppDeamon locally instead (which is significantly more practical than copying the files to whatever device HA is running on during development, and enables e.g. using a debugger...), it doesn't support relative paths for `app_dir`. ([#309](https://github.com/AppDaemon/appdaemon/issues/309#issuecomment-959449004))
</details>

## 📜 Editor

We provide documentation here for VSCode but of course you may configure other editors that have good support for Python.

You may use VSCode either:
1. Directly on your own computer ([Download](https://code.visualstudio.com/))
   - Reactive and flexible editing, with the full power of a native editor on your performant computer
   - Requires to setup file transfer to send your code to your Home Assistant instance
   - It is highly recommended to use `git` for such file transfer. (Github private repos are free.)
2. Via [the VSCode addon](https://community.home-assistant.io/t/home-assistant-community-add-on-visual-studio-code/107863) on Home Assistant
   - Super simple setup to get started, no file transfer necessary
   - Requires some resources on your HomeAssistant instance (~800M dedicated RAM)
   - I would still recommended to use `git` to save versions of your code (learn it by using a graphical git client such as VSCode + Git Graph extension), but you could also choose to rely only on Home Assistant backups.

### Install Python extension

- If you are using the VSCode addon of Home Assistant (or any other non-packed-by-microsoft flavor), [install](https://code.visualstudio.com/docs/editor/extension-marketplace#_browse-for-extensions) the [BasedPyright](https://open-vsx.org/extension/detachhead/basedpyright) extension.
- If you are using the Microsoft-packed VSCode, you may [install](https://code.visualstudio.com/docs/editor/extension-marketplace#_browse-for-extensions) the [Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python) extension (which contains Pylance, which uses Pyright).

### Python configuration & venv

We need to make appdaemon accessible to the type checker.

1. Open your editor (e.g. VSCode), and browse to your AppDaemon apps folder (e.g. if using the VSCode addon, `File > Open folder > /addon_configs/a0d7b954_appdaemon`).
2. Create a virtual environment in your VSCode workspace:
   - Press Ctrl+Shift+P (or Cmd+Shift+P on mac) to open the command palette (Ctrl+P then type `>` if that doesn't work)
   - Type `> Python: Select Interpreter`
   - Click "Create virtual environment"
   - Once that [completes](https://code.visualstudio.com/docs/python/environments#_using-the-create-environment-command), at the bottom right of the editor, if you have any `.py` file open, it should show `3.11.x ('.venv': venv)`
3. Install appdaemon in the virtual env:
   - Press Ctrl+Shift+C to open a terminal
   - It should show `.venv` at the beginning of the prompt, to signify that it is running within the context of the virtual env that we have just created.
   - Type `pip install --upgrade appdaemon` in the VSCode terminal. It should complete without any error after some time.
     - (Note that this command may need to be re-run after appdaemon updates, to keep venv in sync with appdaemon addon version)

### Install and run homeassistant_python_typer

Press Ctrl+Shift+C (or call "Create a new terminal" from the command palette) in VSCode to open a terminal.

1. Go to your appdaemon directory: `cd /addon_configs/a0d7b954_appdaemon/`
2. Download homeassistant_python_typer: `git clone https://github.com/Ten0/homeassistant_python_typer.git`
3. Run as described in [How it works](./README.md#-how-it-works) to generate the `apps/hapt.py` and `apps/homeassistant_python_typer_helpers.py` files.
   - Note that this command will need to be re-run if you have added/removed/updated entities in your Home Assistant and possibly after Home Assistant updates, to make everything known in the `hapt.py` file.

### Typer configuration

To have the typer catch as many mistakes as possible right from your editor, you must configure the extension installed above with appropriate typing constraints in your appdaemon workspace.

Suggested parameters are available in this repository's `pyrightconfig_recommended.jsonc`.

It is recommended to copy these (or better yet, symlink them so that you get updates) over to the folder that you open in VSCode when working on your AppDaemon Apps:
```bash
cd /addon_configs/a0d7b954_appdaemon/ && ln -s ./homeassistant_python_typer/pyrightconfig_recommended.jsonc ./pyrightconfig.json
```

Also you should make VSCode check all files and not only those you currently have open, by adding to the `.vscode/settings.json` file (may need to be created):

With BasedPyright (if running e.g. the VSCode home assistant addon):
```json
{ "basedpyright.analysis.diagnosticMode": "workspace" }
```

With Pylance (official VSCode on local machine):
```json
{ "python.analysis.diagnosticMode": "workspace" }
```

### Note about auto-reload (for VSCode addon users)

By default, the VSCode editor will auto-save all files. Also, appdaemon will auto-reload any touched file.

This means that if you're running via the VSCode addon directly on HomeAssistant, as you're editing the files, appdaemon will keep attempting to reload files as you are still writing them, so they will typically be broken.

You may want either:
- To disable VSCode auto-save in its settings (only manually save with Ctrl+S)
- To disable appdaemon auto-reload by setting `production: true` in `appdaemon.yaml`, and reload the addon when you want to test new app versions (slower)

Note that in any case, you may need to reload the appdaemon addon after editing files other than a single-app file (in particular after refreshing `hapt.py`).

To some extent, this last issue can be avoided by [declaring Global Module Dependencies in `apps.yaml`](https://appdaemon.readthedocs.io/en/latest/APPGUIDE.html#global-module-dependencies)

## 🐣 First app

For night/day/time and other similar features to work properly in appdaemon, update the `appdaemon.yaml` file with appropriate values for:
```yaml
appdaemon:
  latitude: 52.379189
  longitude: 4.899431
  elevation: 2
  time_zone: Europe/Amsterdam
```

Then we will register our first app.
Update your `apps.yaml` like so:
```yaml
homeassistant_python_typer_helpers:
  module: homeassistant_python_typer_helpers
  global: true
hapt:
  module: hapt
  global: true
  dependencies: homeassistant_python_typer_helpers

my_first_sensor_light:
  module: my_first_sensor_light
  class: HallwaySensorLights
  dependencies:
    - hapt
```

More details on the `apps.yaml` structure and options [in the AppDaemon documentation](https://appdaemon.readthedocs.io/en/latest/APPGUIDE.html#configuration-of-apps).

Copy over the `sensor_lights.py` example to the `my_first_sensor_light.py` file:
```bash
cd /addon_configs/a0d7b954_appdaemon/
cp ./homeassistant_python_typer/examples/sensor_lights.py ./apps/my_first_sensor_light.py
```

Opening that `my_first_sensor_light.py` file in your editor, you should see errors: they relate to the example referring to entities that may not exist in your installation.

Go ahead and update the file, using [entity ID](https://www.home-assistant.io/docs/configuration/customizing-devices/)s that exist in your house:
```python
self.light = self.ha.light.an_actual_light_that_you_have_in_your_homeassistant
self.sensor = self.ha.binary_sensor.an_actual_motion_sensor_that_you_have_in_your_homeassistant
```

The errors should disappear, and you should have benefited from auto-completion while looking for your entities. If there are errors left in the `turn_on` or `turn_off` call stating that some parameters don't exist, it means that your particular light does not support them. Remove them from the call.

Disable any automation that currently control the light you're testing with (so that we can test properly).

Restart appdaemon and check its log. It should give "Initialized HallwaySensorLights" and no error message.

Now go wave your hand in front of your sensor, and your light should turn on! 😊

## ⚡️ Running directly on your computer

If you prefer to develop directly from the confort of your own computer from your local editor, you may run the typer script there as well.
However in this case it is necessary to tell the script where your HomeAssistant instance is.

This is done via two environment variables:
- `HOMEASSISTANT_URL`: The URL of your HomeAssistant instance
- `HOMEASSISTANT_TOKEN`: A [long-lived token to your HomeAssistant instance](https://community.home-assistant.io/t/how-to-get-long-lived-access-token/162159/5?u=ten)

The set of commands to run to update your types then becomes:
```
cd homeassistant_python_typer/src
git pull
export HOMEASSISTANT_URL="URL of your home assistant instance"
export HOMEASSISTANT_TOKEN="A long-lived access token to your HomeAssistant instance"
python3 -m homeassistant_python_typer /path/to/write/hapt.py && cp ../homeassistant_python_typer_helpers.py /path/to/write/homeassistant_python_typer_helpers.py
```

<details>
<summary>direnv</summary>

You may make the environment variables (and appropriate Python version) accessible without friction as you `cd` into the relevant project folder by using [`direnv`](https://direnv.net/).

Note that this project already has a `.envrc` configured that ends up sourcing the gitignored file `.secrets`, so you may put the definition of these environment variables there.
</details>
