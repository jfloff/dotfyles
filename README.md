# :snake: dotfyles: the python-based dotfiles

I will update your OSX machine with better system defaults, preferences, software configuration and even auto-install some handy development tools and apps I find helpful.

You don't need to install or configure anything upfront! This works with a brand-new machine as well as an existing machine that you've been working with for years.

*Forget About Manual Configuration!*

Don't you hate getting a new laptop or formatting your existing one and then spending a whole day setting up your system preferences and tools? Me too. That's why we automate; we did it once and we don't want to do have to do it again.

# Running

First you should fork this repo and add private information in a cloud storage (I use Google Drive). Perhaps the quickest way to double check some of the private preferences that you might miss, is to open the `.gitignore` so you can see what I've put there

In case you don't like anything I do and want to set your own preferences (and pull request them)!

```bash
curl -#LS https://raw.githubusercontent.com/jfloff/dotfyles/master/init.sh | bash
```

This will work even in a brand new Mac with no git installed.

> Note: running init.sh is idempotent. You can run it again and again as you add new features or software to the scripts! I'll regularly add new configurations so keep an eye on this repo as it grows and optimizes.

# Watch me run!
[![asciicast](https://asciinema.org/a/RiuoZUJUYVJ9hOypxhC33swWK.png)](https://asciinema.org/a/RiuoZUJUYVJ9hOypxhC33swWK)

# ¯\\_(ツ)_/¯ Warning / Liability
> Warning:
The creator of this repo is not responsible if your machine ends up in a state you are not happy with. If you are concerned, look at the scripts to review everything this script will do to your machine :)

# Contributions
Contributions are always welcome in the form of pull requests with explanatory comments.