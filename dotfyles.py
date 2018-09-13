# -*- coding: UTF-8 -*-

# References:
# - http://git-secret.io/ to check important files
# - https://github.com/herrbischoff/awesome-macos-command-line
# TO SEE:
# - defaults read /Users/jfloff/Library/Preferences/MobileMeAccounts.plist Accounts
# - https://apple.stackexchange.com/questions/79761/editing-system-preferences-via-terminal

import os
import distutils.spawn
import subprocess
from pip._internal import main, utils
import argparse
import getpass
import sys
import collections
import time
import shutil
import string
import io
import csv
import re
import urllib
import json

os.environ["PYTHONIOENCODING"] = "utf-8"
DEV_NULL = open(os.devnull, 'w')

#########################
# Output helper functions
#

def _emoji(code):
    return chr(int(code[2:], 16))

CGREEN = '\033[32m'
CMAGENTA = '\033[35m'
CCYAN = '\033[36m'
CYELLOW= '\033[33m'
CRESET = '\033[0m'
SNEK = _emoji('U+1F40D')
GRASS = _emoji('U+1F33F')
WARN = _emoji('U+26A0')

def _safe_print(msg, **kwargs):
    try:
        print(msg, **kwargs)
    except UnicodeEncodeError:
        print(msg.encode('ascii','ignore'), **kwargs)

def _safe_input(msg):
    try:
        return input(msg)
    except UnicodeEncodeError:
        return input(msg.encode('ascii','ignore'))

def _safe_getpass(msg):
    try:
        return getpass.getpass(msg)
    except UnicodeEncodeError:
        return getpass.getpass(msg.encode('ascii','ignore'))

def _snek(msg):
    _safe_print('\n' + SNEK + ' ' + msg + '\n')

def _grass(msg):
    _safe_print('\n' + GRASS + ' ' + msg + '')

def _ok(msg=""):
    _safe_print(CGREEN + "[ok]" + CRESET + " " + msg)

def _question(msg, pwd=False, yN=False, Yn=False, default=''):
    msg = CMAGENTA + "¿" + CRESET + " " + msg
    if pwd:
        return _safe_getpass(msg + ": ")
    elif default:
        return (_safe_input(msg + " [" + default + "]: ") or default)
    elif Yn:
        yes = {'yes','y', 'ye', ''}
        no = {'no','n'}
        return True if _safe_input(msg + " [Y|n]: ").lower() in yes else False;
    elif yN:
        yes = {'yes','y', 'ye'}
        no = {'no','n', ''}
        return True if _safe_input(msg + " [y|N]: ").lower() in yes else False;
    else:
        return _safe_input(msg + ": ")

def _info(msg, **kwargs):
    _safe_print(CCYAN + "¡" + CRESET + " " + msg, **kwargs)

def _warn(msg, **kwargs):
    _safe_print(CYELLOW + WARN + CRESET + " " + msg, **kwargs)


#########################
# Lib helper functions
#
def _abspath(relative_fpath):
    if '~' in relative_fpath:
        return os.path.expanduser(relative_fpath)
    else:
        return os.path.abspath(relative_fpath)

def _create_symlink(src, dst):
    src = _abspath(src)
    dst = _abspath(dst)

    # return None if the src path doesnt exist
    if not os.path.exists(src):
        return None

    # if the paths are different we will force removal
    if os.path.realpath(dst) != src:
        # remove existing file if not a symlink
        if not os.path.islink(dst):
            os.remove(dst)

        # if its not a symlink or realpath is not the same as the src we replace
        if os.path.islink(dst):
            try:
                os.unlink(dst)
            except OSError:
                pass

        # after removing we add again
        os.symlink(src, dst)

    # we return the dst
    return dst

def _symlink_to_home(src, dst=None):
    if dst is None:
        dst = os.path.join('~/', os.path.basename(src))
    _info("Symlink from '" + src + "' to '" + dst + "'")
    return _create_symlink(src, dst)

def _local_with_brew_check(pkg):
    brew = local.get('brew','/usr/local/bin/brew')

    brew_has_pkg = brew['ls', '--versions', pkg].run(retcode=None)
    if brew_has_pkg[0] == 1:
        _info("Installing '" + pkg +"' terminal tool")
        if brew['install', pkg].run(retcode=None)[0] == 1:
            # return None if we fail to install
            return None

    return local.get(pkg, '/usr/local/bin/'+pkg)

def _wait_for_file(filepath):
    filepath = _abspath(filepath)
    while not os.path.exists(filepath):
        time.sleep(1)

def _download_file(url, filepath=None):
    filepath = _abspath(os.path.join('.', url.split("/")[-1])) if filepath is not None else _abspath(filepath)
    urllib.request.urlretrieve(url, filepath)

def _user_defaults(defaults):
    return os.path.join(_abspath('~/Library/Preferences/'), defaults + '.plist')

def replace_user_path(app_path, new_user_path):
    if app_path.startswith('/Users/'):
        app_path = os.path.join(new_user_path, '/'.join(app_path.split('/', 3)[3:]))
    return app_path

def check_output_zsh(cmd):
    output = subprocess.check_output(cmd, shell=True, executable="/bin/zsh")
    output = output.decode('utf.8')
    return output

#########################
# Step functions
#

PIP_DEPENDENCIES = ['plumbum', 'requests']
SHELL_USER = os.getenv('SUDO_USER') if os.getenv('SUDO_USER') else getpass.getuser()
USER_PATH = os.path.expanduser('~'+SHELL_USER)
GITHUB_USR = ''
GITHUB_PWD = ''
APPLE_ID_EMAIL = ''
USER_NAME = ''
USER_EMAIL = ''
MAC_NAME = ''
SIP_ENABLED = None


def ensure_sudo():
    su = sudo[local['su']]
    chmod = sudo[local['chmod']]

    # recall this script with sudo
    if os.geteuid() != 0:
        _warn(SNEK + " needs sudo to run!")

        # make sure the file can be written to
        chmod['+w', '/etc/profile'].run()
        # read its contents
        with open('/etc/profile', 'r') as f:
            USER_PATH = os.path.join(os.path.expanduser('~'+SHELL_USER), '.profile')
            to_write = "source " + USER_PATH
            if to_write not in f.read():
                os.system("echo '" + to_write + "' | sudo tee -a /etc/profile")

        subprocess.call(['sudo', sys.executable, *sys.argv])
        exit()


def install_pip_packages():
    packages = utils.misc.get_installed_distributions()
    packages = [ p.project_name for p in packages ]
    needed_packages = list(set(PIP_DEPENDENCIES) - set(packages))
    if needed_packages:
        _grass("Installing pip packages: " + ' '.join(needed_packages))
        args = ['install'] + needed_packages
        main(args)

    return needed_packages


def uninstall_pip_packages(installed):
    if installed:
        _grass("Uninstalling pip packages: " + ' '.join(installed))
        args = ['uninstall'] + installed
        main(args)


