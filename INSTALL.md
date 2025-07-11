# Home Assistant Python typer Install guide <!-- omit in toc -->

### Table of contents

- [🎬️ Video guide](#️-video-guide)
- [🚂 AppDaemon](#-appdaemon)
- [📜 Editor](#-editor)
  - [Install Python extensions](#install-python-extensions)
  - [Python configuration \& venv](#python-configuration--venv)
  - [Install and run homeassistant\_python\_typer](#install-and-run-homeassistant_python_typer)
  - [Editor configuration](#editor-configuration)
- [🐣 First app](#-first-app)
- [🕵️ Configuring Git](#️-configuring-git)
  - [When using the VSCode addon directly on Home Assistant](#when-using-the-vscode-addon-directly-on-home-assistant)
- [⚡️ Running directly on your computer](#️-running-directly-on-your-computer)

## 🎬️ Video guide

This video provides detailed guidance on the installation process below.

[![Watch the video](https://img.youtube.com/vi/4o37ULggtSk/hqdefault.jpg)](https://youtu.be/4o37ULggtSk?si=EWnINfKellL70sFu&t=211)

## 🚂 AppDaemon

Of course this requires AppDaemon to be installed on HomeAssistant.

You may install the [AppDaemon add-on of HomeAssistant](https://github.com/hassio-addons/repository/blob/master/appdaemon/DOCS.md) for this.
Make sure to enable "Start on boot" and "Watchdog" on the add-on.

When using AppDaemon, you will be referring to entity IDs, so it may be practical to [enable the **Display entity IDs in picker** option](https://my.home-assistant.io/redirect/profile).

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
   - Some guidance on the setup is available at [⚡️ Running directly on your computer](#️-running-directly-on-your-computer)
   - Requires to setup file transfer to send your code to your Home Assistant instance
   - It is highly recommended to use `git` for such file transfer. (Github private repos are free.)
2. Via [the VSCode addon](https://my.home-assistant.io/redirect/supervisor_addon/?addon=a0d7b954_vscode&repository_url=https%3A%2F%2Fgithub.com%2Fhassio-addons%2Frepository) on Home Assistant
   - Super simple setup to get started, no file transfer necessary
   - Make sure to enable "Show in sidebar" on the add-on
   - Requires some resources on your HomeAssistant instance (~800M dedicated RAM)
   - I would still recommended to use `git` to save versions of your code (learn it by using a graphical git client such as VSCode + Git Graph extension), but you could also choose to rely only on Home Assistant backups.

Once you have that set up, the rest of the configuration is on there, so head over the VSCode interface!

### Install Python extensions

- [Install](https://code.visualstudio.com/docs/editor/extension-marketplace#_browse-for-extensions) the [Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python) extension.
- If you are using the Microsoft-packed VSCode, this pack contains Pylance, which uses Pyright, so you don't need an extra extension.
- If you are instead using the VSCode addon of Home Assistant (or any other non-packed-by-microsoft flavor), [install](https://code.visualstudio.com/docs/editor/extension-marketplace#_browse-for-extensions) the [BasedPyright](https://open-vsx.org/extension/detachhead/basedpyright) extension.
- Install the [Black Formatter](https://open-vsx.org/extension/ms-python/black-formatter) extension

### Python configuration & venv

We need to make appdaemon accessible to the type checker.

1. Open your editor (e.g. VSCode), and browse to your AppDaemon apps folder (e.g. if using the VSCode addon, `File > Open folder > /addon_configs/a0d7b954_appdaemon`).
2. Create a virtual environment in your VSCode workspace:
   - Press Ctrl+Shift+P (or Cmd+Shift+P on mac) to open the [Command Palette](https://code.visualstudio.com/docs/getstarted/userinterface#_command-palette) (Ctrl+P then type `>` if that doesn't work)
   - Type `> Python: Select Interpreter`
   - Click "Create virtual environment", then select "Venv" and "/bin/python3"
   - Once that [completes](https://code.visualstudio.com/docs/python/environments#_using-the-create-environment-command), at the bottom right of the editor, if you have any `.py` file open, it should show `3.11.x ('.venv': venv)`
3. Install appdaemon in the virtual env:
   - Press Ctrl+Shift+C (or Cmd+Shift+C on mac) to open a terminal
   - It should show `.venv` at the beginning of the prompt, to signify that it is running within the context of the virtual env that we have just created.
     (If it doesn't, close the terminal with `Ctrl+D` then open it again.)
   - Paste in the VSCode terminal (you may paste in a terminal by using Ctrl+Shift+V):
     ```bash
     pip install --upgrade appdaemon
     ```
     It should complete without any error after some time.
     - **Note that this command will need to be re-run after appdaemon addon updates, to keep venv in sync with appdaemon addon version**

### Install and run homeassistant_python_typer

Press Ctrl+Shift+C (or call "Create a new terminal" from the command palette) in VSCode to open a terminal.

1. Run the following command (You may paste by using Ctrl+Shift+V):
   ```bash
   cd /addon_configs/a0d7b954_appdaemon/ && git clone https://github.com/Ten0/homeassistant_python_typer.git
   ```
2. Run as described in [How it works](./README.md#-how-it-works) to generate the `apps/hapt.py` and `apps/homeassistant_python_typer_helpers.py` files.
   - **Note that this command will need to be re-run if you have added/removed/updated entities in your Home Assistant and possibly after Home Assistant updates, to make everything known in the `hapt.py` file.**

### Editor configuration

TL;DR: If you're using the VSCode addon on Home Assitant, run the following commands:
```bash
cd /addon_configs/a0d7b954_appdaemon/ && (([ -L "./pyrightconfig.json" ] || [ ! -f "./pyrightconfig.json" ]) && ln -sf ./homeassistant_python_typer/pyrightconfig_recommended.jsonc ./pyrightconfig.json)
cd /addon_configs/a0d7b954_appdaemon/ && (mkdir -p .vscode && [ -f ".vscode/settings.json" ] || echo '{}' > ".vscode/settings.json")
TMPFILE=$(mktemp --suffix="settings.json"); jq -s '.[0] * .[1]' ".vscode/settings.json" "./homeassistant_python_typer/recommended_vscode_workspace_settings.json" > "$TMPFILE" && mv "$TMPFILE" ".vscode/settings.json"
```

Note that this disables auto-save in VSCode for the appdaemon workspace, so you'll have to press `Ctrl+S` to save.

<details>
<summary>
<b>Why do we want to disable auto-save?</b>
</summary>

By default, appdaemon will auto-reload any touched file.

This means that if you're running via the VSCode addon directly on HomeAssistant, as you're editing the files, appdaemon will keep attempting to reload files as you are still writing them, so they will typically be broken.

That is why we typically want either:
- To disable VSCode auto-save in its settings (to only manually save with Ctrl+S) (`Ctrl + ,` to open settings, then search auto save)
- To disable appdaemon auto-reload by setting `production_mode: true` in `appdaemon.yaml`, and reload the addon when you want to test new app versions (slower)

Note that if you feel that this isn't relevant for your usual VSCode usage, but is relevant for this case, you may also enable this option only for the appdaemon workspace by pasting `"files.autoSave": "off"` in the `.vscode/settings.json` file of the workspace (Ctrl+P/Ctrl+Shift+P/Ctrl+P/Cmd+P -> `>Open Workspace Settings (JSON)`) instead of the global one.

</details>

<details>
<summary>
<b>Manual configuration</b>
</summary>

To have the typer catch as many mistakes as possible right from your editor, you must configure the extension installed above with appropriate typing constraints in your appdaemon workspace.

Suggested parameters are available in this repository's `pyrightconfig_recommended.jsonc`.

It is recommended to link these settings over to the folder that you open in VSCode when working on your AppDaemon Apps:
```bash
cd /addon_configs/a0d7b954_appdaemon/ && ln -s ./homeassistant_python_typer/pyrightconfig_recommended.jsonc ./pyrightconfig.json
```
It's linked so that it updates automatically.
Note that if you want to edit these settings (advanced users), you should copy the file instead of linking it:
```bash
cd /addon_configs/a0d7b954_appdaemon/ && rm -f ./pyrightconfig.json && cp ./homeassistant_python_typer/pyrightconfig_recommended.jsonc ./pyrightconfig.json
```

The editor also needs some extra configuration, which should be added to  the `.vscode/settings.json` file
(Ctrl+P/Ctrl+Shift+P/Ctrl+P/Cmd+P -> `>Open Workspace Settings (JSON)`):

Paste all of [these recommended settings](./recommended_vscode_workspace_settings.json) to that file.

You may hover your cursor over each option to see what effect it has.

<details>
<summary>
<b>If using Pylance (official VSCode on local machine)</b>
</summary>

You should replace:
```json
{ "basedpyright.analysis.diagnosticMode": "workspace" }
```
with
```json
{ "python.analysis.diagnosticMode": "workspace" }
```

</details>

Some of these settings may be relevant globally instead of only in the workspace, so paste them to Ctrl+P/Ctrl+Shift+P/Ctrl+P/Cmd+P -> `>Open User Settings (JSON)` at your convenience.

</details>


## 🐣 First app

For night/day/time and other similar features to work properly in appdaemon, update the `appdaemon.yaml` file with [appropriate values](https://appdaemon.readthedocs.io/en/latest/CONFIGURE.html#appdaemon) for:
```yaml
appdaemon:
  latitude: 52.379189
  longitude: 4.899431
  elevation: 2
  time_zone: Europe/Amsterdam
```
- [Latitude & longitude of your HA zones](https://my.home-assistant.io/redirect/zones/) (click the edit button on your "Home" zone after opening this link)
- [Altitude calculator](https://www.advancedconverter.com/map-tools/find-altitude-by-coordinates)
- [Timezone list](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones#List)

Then we will register our first app.
Update your `apps.yaml` like so:
```yaml
my_first_sensor_light:
  module: my_first_sensor_light
  class: FirstSensorLight
```

More details on the `apps.yaml` structure and options [in the AppDaemon documentation](https://appdaemon.readthedocs.io/en/latest/APPGUIDE.html#configuration-of-apps).

Copy over the `sensor_light_most_basic.py` example to the `my_first_sensor_light.py` file:
```bash
cd /addon_configs/a0d7b954_appdaemon/
cp ./homeassistant_python_typer/examples/sensor_light_most_basic.py ./apps/my_first_sensor_light.py
```

Opening that `my_first_sensor_light.py` file in your editor, you should see errors: they relate to the example referring to entities that may not exist in your installation.

Go ahead and update the file, using [entity ID](https://www.home-assistant.io/docs/configuration/customizing-devices/)s that exist in your house:
```python
light = self.ha.light.an_actual_light_that_you_have_in_your_homeassistant
sensor = self.ha.binary_sensor.an_actual_motion_sensor_that_you_have_in_your_homeassistant
```

The errors should disappear, and you should have benefited from auto-completion while looking for your entities. If there are errors left in the `turn_on` or `turn_off` call stating that some parameters don't exist, it means that your particular light does not support them. Remove them from the call.

Disable any automation that currently control the light you're testing with (so that we can test properly).

Restart appdaemon and check its log. It should give "Initialized FirstSensorLight" and no error message.

Now go wave your hand in front of your sensor, and your light should turn on! 😊

## 🕵️ Configuring Git

Git is a great way to keep track of your changes and make sure you make no unintended edits.

It's fully local unless explicitly adding a "remote repository" (such as on GitHub) to save it online.

### When using the VSCode addon directly on Home Assistant

Here's how to initialize a local git repository for your appdaemon folder:
```bash
cd /addon_configs/a0d7b954_appdaemon/
[ ! -d .git ] && git init
git config --global user.name &>/dev/null || { echo -n "Enter your name: "; read user_name; git config --global user.name "$user_name"; }
git config --global user.email &>/dev/null || { echo -n "Enter your email: "; read user_email; git config --global user.email "$user_email"; }
```

Then "Reload Window" in VSCode (Ctrl+P/Ctrl+Shift+P/Ctrl+P/Cmd+P -> `> Reload Window`), to make it detect it as the main git repository of the folder.

You may then review and "save" (commit) your changes [using the corresponding VSCode panel](https://code.visualstudio.com/docs/sourcecontrol/intro-to-git#_staging-and-committing-code-changes).

The repository will be backed up along with your regular HomeAssistant backup, as part of the AppDaemon addon's backup.

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
