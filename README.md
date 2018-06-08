Alfred the butler
=================

Alfred is a flake8 plugin to warn on unsafe/obsolete symbols. You can use it as
a transition tools to eliminate functions, modules, variables you don't want in
existing project or you want to avoid in new ones.

Cloning/Installation
--------------------

First, clone the repository:

```bash
# Clone
https://github.com/datatheorem/alfred-checker.git
```

Then, if you want to install the plugin on your user-specific directories, run
this command:

```bash
python3 setup.py install --user
```

If you want to install it on your system directories and make it available to
all the users, run this command:

```bash
python3 setup.py install
```

You can also use pipenv to setup a more reproductible environment, but the
setup.py install should be sufficient most of the time:

```bash
pipenv install
```

Configuration
-------------

By default, this plugin do nothing, you have to configure your project to
enable it. Also no symbols are source of warnings by default.

Here's an example of configuration in your project's `setup.cfg` (also works
with `.flake8`):

```ini
[flake8]
enable-extensions = B1
warn-symbols =
    obsolete_module = Warning! This module is obsolete!
    module.obsolete_function = Warning! This function is obsolete!
    module.submodule.constant = Warning! this variable will be removed!
```

Here enable-extensions tells flake8 to enable this plugin and warn-symbols is
the list of symbols we want to avoid in our project, with the associated
warning. By default, this plugin doesn't warn about any symbol.

If you just want to test/run once, you can also pass the configuration directly
to flake8:

```bash
$ flake8 --enable-extensions=B1 --warn-symbols=$'obsolte_module=Warning!\nmodule.obsolete_function=Warning!'
```