def personal_info():
    global USER_NAME, USER_EMAIL, GITHUB_USR, APPLE_ID_EMAIL, MAC_NAME
    git = local["git"]
    scutil = sudo[local['scutil']]
    dscacheutil = local['dscacheutil']
    defaults = sudo[local['defaults']]


    _snek("Setting up personal info")

    _grass("Getting your Github info")

    existing_github_user = git['config', '--global', 'github.user'].run(retcode=None)[1].rstrip('\n')
    GITHUB_USR = _question("Github username", default=existing_github_user)

    github_info = []
    if GITHUB_USR != existing_github_user:
        GITHUB_PWD = _question("Github '" + GITHUB_USR + "' password", pwd=True)
        session = requests.Session()
        session.auth = (GITHUB_USR, GITHUB_PWD)
        github_info = session.get('https://api.github.com/users/'+GITHUB_USR).json()

        existing_name = github_info['name']
        existing_email = github_info['email']
        github_clientid = github_info['id']
    else:
        existing_name = git['config', '--global', 'user.name'].run(retcode=None)[1].rstrip('\n')
        existing_email = git['config', '--global', 'user.email'].run(retcode=None)[1].rstrip('\n')

    USER_EMAIL = _question("Set email to", default=existing_email)
    USER_NAME = _question("Set user full name to", default=existing_name)
    _ok()


    _grass("Setup 'mas' Apple ID")

    mas = _local_with_brew_check('mas')
    if mas is None:
        _warn("Cannot install 'mas'! Skipping Apple ID setup.")
    else:
        mas_has_account = mas['account'].run(retcode=None)
        if mas_has_account[0] == 1:
            APPLE_ID_EMAIL = _question("Please enter your Apple ID email", default=USER_EMAIL)
            mas['signin', APPLE_ID_EMAIL] & FG

    _ok()

    _grass("Set computer name")
    MAC_NAME = scutil['--get', 'ComputerName'].run()[1].rstrip("\n\r")
    MAC_NAME = _question("Please enter your Mac's name", default=MAC_NAME)
    _info("Set computer name to: " + MAC_NAME)
    scutil['--set', 'ComputerName', MAC_NAME].run()
    scutil['--set', 'HostName', MAC_NAME].run()
    scutil['--set', 'LocalHostName', MAC_NAME].run()
    defaults['write', '/Library/Preferences/SystemConfiguration/com.apple.smb.server', 'NetBIOSName', '-string', MAC_NAME].run()
    dscacheutil['-flushcache']
    _ok()


    _snek("Done!")


def git():
    global USER_NAME, USER_EMAIL, GITHUB_USR
    git = local["git"]
    openapp = local["open"]

    _snek("Setting up >Git<")

    _grass("Setting your personal info in .gitconfig with (name: {}, email: {}, github user: {})".format(USER_NAME, USER_EMAIL, GITHUB_USR))
    git['config', '--global', 'user.name', USER_NAME]
    git['config', '--global', 'user.email', USER_EMAIL]
    git['config', '--global', 'github.user', GITHUB_USR]

    _grass("Setting [github.token] parameter")
    gitconfig_private = _abspath('.gitconfig.private')
    has_token = git['config', '-f', gitconfig_private, 'github.token'].run(retcode=None)
    if (has_token[0] == 1) or (not has_token[1]):
        _info("Opening Github tokens website")
        openapp["https://github.com/settings/tokens"] & BG
        github_token = _question("Please input your github command line token: ")
        _info("Adding github token to your .gitconfig.private file")
        git['config', '-f', gitconfig_private, 'github.token', github_token] & FG
    _ok()

    update_gitignore()

    _grass("Symlinking git dotfiles")
    _symlink_to_home('.gitconfig')
    _symlink_to_home(gitconfig_private)
    _symlink_to_home('.gitignore')
    _ok()


def update_gitignore():
    GITIGNORE_URLS = [
        'https://raw.githubusercontent.com/github/gitignore/master/Global/macOS.gitignore',
        'https://raw.githubusercontent.com/github/gitignore/master/Global/Linux.gitignore',
        'https://raw.githubusercontent.com/github/gitignore/master/Global/Windows.gitignore',
        'https://raw.githubusercontent.com/github/gitignore/master/Global/Dropbox.gitignore',
        'https://raw.githubusercontent.com/github/gitignore/master/Global/MicrosoftOffice.gitignore',
        'https://raw.githubusercontent.com/github/gitignore/master/Global/VisualStudioCode.gitignore',
        'https://raw.githubusercontent.com/github/gitignore/master/Global/JetBrains.gitignore',
    ]
    GITIGNORE_SEP_LINE = '#######################\n#######################'


    _grass("Updating global .gitignore")

    # get our personal part of .gitignore
    f = open(_abspath('.gitignore'),'r')
    own_gitignore = f.read().split(GITIGNORE_SEP_LINE,1)[0]
    f.close()

    # we ignore the rest and build again from the urls
    remote_gitignore = ''
    remote_gitignore_values = set()
    for url in GITIGNORE_URLS:
        header = '\n\n\n' \
                 '#######################\n' \
                 '# ' + url + ' \n' \
                 '#\n\n'

        remote_gitignore += header + requests.get(url).text

        # add content of the file
        for l in requests.get(url).text.splitlines():
            if l and (not l.startswith('#')):
                remote_gitignore_values.add(l)


    own_gitignore_values = set([ v for v in own_gitignore.splitlines() if v and not v.startswith('#') ])
    duplicate_on_owngitinore = own_gitignore_values.intersection(remote_gitignore_values)
    for dup in duplicate_on_owngitinore:
        own_gitignore = own_gitignore.replace(dup + '\n', '')

    merged_files = ''.join([own_gitignore, GITIGNORE_SEP_LINE, remote_gitignore])
    with open(_abspath('.gitignore'), 'w') as tmp_gitignore:
        tmp_gitignore.write(merged_files)

    _ok()


def brew():
    brew = local['brew']

    # Make sure we’re using the latest Homebrew
    _grass("Updating homebrew")
    brew["update"]
    brew["upgrade"]
    _ok()

    _grass("Installing brews")
    brewfile = '.Brewfile'
    _symlink_to_home(brewfile)

    brew_bundle_check = brew['bundle', 'check', '--file='+brewfile].run(retcode=None)
    if brew_bundle_check[0] == 1:
        brew['bundle', 'install', '--file='+brewfile].run(retcode=None)

    _ok()

    _grass("Brew post-installation settings")
    _info("Make sure loginitems ls command prints more output")
    # FIXME: Copy this file until PR is not merged back to main
    # find path no matter the loginitems version
    loginitemsls_path = readlink['-f', '/usr/local/bin/loginitems-ls'].run()[1]
    _download_file('https://raw.githubusercontent.com/jfloff/loginitems/master/loginitems-ls', loginitemsls_path)

    _ok()


def shell():
    chsh = sudo[local['chsh']]
    which = local['which']
    touch = local['touch']
    git = local['git']
    chmod = sudo[local['chmod']]


    _grass("Setting up ZSH")

    which_zsh = which['zsh'].run()[1].rstrip('\n')
    chsh['-s', which_zsh, SHELL_USER].run()
    chmod['-R', '755', '/usr/local/share'].run()

    _symlink_to_home('.profile')
    _symlink_to_home('.profile.private')

    # zsh shell
    _symlink_to_home('.zprofile')
    _symlink_to_home('.zsh_history')
    _symlink_to_home('.zshrc')
    _symlink_to_home('.warprc')
    _ok()

    _grass("Silencing macOS login MOTD")
    touch[_abspath('~/.hushlogin')].run()
    _ok()

    # https://github.com/gpakosz/.tmux
    _grass("Setting tmux")
    git['submodule', 'update', '--init', '--recursive']
    shutil.copy('.tmux/.tmux.conf', '.')
    _symlink_to_home('.tmux.conf')
    _symlink_to_home('.tmux.conf.local')
    _ok()

    _grass("Setting .ssh dir")
    _symlink_to_home('.ssh')
    _ok()


