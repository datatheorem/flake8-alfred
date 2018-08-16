Alfred the butler
=================

[![Build Status](https://travis-ci.org/datatheorem/flake8-alfred.svg?branch=master)](https://travis-ci.org/datatheorem/flake8-alfred)
[![PyPI version](https://badge.fury.io/py/flake8-alfred.svg)](https://badge.fury.io/py/flake8-alfred)

Alfred is a flake8 plugin to warn on unsafe/obsolete symbols. You can use it as
a transition tool to eliminate functions, modules, variables you don't want in
existing project or you want to avoid in new ones. This plugin requires Python 3.6.

Getting Started
---------------

First, install Alfred using pip:

```bash
$ pip install flake8-alfred
```

Then, enable the plugin by configuring a blacklist of Python symbols that should
be flagged by flake8. Here is an example of configuration in your project's `setup.cfg`:

```ini
[flake8]
enable-extensions = B1
warn-symbols =
    obsolete_module = Warning! This module is obsolete!
    module.obsolete_function = Warning! This function is obsolete!
    module.submodule.constant = Warning! this variable will be removed!
```

Here `enable-extensions` tells flake8 to enable this plugin and `warn-symbols` is
the list of symbols we want to flag in our project, with the associated
warning. By default, this plugin doesn't warn about any other symbol.


If you just want to test/run once, you can also pass the configuration directly
to flake8:

```bash
$ flake8 --enable-extensions=B1 --warn-symbols=$'obsolte_module=Warning!\nmodule.obsolete_function=Warning!'
```

Local Development
-----------------

First, clone the repository:

```bash
git clone https://github.com/datatheorem/alfred-checker.git
```

The project uses pipenv to manage dependencies:

```bash
$ pipenv install --dev
```

Then, the test suite can be run:

```bash
$ pipenv run pytest
```
