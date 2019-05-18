#!/usr/bin/env bash

#########################################################################
# Colors
ESC_SEQ="\x1b["
COL_RESET=$ESC_SEQ"39;49;00m"
COL_GREEN=$ESC_SEQ"32;01m"
COL_MAGENTA=$ESC_SEQ"35;01m"
COL_CYAN=$ESC_SEQ"36;01m"
COL_YELLOW=$ESC_SEQ"33;01m"
SNAKE="\xF0\x9F\x90\x8D"
GRASS="\xF0\x9F\x8C\xBF"
WARN="\xE2\x9A\xA0"

function clean_stdin() {
  while read -e -t 1; do : ; done
}

function snek() {
  echo -e "$SNAKE Hiss. " $1
}

function grass() {
  echo -e "$GRASS " $1
}

function ok() {
  echo -e "$COL_GREEN[ok]$COL_RESET "$1
}

function question() {
  clean_stdin
  echo -en "$COL_MAGENTA ¿$COL_RESET" $1 " "
  read -rp "" ret
  eval "$2=\$ret"
}

function msg() {
  echo -en "$COL_CYAN ¡$COL_RESET "$1" "
}

function warn() {
  echo -en "$COL_YELLOW $WARN $COL_RESET "$1" "
}

snek "I'm here to make your OSX a better system!"

snek "Setting up basic settings for me to run correctly."

SIP_ENABLED=0
if csrutil status | grep -q 'System Integrity Protection status: enabled.'; then
  question "SIP is enabled. Do you want to continue with $SNAKE ? Some settings might be skipped. [y|N]" response
  if [[ $response =~ ^(no|n|N) ]];then
    warn "Restart your Mac. Hold down Command-R until you see an Apple icon and a progress bar. Go to Utilities > Terminal. Type `csrutil disable` and then restart."
    exit 1
  fi
fi

grass "Installing command line tools ..."
if [ ! -x "$(command -v git)" ]; then
    # keeps system alive
    caffeinate -i -d &
    caff_pid=$!

    # install command line tools so we have git
    # loops while we don't have the tools installed
    while true; do
        xcode-select --install > /dev/null 2>&1
        sleep 5
        xcode-select -p > /dev/null 2>&1
        [ $? == 2 ] || break
    done

    # kills caffeinate, theres already one running inside install.sh
    kill -INT $caff_pid
fi
ok

# clone main repo
# this repo will be synchronized with code/dotyfiles on a regular basis
# git clone --recurse-submodules https://github.com/jfloff/dotfyles ~/.dotfyles > /dev/null 2>&1

# install brew
grass "Installing homebrew ..."
if [ ! -x "$(command -v brew)" ]; then
  # redirect input so we bypass the prompt: http://stackoverflow.com/a/25535532/1700053
  ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)" </dev/null
fi
ok

# get lists of brews and casks already installed
brew_list=$(brew list)
brew_cask_list=$(brew cask list)

grass "Installing python ..."
if [[ $brew_list != *python* ]]; then
  brew install python
fi
ok

grass "Installing Google Backup and Sync ..."
if ! open -Ra "Backup and Sync" ; then
  brew cask install google-backup-and-sync
fi
ok

# source some vars such as the google drive path
grass "Checking for \$DOTFYLES_GDRIVE_PATH variable ..."
source .profile
if [ -z "$DOTFYLES_GDRIVE_PATH" ]; then
  warn "You have to set the \$DOTFYLES_GDRIVE_PATH variable with the path for your dotfyles folder"
  exit
fi
ok

grass "Waiting for '$DOTFYLES_GDRIVE_PATH' to be synced by Google Drive ..."
while [ ! -f "$DOTFYLES_GDRIVE_PATH/dotfyles.py" ]; do
  sleep 1
done
ok

# set input from the terminal
python $DOTFYLES_GDRIVE_PATH/dotfyles.py < /dev/tty