def check_sip(double_check=False):
    global SIP_ENABLED

    if SIP_ENABLED is None:
        csrutil = local['csrutil']
        check_sip = csrutil['status'].run(retcode=None)
        SIP_ENABLED = ("System Integrity Protection status: enabled." in check_sip[1])

    if SIP_ENABLED: _warn("SIP is enabled!")

    if SIP_ENABLED and double_check:
        if not _question("Do you want to continue with " + SNEK + " ? Some settings might be skipped.", yN=True):
            _warn("Restart your Mac. Hold down Command-R until you see an Apple icon and a progress bar. Go to Utilities > Terminal. Type `csrutil disable` and then restart.")
            _snek("Cya soon ... Hisss.")
            exit()

    return SIP_ENABLED


def update_osx():
    global USER_EMAIL, APPLE_ID_EMAIL
    softwareupdate = sudo[local['softwareupdate']]
    defaults = sudo[local['defaults']]
    mas = _local_with_brew_check('mas')


    _grass("Update macOS")
    _info("Enable software updates")
    defaults['write', '/Library/Preferences/com.apple.commerce', 'AutoUpdateRestartRequired', '-bool' 'true'].run()
    softwareupdate['--schedule', 'on'].run()
    _info("Check for software updates daily, not just once per week")
    defaults['write', '/Library/Preferences/com.apple.SoftwareUpdate', 'ScheduleFrequency', '-int', '1'].run()
    _info("Check for software updates now")
    softwareupdate['-i', '-a'].run()
    if mas is not None: mas['upgrade'].run()
    _ok()


def conf_osx__general():
    defaults = local['defaults']


    _grass("Set up System Preferences > General settings")

    _info("Set highlight color to green")
    defaults['write', 'NSGlobalDomain', 'AppleHighlightColor', '-string', '"0.764700 0.976500 0.568600"'].run()

    _info("Set sidebar icon size to medium")
    defaults['write', 'NSGlobalDomain', 'NSTableViewDefaultSizeMode', '-int', 2].run()

    _info("Show scroll bars when scrolling")
    # Possible values: `WhenScrolling`, `Automatic` and `Always`
    defaults['write', 'NSGlobalDomain', 'AppleShowScrollBars', '-string', '"WhenScrolling"'].run()

    _info("Jump to the spot that's clicked on scollbar")
    defaults['write', 'NSGlobalDomain', 'AppleScrollerPagingBehavior', '-int', 1].run()

    _info("Disable the “Are you sure you want to open this application?” dialog")
    defaults['write', 'com.apple.LaunchServices', 'LSQuarantine', '-bool', 'false'].run()

    _info("Set recent itens number to 5")
    defaults['write', 'NSGlobalDomain', 'NSRecentDocumentsLimit', 5].run()

    _info("Enable subpixel font rendering on non-Apple LCDs")
    defaults['write', 'NSGlobalDomain', 'AppleFontSmoothing', '-int', '2'].run()


    _ok()


def conf_osx__dock():
    defaults = local['defaults']
    dockutil = _local_with_brew_check('dockutil')


    _grass("Configuring Dock")

    _info("Set the icon size of Dock items to 45 pixels")
    defaults['write', 'com.apple.dock', 'tilesize', '-int', '45'].run()

    _info("Disable Dock icon magnification")
    defaults['write', 'com.apple.dock', 'magnification', '-bool', 'false'].run()

    _info("Set Dock to appear on the left")
    defaults['write', 'com.apple.dock', 'orientation', '-string', 'left'].run()

    _info("Change minimize/maximize window effect to genie")
    defaults['write', 'com.apple.dock', 'mineffect', '-string', 'genie'].run()

    _info("Double-click a window's title bar to zoom")
    defaults['write', 'NSGlobalDomain', 'AppleActionOnDoubleClick', '-string', 'Maximize'].run()

    _info("Minimize windows into their application’s icon")
    defaults['write', 'com.apple.dock', 'minimize-to-application', '-bool', 'true'].run()

    _info("Animate opening applications from the Dock")
    defaults['write', 'com.apple.dock', 'launchanim', '-bool', 'true'].run()

    _info("Autohide Dock")
    defaults['write', 'com.apple.dock', 'autohide', '-bool', 'true'].run()

    _info("Show indicator lights for open applications in the Dock")
    defaults['write', 'com.apple.dock', 'show-process-indicators', '-bool', 'true'].run()

    _info("Make Dock icons of hidden applications translucent")
    defaults['write', 'com.apple.dock', 'showhidden', '-bool', 'true'].run()

    #running "Remove the auto-hiding Dock delay"
    #defaults write com.apple.dock autohide-delay -float 0;ok

    #running "Remove the animation when hiding/showing the Dock"
    #defaults write com.apple.dock autohide-time-modifier -float 0;ok

    #running "Make Dock more transparent"
    #defaults write com.apple.dock hide-mirror -bool true;ok

    _info("Enable highlight hover effect for the grid view of a stack (Dock)")
    defaults['write', 'com.apple.dock', 'mouse-over-hilite-stack', '-bool', 'true'].run()

    _info("Enable spring loading for all Dock items")
    defaults['write', 'com.apple.dock', 'enable-spring-load-actions-on-all-items', '-bool', 'true'].run()

    dock_settings = _symlink_to_home('.macos_dock')

    _info("Setup docker icons")
    # tries to read file, if it doesnt exist we do nothing
    if dock_settings is None:
        _warn("No macOS dock settings found at '~/.macos_dock'. It might be your first setup. If its not, either run with 'dockutil' or wait for crontab task.")
    else:
        # reset first and then set everything
        dockutil['--remove', 'all', '--no-restart'].run()
        # count all the rows so we only restart finder on last one
        row_count = sum(1 for line in open(dock_settings,'r'))
        # open again but to execute commands
        with open(dock_settings,'r') as f:
            items = csv.reader(f, delimiter='\t')
            for i, line in enumerate(items, start=1):
                app_section = line[2].replace('persistent-','')

                # remove the file and spaces encoding
                app_path = line[1].replace('file://','').replace('%20',' ')
                # also remove the user path if it exists
                app_path = replace_user_path(app_path, USER_PATH)

                # add no-restart on every command except the last
                params = ['--add', app_path, '--section', app_section]
                if i < row_count: params.append('--no-restart')
                dockutil[params].run()

    _ok()


def conf_osx__mission_control():
    defaults = local['defaults']


    _grass("Configuring Mission Control")

    _info("Don’t automatically rearrange Spaces based on most recent use")
    defaults['write', 'com.apple.dock', 'mru-spaces', '-bool', 'false'].run()

    _info("Switch to space with open application")
    defaults['write', 'com.apple.dock', 'workspaces-auto-swoosh', '-bool', 'true'].run()

    _info("Disable group windows by application in Mission Control")
    # (i.e. use the old Exposé behavior instead)
    defaults['write', 'com.apple.dock', 'expose-group-by-app', '-bool', 'false'].run()

    _info("Disable Dashboard")
    defaults['write', 'com.apple.dashboard', 'mcx-disabled', '-bool', 'true'].run()

    _info("Don’t show Dashboard as a Space")
    defaults['write', 'com.apple.dock', 'dashboard-in-overlay', '-bool', 'true'].run()

    _info("Speed up Mission Control animations")
    defaults['write', 'com.apple.dock', 'expose-animation-duration', '-float', 0.1].run()

    # _info("Reset Launchpad, but keep the desktop wallpaper intact")
    # find "${HOME}/Library/Application Support/Dock" -maxdepth 1 -name "*-*.db" -delete

    # Hot Corners
    # Possible values:
    #  0: no-op
    #  2: Mission Control
    #  3: Show application windows
    #  4: Desktop
    #  5: Start screen saver
    #  6: Disable screen saver
    #  7: Dashboard
    # 10: Put display to sleep
    # 11: Launchpad
    # 12: Notification Center

    _info("Top left screen corner → Mission Control")
    defaults['write', 'com.apple.dock', 'wvous-tl-corner', '-int', 2].run()
    defaults['write', 'com.apple.dock', 'wvous-tl-modifier', '-int', 0].run()

    _info("Top right screen corner → Mission Control")
    defaults['write', 'com.apple.dock', 'wvous-tr-corner', '-int', 2].run()
    defaults['write', 'com.apple.dock', 'wvous-tr-modifier', '-int', 0].run()

    _info("Bottom left screen corner → Desktop")
    defaults['write', 'com.apple.dock', 'wvous-bl-corner', '-int', 4].run()
    defaults['write', 'com.apple.dock', 'wvous-bl-modifier', '-int', 0].run()

    _info("Bottom right screen corner → Desktop")
    defaults['write', 'com.apple.dock', 'wvous-br-corner', '-int', 4].run()
    defaults['write', 'com.apple.dock', 'wvous-br-modifier', '-int', 0].run()

    _ok()


