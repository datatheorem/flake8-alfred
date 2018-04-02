Willie the janitor
==================

Flake8 plugin to warn on unsafe/obsolete symbols.

Configuration in your project's setup.cfg:

.. code-block:: ini

    [flake8]
    enable-extensions = B1
    warn-symbols =
        obsolete_module = This module is obsolete !
        module.obsolete_function = This function is obsolete !
        module.submodule.constant = This variable will be removed !
