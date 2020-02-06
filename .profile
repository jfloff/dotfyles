#############################################################
# Generic configuration that applies to all shells
#############################################################

# path to google drive folder with the dotfyles path
export DOTFYLES_GDRIVE_PATH="/Users/jfloff/Drive/code/dotfyles"

#############################################################
# PRIVATE INFO
#
# skips if the file doesnt exist
if [ -f ~/.profile.private ]; then
  source ~/.profile.private
fi


#############################################################
# SHELL PATHS
#
# add Brew paths
export PATH=/usr/local/sbin:$PATH
export PATH=/usr/local/bin:$PATH
# for homebrew python
export PATH=/usr/local/opt/python/libexec/bin:$PATH
# for jenv
export PATH=$HOME/.jenv/bin:$PATH
# for vscode
export PATH="$PATH:/Applications/Visual Studio Code.app/Contents/Resources/app/bin"
# for coreutils
# bug with Google Drive File Stream and the gnu utils
# disabling this for now
# export PATH=/usr/local/opt/coreutils/libexec/gnubin:$PATH
# export MANPATH=/usr/local/opt/coreutils/libexec/gnuman:$MANPATH
# for findutils
export PATH=/usr/local/opt/findutils/libexec/gnubin:$PATH
export MANPATH=/usr/local/opt/findutils/libexec/gnuman:$MANPATH


#############################################################
# VARS
#
# set brew cask default application dir
export HOMEBREW_CASK_OPTS='--appdir=/Applications'
# set code as the default editor
export EDITOR='code --wait'
# set antigen path
export ADOTDIR=$HOME/.dotfiles/antigen
# Init jenv
if [ -x "$(command -v jenv)" ]; then
  eval "$(jenv init -)"
fi

#############################################################
# SHELL ALIAS
#
alias edit="${EDITOR} $1"

# Detect which `ls` flavor is in use
if ls --color > /dev/null 2>&1; then # GNU `ls`
  colorflag="--color"
else # OS X `ls`
  colorflag="-G"
fi

# Enable aliases to be sudo’ed
alias sudo='sudo '

# Stopwatch
alias timer='ttimer'

# Recursively delete `.DS_Store` files
alias dscleanup="find . -type f -name '*.DS_Store' -ls -delete"

# Empty the Trash on all mounted volumes and the main HDD.
# Also, clear Apple’s System Logs to improve shell startup speed.
# Finally, clear download history from quarantine. https://mths.be/bum
alias emptytrash="sudo rm -rfv /Volumes/*/.Trashes; sudo rm -rfv ~/.Trash; sudo rm -rfv /private/var/log/asl/*.asl; sqlite3 ~/Library/Preferences/com.apple.LaunchServices.QuarantineEventsV* 'delete from LSQuarantineEvent'"

# Merge PDF files
# Usage: `mergepdf -o output.pdf input{1,2,3}.pdf`
alias mergepdf='/System/Library/Automator/Combine\ PDF\ Pages.action/Contents/Resources/join.py'

# Disable Spotlight
alias spotoff="sudo mdutil -a -i off"

# Kill all the tabs in Chrome to free up memory
# [C] explained: http://www.commandlinefu.com/commands/view/402/exclude-grep-from-your-grepped-output-of-ps-alias-included-in-description
alias chromekill="ps ux | grep '[C]hrome Helper --type=renderer' | grep -v extension-process | tr -s ' ' | cut -d ' ' -f2 | xargs kill"

# Lock the screen (when going AFK)
alias afk="/System/Library/CoreServices/Menu\ Extras/User.menu/Contents/Resources/CGSession -suspend"

# IP addresses
alias ip="dig +short myip.opendns.com @resolver1.opendns.com"
alias localip="ipconfig getifaddr en1"
alias ips="ifconfig -a | grep -o 'inet6\? \(addr:\)\?\s\?\(\(\([0-9]\+\.\)\{3\}[0-9]\+\)\|[a-fA-F0-9:]\+\)' | awk '{ sub(/inet6? (addr:)? ?/, \"\"); print }'"

# Remove all items safely, to Trash
alias rrm='rm'
alias rm='trash'

# Detect which `ls` flavor is in use
if ls --color > /dev/null 2>&1; then # GNU `ls`
  colorflag="--color"
else # OS X `ls`
  colorflag="-G"
fi
# Always use color output for `ls`
alias ls="command ls ${colorflag}"

# brew ctags default to brew one
alias ctags="`brew --prefix`/bin/ctags"

# maven uses 1 thread per core per default
alias mvn="mvn -T 1C"

# sudo find to avoid permission denied warnings
alias sufind="sudo find"

alias sane="stty sane"

alias wd="wdx"


#############################################################
# FUNCTIONS
#
# kill all instances of a process by name
function skill()
{
    sudo kill -9 `ps ax | grep $1 | grep -v grep | awk '{print $1}'`
}