def conf_osx__language():
    defaults = local['defaults']

    _grass("Configuring Language and Region")

    # Set language and text formats
    _info("Set language and text formats (english/en)")
    defaults['write', 'NSGlobalDomain', 'AppleLanguages', '-array', 'en-US', 'pt-US'].run()
    defaults['write', 'NSGlobalDomain', 'AppleLocale', '-string', 'en_US_POSIX@currency=EUR'].run()

    _info("Set Monday as the first day of the week")
    defaults['write', 'NSGlobalDomain', 'AppleFirstWeekday', '-dict', 'gregorian', '2'].run()

    _info("Set measurement units")
    defaults['write', 'NSGlobalDomain', 'AppleMeasurementUnits', '-string', 'Centimeters'].run()
    defaults['write', 'NSGlobalDomain', 'AppleMetricUnits', '-int', '1'].run()
    defaults['write', 'NSGlobalDomain', 'AppleTemperatureUnit', '-string', 'Celsius'].run()

    _info("Disable auto-correct")
    defaults['write', 'NSGlobalDomain', 'NSAutomaticSpellingCorrectionEnabled', '-bool', 'false'].run()

    _ok()


def conf_osx__sec():
    defaults = local['defaults']
    pmset = sudo[local['pmset']]
    spctl = sudo[local['spctl']]
    socketfilterfw = sudo[local['socketfilterfw']]


    _grass("Set Security and Privacy settings")
    #running "Never go into computer sleep mode"
    #sudo systemsetup -setcomputersleep Off > /dev/null;ok

    _info("Set standby to 24h")
    pmset['-a', 'standbydelay', '86400'].run()

    _info("Reveal IP, hostname, OS, etc. when clicking clock in login window")
    sudo[defaults['write', '/Library/Preferences/com.apple.loginwindow', 'AdminHostInfo', 'HostName']].run()

    _info("Require password immediately after sleep or screen saver begins")
    defaults['write', 'com.apple.screensaver', 'askForPassword', '-int', '1'].run()
    defaults['write', 'com.apple.screensaver', 'askForPasswordDelay', '-int', '0'].run()

    _info("Enable application from everywhere")
    spctl['--master-disable'].run()

    _info("Enable firewall ... better safe than sorry")
    socketfilterfw["--setglobalstate", "on"].run()
    sudo[defaults['write', '/Library/Preferences/com.apple.alf', 'globalstate', '-int', '1']].run()


    _ok()


def conf_osx__spotlight():
    defaults = local['defaults']
    killall = local['killall']
    mdutil = sudo[local['mdutil']]


    _grass("Configuring Spotlight settings")

    _info("Disable Spotlight indexing for any volume that gets mounted and has not yet been indexed")
    sudo[defaults['write', '/.Spotlight-V100/VolumeConfiguration', 'Exclusions', '-array', '/Volumes']].run()
    # Load new settings before rebuilding the index
    killall['msd'].run(retcode=None)
    # Make sure indexing is enabled for the main volume
    mdutil['-i', 'on'].run(retcode=None)
    # rebuild index
    mdutil['-E', '/'].run(retcode=None)

    _info("Change Spotlight indexing")
    SPOTLIGHT_INDEX_SETTINGS = {
        'APPLICATIONS': True,
        '"MENU_SPOTLIGHT_SUGGESTIONS"': True,
        '"MENU_CONVERSION"': True,
        '"MENU_EXPRESSION"': True,
        '"MENU_DEFINITION"': True,
        '"SYSTEM_PREFS"': True,
        'DOCUMENTS': True,
        'DIRECTORIES': True,
        'PRESENTATIONS': True,
        'SPREADSHEETS': True,
        'PDF': True,
        'MESSAGES': False,
        'CONTACT': False,
        '"EVENT_TODO"': False,
        'IMAGES': False,
        'BOOKMARKS': False,
        'MUSIC': False,
        'MOVIES': False,
        'FONTS': False,
        '"MENU_OTHER"': True,
    }
    # reset and set again
    defaults['delete', 'com.apple.Spotlight', 'orderedItems'].run()
    for name,enabled in SPOTLIGHT_INDEX_SETTINGS.items():
        defaults['write', 'com.apple.Spotlight', 'orderedItems', '-array-add', "'<dict><key>name</key><string>" + name + "</string><key>enabled</key> <" + str(int(enabled)) + "/></dict>'"].run()

    _ok()


def conf_osx__keyboard():
    defaults = local['defaults']
    plistbuddy = local['/usr/libexec/PlistBuddy']
    launchctl = local['launchctl']


    _grass("Setup Keyboard settings")

    _info("Disable smart quotes and dashes as they’re annoying when typing code")
    defaults['write', 'NSGlobalDomain', 'NSAutomaticQuoteSubstitutionEnabled', '-bool', 'false'].run()
    defaults['write', 'NSGlobalDomain', 'NSAutomaticDashSubstitutionEnabled', '-bool', 'false'].run()

    _info("Remove spotlight keyboard shortcut")
    plistbuddy[_abspath('~/Library/Preferences/com.apple.symbolichotkeys.plist'), '-c', 'Set AppleSymbolicHotKeys:64:enabled false'].run()

    _info("Stop iTunes from responding to the keyboard media keys")
    launchctl['unload', '-w', '/System/Library/LaunchAgents/com.apple.rcd.plist'].run()


    _ok()


