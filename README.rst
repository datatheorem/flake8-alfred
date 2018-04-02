### Alban's TODOs/Feedback

* I love the name
* Nice use of type annotations and good that you have tests - overall this project is very clean. Nice work!
* We always use Markdown (.md) for text files like the README (not ReStructured). Please change to md.
* Add a stricter mypy configuration to your setup.cfg (like this one: https://bitbucket.org/datatheorem/caprica-server/src/master/mypy.ini ). You can also use the flake8 config from that repo (we use 120 characters per line).
* Is there a way to add a basic test that takes a file with banned modules/functions and ensures that the banned things are detected? I realize this would involve launching flake8 from a test, which might be tricky/cumbersome. Just let me know if it can be done easily or not.
* There are other TODOs in the code


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