# know path to app
# https://stackoverflow.com/a/12900116/1700053
function whichapp()
{
  local appNameOrBundleId=$1 isAppName=0 bundleId
  # Determine whether an app *name* or *bundle ID* was specified.
  [[ $appNameOrBundleId =~ \.[aA][pP][pP]$ || $appNameOrBundleId =~ ^[^.]+$ ]] && isAppName=1
  if (( isAppName )); then # an application NAME was specified
    # Translate to a bundle ID first.
    bundleId=$(osascript -e "id of application \"$appNameOrBundleId\"" 2>/dev/null) ||
      { echo "$FUNCNAME: ERROR: Application with specified name not found: $appNameOrBundleId" 1>&2; return 1; }
  else # a BUNDLE ID was specified
    bundleId=$appNameOrBundleId
  fi
    # Let AppleScript determine the full bundle path.
  osascript -e "tell application \"Finder\" to POSIX path of (get application file id \"$bundleId\" as alias)" 2>/dev/null ||
    { echo "$FUNCNAME: ERROR: Application with specified bundle ID not found: $bundleId" 1>&2; return 1; }
}

# know path to bundleid
# https://stackoverflow.com/a/12900116/1700053
function bundleid()
{
  osascript -e "id of application \"$1\"" 2>/dev/null ||
    { echo "$FUNCNAME: ERROR: Application with specified name not found: $1" 1>&2; return 1; }
}

#############################################################
# JENV
#

#########################################
# emulates the commands below like they would natively be in docker
function jenv() {
  if command -v "jenv-$1" > /dev/null 2>&1; then
    subcommand=$1
    shift
    jenv-$subcommand $@
  else
    /usr/local/bin/jenv $@
  fi
}

# add all
function jenv-add-all() {
  for java_dir in /Library/Java/JavaVirtualMachines/*; do
    jenv add --complete "$java_dir/Contents/Home/"
  done
}

#############################################################
# DOCKER
#

#########################################
# emulates the commands below like they would natively be in docker
# docker clean -- runs --> docker-clean
# etc
docker() {
  if command -v "docker-$1" > /dev/null 2>&1; then
    subcommand=$1
    shift
    docker-$subcommand $@
  else
    /usr/local/bin/docker $@
  fi
}

# cleans untagged images
# cleans dangling volumes
docker-clean() {
  # dependant images can be released after the original are deleted
  # cleans all those scenarios
  while : ; do
    IMAGE_IDS=$(docker images | grep \<none\> | awk '{print $3}')
    NUM_IMAGES=$(echo $IMAGE_IDS | sed '/^\s*$/d' | wc -l | xargs)
    [[ $NUM_IMAGES != 0 ]] || break
    printf '%s\n' "$IMAGE_IDS" | while IFS= read -r i; do docker rmi -f $i; done
  done
  for i in `docker volume ls -qf dangling=true`; do docker volume rm $i; done
}

# stop and remove container
docker-strm() {
  docker stop $@
  docker rm $@ 1> /dev/null
}

# get ip of container
docker-ip() {
  docker inspect --format '{{ .NetworkSettings.IPAddress }}' $1
}

docker-rme() {
  echo -n "Are you sure you want to remove all exited Docker containers? [y|N] "
  read response
  if [[ $response =~ ^(y|yes|Y) ]]; then
    docker rm $(docker ps --all -q -f status=exited)
  fi
}

_rmcontainers() {
  #docker rm $(docker ps -a -q)
  if [[ $(docker ps -a -q) ]]; then
    for i in `docker ps -a -q|awk '{print $1}'`; do
      docker stop $i
      docker rm -f $i
    done
  fi
}

_rmimages() {
  #docker rmi $(docker images -q)
  if [[ $(docker images -q) ]]; then
    #docker rmi $(docker images -qa)
    for i in `docker images -q|awk '{print $1}'`; do
      docker rmi -f $i
    done
  fi
}

_rmvolumes() {
  # remove all volumes
  if [[ $(docker volume ls -q) ]]; then
    for i in `docker volume ls -q|awk '{print $1}'`; do
      docker volume rm $i
    done
  fi
}

# purges all images and containers
docker-purgei() {
  echo -n "Are you sure you want to purge Docker images? This will delete all images and volumes! [y|N] "
  read response
  if [[ $response =~ ^(y|yes|Y) ]]; then
    _rmimages
    _rmvolumes
  fi
}

docker-purgep() {
  echo -n "Are you sure you want to purge Docker containers? This will delete all containers! [y|N] "
  read response
  if [[ $response =~ ^(y|yes|Y) ]];then
    _rmcontainers
  fi
}

# purges all images and containers
docker-purge() {
  echo -n "Are you sure you want to purge Docker? This will delete all containers, volumes and images! [y|N] "
  read response
  if [[ $response =~ ^(y|yes|Y) ]];then
    _rmcontainers
    _rmimages
    _rmvolumes
  fi
}