def conf_osx__trackpad():
    defaults = local['defaults']


    _grass("Setup Trackpad settings")

    _info("Map bottom right corner to right-click")
    defaults['write', 'com.apple.driver.AppleBluetoothMultitouch.trackpad', 'TrackpadCornerSecondaryClick', '-int', '2'].run()
    defaults['write', 'com.apple.driver.AppleBluetoothMultitouch.trackpad', 'TrackpadRightClick', '-bool', 'true'].run()
    defaults['-currentHost', 'write', 'NSGlobalDomain', 'com.apple.trackpad.trackpadCornerClickBehavior', '-int', '1'].run()
    defaults['-currentHost', 'write', 'NSGlobalDomain', 'com.apple.trackpad.enableSecondaryClick', '-bool', 'true'].run()

    _info("Enable three finger tap (look up)")
    defaults['write', 'com.apple.driver.AppleBluetoothMultitouch.trackpad', 'TrackpadThreeFingerTapGesture', '-int', '2'].run()

    _info("Enable three finger drag")
    defaults['write', 'com.apple.driver.AppleBluetoothMultitouch.trackpad', 'TrackpadThreeFingerDrag', '-bool', 'true'].run()

    _info("Disable “natural” scrolling")
    defaults['write', 'NSGlobalDomain', 'com.apple.swipescrolldirection', '-bool', 'false'].run()

    _info("Zoom in or out")
    defaults['write', 'com.apple.driver.AppleBluetoothMultitouch.trackpad', 'TrackpadPinch', '-bool', 'true'].run()

    _info("Smart zoom, double-tap with two fingers")
    defaults['write', 'com.apple.driver.AppleBluetoothMultitouch.trackpad', 'TrackpadTwoFingerDoubleTapGesture', '-bool', 'true'].run()

    _info("Rotate")
    defaults['write', 'com.apple.driver.AppleBluetoothMultitouch.trackpad', 'TrackpadRotate', '-bool', 'true'].run()

    _info("Swipe between pages with two fingers")
    defaults['write', 'NSGlobalDomain', 'AppleEnableSwipeNavigateWithScrolls', '-bool', 'true'].run()

    _info("Swipe between full-screen apps with three fingers")
    defaults['write', 'com.apple.driver.AppleBluetoothMultitouch.trackpad', 'TrackpadThreeFingerHorizSwipeGesture', '-int', '2'].run()

    _info("Show Notification Center")
    defaults['write', 'com.apple.driver.AppleBluetoothMultitouch.trackpad', 'TrackpadTwoFingerFromRightEdgeSwipeGesture', '-int', '2'].run()

    _info("Show Mission Control")
    defaults['write', 'com.apple.dock', 'showMissionControlGestureEnabled', '-bool', 'true'].run()

    _info("Disable Show Expose")
    defaults['write', 'com.apple.dock', 'showAppExposeGestureEnabled', '-bool', 'false'].run()

    _info("Trackpad: Disable the Launchpad gesture (pinch with thumb and three fingers)")
    defaults['write', 'com.apple.dock', 'showLaunchpadGestureEnabled', '-int', '0'].run()

    _info("Enable Show Desktop")
    defaults['write', 'com.apple.dock', 'showDesktopGestureEnabled', '-bool', 'true'].run()

    _ok()


def conf_osx__timemachine():
    defaults = local['defaults']
    t_hash = local['hash']
    tmutil = local['tmutil']


    _grass("Configuring Time Machine")

    _info("Backup only when connected to AC")
    sudo[defaults["write", 'com.apple.TimeMachine', 'RequiresACPower', '-bool', 'true']].run()

    _info("Prevent Time Machine from prompting to use new hard drives as backup volume")
    defaults['write', 'com.apple.TimeMachine', 'DoNotOfferNewDisksForBackup', '-bool', 'true'].run()

    _ok()

def conf_osx__menubar():
    defaults = local['defaults']


    _grass("Configuring Menu bar")

    _info("Hide/show menubar itens")
    menu_bar_itens_visibility = {
        "NSStatusItem Visible Siri": False,
        "NSStatusItem Visible com.apple.menuextra.keychain": False,
        "NSStatusItem Visible com.apple.menuextra.airport": True,
        "NSStatusItem Visible com.apple.menuextra.battery": True,
        "NSStatusItem Visible com.apple.menuextra.clock": True,
        "NSStatusItem Visible com.apple.menuextra.textinput": True,
        "NSStatusItem Visible com.apple.menuextra.volume": True,
    }
    for entry,visibility in menu_bar_itens_visibility.items():
        defaults['write', 'com.apple.systemuiserver', entry, '-bool', str(visibility).lower()].run()


    _info("Set clock definitions")
    defaults['write', 'com.apple.menuextra.clock', 'IsAnalog', '-bool', 'false'].run()
    defaults['write', 'com.apple.menuextra.clock', 'FlashDateSeparators', '-bool', 'false'].run()
    defaults['write', 'com.apple.menuextra.clock', 'DateFormat', '-string', '"EEE d MMM  HH:mm"'].run()

    _info("Show percentage of batery")
    defaults['write', 'com.apple.menuextra.battery', 'ShowPercent', '-string', 'YES'].run()

    _info("Show VPN connected time")
    defaults['write', 'com.apple.networkConnect', 'VPNShowTime', '-bool', 'true'].run()

    _info("Disable menu bar transparency")
    defaults['write', 'NSGlobalDomain', 'AppleEnableMenuBarTransparency', '-bool', 'false'].run()

    _ok()


def conf_osx__login():
    defaults = local['defaults']


    _grass("Set login settings")

    _info("Disable guest account form login window")
    sudo[defaults['write', '/Library/Preferences/com.apple.loginwindow', 'GuestEnabled', '-bool', 'false']].run()

    _info("Enable auto-login at my user")
    sudo[defaults['write', '/Library/Preferences/com.apple.loginwindow', 'autoLoginUser', '-string', SHELL_USER]].run()

    _info("Set login itens")
    # waiting on PR: https://github.com/OJFord/loginitems/pull/2

    _ok()


