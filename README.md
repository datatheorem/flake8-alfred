Alfred the butler
=================

Alfred is a flake8 plugin to warn on unsafe/obsolete symbols. Example
configuration in your project's `setup.cfg` (also works with `.flake8`):

```ini
[flake8]
enable-extensions = B1
warn-symbols =
    obsolete_module = Warning! This module is obsolete!
    module.obsolete_function = Warning! This function is obsolete!
    module.submodule.constant = Warning! this variable will be removed!
```

You can also enable this using flake8's command line options:

```bash
$ flake8 --enable-extensions=B1 --warn-symbols=$'obsolte_module=Warning!\nmodule.obsolete_function=Warning!'
```
