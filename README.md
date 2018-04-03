Alfred the butler
=================

Willie has left, he's now in Scotland. Alfred replaced him.

This is a flake8 plugin to warn on unsafe/obsolete symbols. Example
configuration in your project's setup.cfg:

```ini
[flake8]
enable-extensions = B1
warn-symbols =
    obsolete_module = I am a warning message ! This module is obsolete !
    module.obsolete_function = Still a warning ! This function is obsolete !
    module.submodule.constant = Warning, this variable will be removed !
```