def conf_osx__finder():
    defaults = local['defaults']
    lsregister = local['/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister']
    chflags = local['chflags']


    _grass("Set Finder settings")

    _info("Expand save panel by default")
    defaults['write', 'NSGlobalDomain', 'NSNavPanelExpandedStateForSaveMode', '-bool', 'true'].run()
    defaults['write', 'NSGlobalDomain', 'NSNavPanelExpandedStateForSaveMode2', '-bool', 'true'].run()

    _info("Expand print panel by default")
    defaults['write', 'NSGlobalDomain', 'PMPrintingExpandedStateForPrint', '-bool', 'true'].run()
    defaults['write', 'NSGlobalDomain', 'PMPrintingExpandedStateForPrint2', '-bool', 'true'].run()

    _info("Automatically quit printer app once the print jobs complete")
    defaults['write', 'com.apple.print.PrintingPrefs', '"Quit When Finished"', '-bool', 'true'].run()

    _info("Save to disk (not to iCloud) by default")
    defaults['write', 'NSGlobalDomain', 'NSDocumentSaveNewDocumentsToCloud', '-bool', 'false'].run()

    _info("Remove duplicates in the “Open With” menu (also see 'lscleanup' alias)")
    lsregister['-kill', '-r', '-domain', 'local', '-domain', 'system', '-domain', 'user'].run()

    _info("Show icons for external hard drives, servers, and removable media on the desktop")
    defaults['write', 'com.apple.finder', 'ShowExternalHardDrivesOnDesktop', '-bool', 'true'].run()
    defaults['write', 'com.apple.finder', 'ShowHardDrivesOnDesktop', '-bool', 'false'].run()
    defaults['write', 'com.apple.finder', 'ShowMountedServersOnDesktop', '-bool', 'true'].run()
    defaults['write', 'com.apple.finder', 'ShowRemovableMediaOnDesktop', '-bool', 'true'].run()

    _info("Hide recent tags from sidebar")
    defaults['write', 'com.apple.finder', 'ShowRecentTags', '-bool', 'false'].run()

    _info("Show all filename extensions")
    defaults['write', 'NSGlobalDomain', 'AppleShowAllExtensions', '-bool', 'true'].run()

    _info("Show status bar")
    defaults['write', 'com.apple.finder', 'ShowStatusBar', '-bool', 'true'].run()

    _info("Show path bar")
    defaults['write', 'com.apple.finder', 'ShowPathbar', '-bool', 'true'].run()

    _info("Allow text selection in Quick Look")
    defaults['write', 'com.apple.finder', 'QLEnableTextSelection', '-bool', 'true'].run()

    _info("Display full POSIX path as Finder window title")
    defaults['write', 'com.apple.finder', '_FXShowPosixPathInTitle', '-bool', 'true'].run()

    _info("When performing a search, search the current folder by default")
    defaults['write', 'com.apple.finder', 'FXDefaultSearchScope', '-string', 'SCcf'].run()

    _info("Disable the warning when changing a file extension")
    defaults['write', 'com.apple.finder', 'FXEnableExtensionChangeWarning', '-bool', 'false'].run()

    _info("Enable spring loading for directories")
    defaults['write', 'NSGlobalDomain', 'com.apple.springing.enabled', '-bool', 'true'].run()

    _info("Remove the spring loading delay for directories")
    defaults['write', 'NSGlobalDomain', 'com.apple.springing.delay', '-float', '0'].run()

    _info("Avoid creating .DS_Store files on network and USB volumes")
    defaults['write', 'com.apple.desktopservices', 'DSDontWriteNetworkStores', '-bool', 'true'].run()
    defaults['write', 'com.apple.desktopservices', 'DSDontWriteUSBStores', '-bool', 'true'].run()

    _info("Disable disk image verification")
    defaults['write', 'com.apple.frameworks.diskimages', 'skip-verify,' '-bool', 'true'].run()
    defaults['write', 'com.apple.frameworks.diskimages', 'skip-verify-locked,' '-bool', 'true'].run()
    defaults['write', 'com.apple.frameworks.diskimages', 'skip-verify-remote,' '-bool', 'true'].run()

    _info("Automatically open a new Finder window when a volume is mounted")
    defaults['write', 'com.apple.frameworks.diskimages', 'auto-open-ro-root,' '-bool', 'true'].run()
    defaults['write', 'com.apple.frameworks.diskimages', 'auto-open-rw-root,' '-bool', 'true'].run()
    defaults['write', 'com.apple.finder', 'OpenWindowForNewRemovableDisk', '-bool', 'true'].run()

    _info("Use list view in all Finder windows by default")
    # Four-letter codes for the other view modes: `icnv`, `clmv`, `Flwv`
    defaults['write', 'com.apple.finder', 'FXPreferredViewStyle', '-string', 'Nlsv'].run()

    #running "Disable the warning before emptying the Trash"
    #defaults write com.apple.finder WarnOnEmptyTrash -bool false;ok

    _info("Empty Trash securely by default")
    defaults['write', 'com.apple.finder', 'EmptyTrashSecurely', '-bool', 'true'].run()

    _info("Enable AirDrop over Ethernet and on unsupported Macs running Lion")
    defaults['write', 'com.apple.NetworkBrowser', 'BrowseAllInterfaces', '-bool', 'true'].run()

    _info("Show the ~/Library folder")
    chflags['nohidden', _abspath('~/Library')].run()

    _info("Expand the following File Info panes: “General”, “Open with”, and “Sharing & Permissions”")
    defaults['write', 'com.apple.finder', 'FXInfoPanesExpanded', '-dict', 'General', '-bool', 'true', 'OpenWith', '-bool', 'true', 'Privileges', '-bool', 'true'].run()

    _info("Save screenshots in PNG format (other options: BMP, GIF, JPG, PDF, TIFF)")
    defaults['write', 'com.apple.screencapture', 'type', '-string', 'png'].run()

    _info("Disable shadow in screenshots")
    defaults['write', 'com.apple.screencapture', 'disable-shadow', '-bool', 'true'].run()


    _ok()


def conf_osx__hardware():
    defaults =  local['defaults']
    pmset = sudo[local['pmset']]
    chflags = sudo[local['chflags']]
    rmrf = sudo[rm['-rf']]
    touch = sudo[local['touch']]
    killall = sudo[local['killall']]
    df = local['df']
    diskutil = local['diskutil']


    _grass("SSD tweaks")

    _info("Disable hibernation (speeds up entering sleep mode)")
    pmset['-a', 'hibernatemode', '0'].run()

    _info("Remove the sleep image file to save disk space")
    chflags['nouchg', '/private/var/vm/sleepimage'].run()
    rmrf['/private/var/vm/sleepimage'].run()
    # Create a zero-byte file instead
    touch['/private/var/vm/sleepimage'].run()
    # and make sure it can’t be rewritten
    chflags['uchg', '/private/var/vm/sleepimage'].run()

    _info("Disable the sudden motion sensor as it’s not useful for SSDs")
    pmset['-a', 'sms', '0'].run()

    # Restart automatically if the computer freezes
    # sudo systemsetup -setrestartfreeze on;ok

    _info("Disable automatic termination of inactive apps")
    defaults['write', 'NSGlobalDomain', 'NSDisableAutomaticTermination', '-bool', 'true'].run()

    _info("Disable the crash reporter")
    defaults['write', 'com.apple.CrashReporter', 'DialogType', '-string', 'none'].run()

    _ok()

    _grass("Bluetooth tweaks")

    sudo[defaults["write", "com.apple.Bluetooth", "ControllerPowerState", "-int", 0]].run()
    killall["-HUP", "blued"].run(retcode=None)

    _ok()

    _grass("Setup NTFS")

    if SIP_ENABLED:
        dev_entry = df['/'].run()[1].split('\n')[1].split(' ')[0]
        volume_name = diskutil['info', dev_entry].run()[1].split('Volume Name:')[1].split('\n',1)[0].strip()
        ntfs_file = "/Volumes/" + volume_name + "/sbin/mount_ntfs"
        sudo[mv[ntfs_file, ntfs_file+".orig"]].run()
        sudo[ln["-s", "/usr/local/sbin/mount_ntfs", ntfs_file]].run()

    _ok()


def conf_osx__other():
    defaults = local['defaults']
    app_open = local['open']
    launchctl = sudo[local['launchctl']]
    plutil = sudo[local['plutil']]

    _grass("Configuring other settings")

    _info("Allow 'locate' command")
    launchctl['load', '-w', '/System/Library/LaunchDaemons/com.apple.locate.plist'].run()

    _info("Fix for the ancient UTF-8 bug in QuickLook (http://mths.be/bbo)")
    # Commented out, as this is known to cause problems in various Adobe apps :(
    # See https://github.com/mathiasbynens/dotfiles/issues/237
    # sudo sh -c 'echo "0x08000100:0" > ~/.CFUserTextEncoding' 2> /dev/null;ok
    echo["0x08000100:0"] | sudo[tee['~/.CFUserTextEncoding']]

    _info("Increase window resize speed for Cocoa applications")
    defaults['write', 'NSGlobalDomain', 'NSWindowResizeTime', '-float', '0.001'].run()

    _info("Display ASCII control characters using caret notation in standard text views")
    # Try e.g. `cd /tmp; unidecode "\x{0000}" > cc.txt; open -e cc.txt`
    defaults['write', 'NSGlobalDomain', 'NSTextShowsControlCharacters', '-bool', 'true'].run()

    _info("Set Help Viewer windows to non-floating mode")
    defaults['write', 'com.apple.helpviewer', 'DevMode', '-bool', 'true'].run()

    _info("Play chime (iOS charging sound) when charging")
    defaults['write', 'com.apple.PowerChime', 'ChimeOnAllHardware', '-bool', 'true'].run()
    app_open['/System/Library/CoreServices/PowerChime.app'].run()

    # running "Disable repoen windows system-wide"
    # defaults write NSGlobalDomain NSQuitAlwaysKeepsWindows -bool false;ok
    # might want to enable this again and set specific apps that this works great for
    # e.g. defaults write com.microsoft.word NSQuitAlwaysKeepsWindows -bool true

    # _info("Remove all unavailable simulators from XCode")
    # xcrun simctl delete unavailable

    _info("Get SF Mono Fonts")
    cp.popen("-v /Applications/Utilities/Terminal.app/Contents/Resources/Fonts/SFMono-* " + _abspath("~/Library/Fonts"))

    _info("Disable Bonjour")
    sudo[defaults["write", "/System/Library/LaunchDaemons/com.apple.mDNSResponder.plist", "ProgramArguments", "-array-add", "-NoMulticastAdvertisements"]].run()

    _info("Disable Siri")
    plutil['-replace', 'Disabled', '-bool', 'true', '/System/Library/LaunchAgents/com.apple.Siri.agent.plist'].run()
    plutil['-replace', 'Disabled', '-bool', 'true', '/System/Library/LaunchAgents/com.apple.assistantd.plist'].run()

    _ok()


def conf_osx__extensions():
    duti = local['duti']

    _grass("Configuring applications to open certain files")

    duti["-s", "com.microsoft.VSCode", ".txt", "all"].run()

    _ok()


def conf_osx():
    killall = local['killall']
    app_open = local['open']


    _snek("Configuring macOS settings")

    _grass("Linking apps to /usr/local/bin")
    _create_symlink("/usr/libexec/ApplicationFirewall/socketfilterfw", "/usr/local/bin/socketfilterfw")
    _ok()

    _grass("Opening panels so they write default settings")
    app_open["/System/Library/PreferencePanes/Spotlight.prefPane/"].run()
    _ok()

    _warn("Killing 'System Preferences' to avoid settings from being overridden. Please do not open until reboot.")
    killall.run('System Preferences', retcode=None)
    _ok()

    conf_osx__general()
    conf_osx__dock()
    conf_osx__mission_control()
    conf_osx__language()
    conf_osx__sec()
    conf_osx__spotlight()
    conf_osx__keyboard()
    conf_osx__trackpad()
    conf_osx__timemachine()
    conf_osx__menubar()
    conf_osx__finder()
    conf_osx__hardware()
    conf_osx__extensions()
    conf_osx__other()


def macos_calendar():
    defaults = local['defaults']

    _grass("Set Calendar settings")

    _info("Show week numbers")
    defaults['write', 'com.apple.iCal', 'Show Week Numbers', '-bool', 'true'].run()

    _info("Show 7 days")
    defaults['write', 'com.apple.iCal', 'n days of week', '-int', '7'].run()

    _info("Week starts on monday")
    defaults['write', 'com.apple.iCal', 'first day of week', '-int', '1'].run()

    _info("Show event times")
    defaults['write', 'com.apple.iCal', 'Show time in Month View', '-bool', 'true'].run()

    _ok()


def macos_terminal():
    defaults = local['defaults']

    _grass("Configuring Calendar settings")

    _info("Only use UTF-8 in Terminal.app")
    defaults['write', 'com.apple.terminal', 'StringEncodings', '-array', 4].run()

    _info("Set the 'Pro' as the default")
    defaults['write', 'com.apple.Terminal', '"Startup Window Settings"', '-string', '"Pro"'].run()
    defaults['write', 'com.apple.Terminal', '"Default Window Settings"', '-string', '"Pro"'].run()

    _ok()


def macos_activitymonitor():
    defaults = local['defaults']


    _grass("Configuring Activity Monitor")

    _info("Show the main window when launching Activity Monitor")
    defaults['write', 'com.apple.ActivityMonitor', 'OpenMainWindow', '-bool', 'true'].run()

    _info("Visualize CPU usage in the Activity Monitor Dock icon")
    defaults['write', 'com.apple.ActivityMonitor', 'IconType', '-int', '5'].run()

    _info("Show all processes in Activity Monitor")
    defaults['write', 'com.apple.ActivityMonitor', 'ShowCategory', '-int', '0'].run()

    _info("Sort Activity Monitor results by CPU usage")
    defaults['write', 'com.apple.ActivityMonitor', 'SortColumn', '-string', '"CPUUsage"'].run()
    defaults['write', 'com.apple.ActivityMonitor', 'SortDirection', '-int', '0'].run()

    _ok()


def macos_textedit():
    defaults = local['defaults']


    _grass("Configuring TextEdit")

    _info("Use plain text mode for new TextEdit documents")
    defaults['write', 'com.apple.TextEdit', 'RichText', '-int', 0].run()

    _info("Open and save files as UTF-8 in TextEdit")
    defaults['write', 'com.apple.TextEdit', 'PlainTextEncoding', '-int', 4].run()
    defaults['write', 'com.apple.TextEdit', 'PlainTextEncodingForWrite', '-int', 4].run()

    _ok()


def google_chrome():
    defaults = local['defaults']
    openapp = local["open"]


    _grass("Setting up >Google Chrome<")

    _info("Opening Chrome for you to setup your account")
    openapp['/Applications/Google Chrome.app'].run()
    _wait_for_file(_user_defaults('com.google.Chrome'))

    _info("Allow installing user scripts via GitHub Gist")
    defaults['write', 'com.google.Chrome', 'ExtensionInstallSources', '-array', "https://gist.githubusercontent.com/"].run()

    _info("Use the system-native print preview dialog")
    defaults['write', 'com.google.Chrome', 'DisablePrintPreview', '-bool', 'true'].run()

    _info("Expand the print dialog by default")
    defaults['write', 'com.google.Chrome', 'PMPrintingExpandedStateForPrint2', '-bool', 'true'].run()

    _ok()


def iterm():
    defaults = local['defaults']
    openapp = local["open"]


    _grass("Setting iTerm2")

    _info("Opening iTerm2 for you to setup your profile")
    openapp['/Applications/iTerm.app'].run()

    # _wait_for_file("~/Library/Preferences/com.googlecode.iterm2.plist")

    _ok()


def vscode():
    openapp = local['open']
    vscode = local['code']


    _grass("Set Visual Studio Code settings")

    _info("Waiting for VSCode binaries to be available ...")
    _wait_for_file("/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code")

    _info("Installing Settings Sync extension")
    sync_extensionid = 'Shan.code-settings-sync'

    # if not in current extensions try to install it
    if sync_extensionid not in vscode['--list-extensions'].run()[1]:
        _info("Waiting for Settings Sync extension to be installed ...")
        openapp["vscode:extension/" + sync_extensionid].run()
        while sync_extensionid not in vscode['--list-extensions'].run()[1]:
            time.sleep(1)

    vscodedir_path = os.path.join(USER_PATH, "Library/Application Support/Code/User/")
    _info("Symlink Settings Sync local settings file")
    local_settings_filepath = os.path.join(vscodedir_path, "syncLocalSettings.json")
    _create_symlink("./vscode_sync_settings.json", local_settings_filepath)

    _info("Check if Settings Sync VSCode settings are set")
    vscode_settings_filepath = os.path.join(vscodedir_path, "settings.json")

    # make sure the settings file exists
    open(vscode_settings_filepath, 'a').close()

    # write the gist id to the file
    with open(vscode_settings_filepath, 'r+') as vsf, open(local_settings_filepath, 'r') as syncf:
        local_settings_json = json.load(syncf)
        # loads settings even if empty file
        try:
            vscode_settings_json = json.load(vsf)
        except ValueError:
            vscode_settings_json = {}

        # write the sync settings token into the vscode settings
        vscode_settings_json['sync.gist'] = local_settings_json['gist']
        vsf.seek(0)
        json.dump(vscode_settings_json, vsf, indent=4)
        vsf.truncate()

    _ok()


def transmission():
    defaults = local['defaults']


    _grass("Setting up >Transmission<")

    _info("Use '~/Downloads' to store incomplete downloads")
    defaults['write', 'org.m0k.transmission', 'UseIncompleteDownloadFolder', '-bool', 'true'].run()
    defaults['write', 'org.m0k.transmission', 'IncompleteDownloadFolder', '-string', os.path.join(USER_PATH, "Downloads")].run()

    _info("Do not prompt for confirmation before downloading")
    defaults['write', 'org.m0k.transmission', 'DownloadAsk', '-bool', 'false'].run()

    _info("Trash original torrent files")
    defaults['write', 'org.m0k.transmission', 'DeleteOriginalTorrent', '-bool', 'true'].run()

    _info("Hide the donate message")
    defaults['write', 'org.m0k.transmission', 'WarningDonate', '-bool', 'false'].run()

    _info("Hide the legal disclaimer")
    defaults['write', 'org.m0k.transmission', 'WarningLegal', '-bool', 'false'].run()

    _ok()


def mendeley():
    defaults = local['defaults']


    _grass("Setting up >Mendeley<")

    _info("Enabling Bibtex sync")
    defaults["write", "com.mendeley.Mendeley Desktop", "BibtexSync.enabled", "-bool", "true"].run()

    _info("Escape special charts")
    defaults["write", "com.mendeley.Mendeley Desktop", "Bibtex.escapeSpecialChars", "-bool", "true"].run()

    _info("Disable publication abbreviations")
    defaults["write", "com.mendeley.Mendeley Desktop", "Bibtex.usePublicationAbbreviations", "-bool", "false"].run()

    _info("Setting Bibtex sync as a one-file type")
    defaults["write", "com.mendeley.Mendeley Desktop", "BibtexSync.syncMode", "-string", "SingleFile"].run()

    _info("Setting Bibtex sync folder")
    defaults["write", "com.mendeley.Mendeley Desktop", "BibtexSync.path", "-string", "~/Dropbox/PhD Loff/rw"].run()

    _ok()


def unarchiver():
    defaults = local['defaults']


    _grass("Setting up >The Unarchiver<")

    _info("Set to extract archives to same folder as the archive")
    defaults["write", "cx.c3.theunarchiver", "extractionDestination", "-int", "1"].run()

    _info("Set the modification date of the created folder to the modification date of the archive file")
    defaults["write", "cx.c3.theunarchiver", "folderModifiedDate", "-int", "2"].run()

    _info("Delete archive after extraction")
    defaults["write", "cx.c3.theunarchiver", "deleteExtractedArchive", "-bool", "true"].run()

    _info("Do not open folder afer extraction")
    defaults["write", "cx.c3.theunarchiver", "openExtractedFolder", "-bool", "false"].run()

    _ok()


def alfred():
    openapp = local['open']


    _grass("Setting up >Alfred<")

    # check if alfred is installed
    _download_file('https://github.com/packal/repository/raw/master/com.shawn.patrick.rice.caffeinate.control/caffeinate_control.alfredworkflow','/tmp/')
    openapp['/tmp/caffeinate_control.alfredworkflow'].run()

    _ok()


def bartender():
    _grass("Setting up >Bartender<")
    _ok()


def conf_apps():

    _snek("Configuring Applications")

    macos_calendar()
    macos_terminal()
    macos_activitymonitor()
    macos_textedit()
    google_chrome()
    iterm()
    vscode()
    transmission()
    mendeley()
    unarchiver()


def teardown():
    brew = local['brew']
    killall = local['killall']

    _snek("Tearing down ...")

    # Remove outdated versions from the cellar
    _grass("Cleaning up homebrew cache")
    brew['cleanup'] & FG
    brew['cask','cleanup'] & FG
    _ok()

    _grass("Killing affected applications (so they can reboot)....")
    APPS_TO_KILL=[
        "Activity Monitor", "Address Book", "Calendar", "Contacts", "cfprefsd",
        "Dock", "Finder", "Mail", "Messages", "SystemUIServer", "iCal", "Transmission",
        "Visual Studio Code", "The Unarchiver",
    ]
    for app in APPS_TO_KILL:
        _info("Killing " + app + " ... ", end='', flush=True)
        ret = killall[app].run(retcode=None)
        # get all return strings, write done if no string was there
        ret = ret[2].rstrip("\n")
        if not ret: ret = 'done'
        print(ret)
    _ok()

    _snek("Unfortunately I can't setup everything :( Heres a list of things you need to manually do.")
    post_mortem = """
        Set Finder settings:
            - Remove 'All My Files', 'Movies', 'Music' and 'Pictures' from sidebar
            - Add folders to sidebar: 'PhD', 'Code'

        Set Network settings:
            - Add University VPN

        Set iCloud settings:
            - Disable Safari and Mail sync
            - Sign in for Facebook, Twitter, Linkedin, Google (Only select contacts)

        Set Dropbox configuration:
            - Show desktop notifications
            - Start dropbox on system startup
            - Selective Sync folders
            - Do not enable camera uploads
            - Share screenshots using Dropbox
            - Enable LAN sync

        Set Mendeley configuration:
            - File Organizer > Organize my files: ~/Drive/phd/rw
            - File Organizer > Sort files into subfolders > Folder path: Year
            - File Organizer > Rename document files > Filename: Author Year Title
    """

    # print and save to file


def cron_tasks():
    docker = local['docker']
    brew = local['brew']
    git = local['git']
    dockutil = local['dockutil']

    update_gitignore()
    update_osx()

    # Docker
    _grass("Clean up Docker")
    print(check_output_zsh('source ' + _abspath('~/.profile') + ' ; docker clean'))
    _ok()

    # Brew
    _grass("Update Homebrew")
    brew["update"] & FG
    brew["upgrade", "--all"] & FG
    brew["cleanup"] & FG
    brew["bundle", "dump", "--file=.Brewfile", "--force"] & FG
    git['submodule', 'update', '--init', '--recursive'] & FG
    _ok()

    # Backup Tasks
    _grass("Execute backup tasks")
    with open('.macos_dock', 'w+') as f:
        f.write(dockutil['--list'].run()[1])
    _ok()


if __name__ == '__main__':
    installed_packages = install_pip_packages()

    # parse some flags
    # TODO: flags from init have to come here as well
    parser = argparse.ArgumentParser()
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--update', action='store_true')
    parser.add_argument('--method', type=str)
    args = parser.parse_args()

    # import only after we install the pip packages
    import requests
    from plumbum import local, FG, BG, TF, RETCODE
    from plumbum.cmd import sudo, true, rm, ln, echo, tee, cp, mv, ls, find, grep, readlink

    # if only one function was called
    if args.method:
        print(locals()[args.method]())
        exit(0)

    _snek("Starting! Hissss...")

    # start caffeine so computer doesnt go to sleep
    caffeinate = local["caffeinate"]
    caff = caffeinate.popen("-i -d")

    if args.update:
        update_gitignore()
        update_osx()


    check_sip(double_check=False)
    update_osx()
    personal_info()
    git()
    brew()
    shell()
    conf_osx()
    conf_apps()
    teardown()

    # uninstall pip packages
    uninstall_pip_packages(installed_packages)
    caff.terminate()

    _grass("Note that some of these changes require a logout/restart to take effect.")
    _grass("You should also NOT open System Preferences. It might overwrite some of the settings.")
    _snek("Hissss. All done!")