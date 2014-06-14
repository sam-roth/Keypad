
.. _settings-howto:

Settings HOWTO
**************

:author: Sam Roth

.. topic:: Abstract
    
    In this document, we will provide motivation for the settings system, define
    the relevant terminology, and provide information on the use and declaration
    of settings.

.. note:: 
    Readers who only seek to change settings may wish to skip to the 
    :ref:`settings-howto.using-settings` section.

Motivation
==========

Initially, the editor simply stored configuration in variables at module scope.
To change the settings, one would import the module and assign to the variables.
This method had a number of drawbacks: First, there was no way of observing the
value of a setting. If you wanted to know if a setting had changed, you would
have had to poll it. Second, it was global. Changing such a setting would
affect every object in the application. Third and finally, there was no way to
attach metadata to the settings, such as a docstring, or information about
whether the setting could be safely loaded from an untrusted configuration file. 

To address these issues, a new settings system was created based on ideas from
the :abbr:`EDSL (embedded domain-specific language)` used for specifying
database schemas in Django.


Terminology
===========

settings
    Settings classes are the schema for the settings system. Many different
    settings objects can load data from the same configuration. **Settings
    classes control the interpretation of configuration data.**

configuration
    The configuration is the specific data from which settings are loaded.
    Configuration can be loaded from a YAML file or modified by using a
    settings class.

contextual configuration
    The contextual configuration is the configuration data loaded automatically
    (if present) when opening a file under its control. For instance,
    contextual configuration allows you to use tab-based indentation when
    working on one project and space-based indentation when working on another.



.. py:currentmodule:: stem.core.nconfig

Cascading Configuration
=======================

Multiple configuration data sources may be used. If looking up in
the topmost fails, the next one will be tried. Modifications are always written back
to the topmost configuration. Configurations may derive from other configurations,
and changes to parent configurations take effect immediately in child configurations.

.. _settings-howto.using-settings:

Using Settings
==============

To adjust settings from a Python script,


#. Find the Settings class in which they are declared.
#. Use the :py:meth:`~stem.core.nconfig.Settings.from_config` method to load
   the settings from a configuration.
#. Modify the setting.


For example, the following snippet will set the text view font to
Fira Mono globally::
    
    from stem.options import GeneralSettings
    from stem.core import Config

    s = GeneralSettings.from_config(Config.root)
    s.font_family = 'Fira Mono OT'

Changes take effect as soon as the ``font_family`` field is assigned to. No
further action is necessary.

To do the same thing with a YAML configuration file, use this snippet::

    from stem.core import Config

    Config.root.load_yaml('''
    general:
        font_family: 'Fira Mono OT'
    ''', safe=False)

Notice how `~stem.options.GeneralSettings` wasn't mentioned in the second
example? This is because the settings (the schema) and the configuration (the
data) are decoupled. We only needed to modify the underlying data, so we didn't need
the settings class. 

Where did the ``general`` come from? It's specified in the documentation
for `~stem.options.GeneralSettings`, under the heading "Config Namespace".


.. tip::
    
    By convention, settings classes always have the word ``Settings`` in their
    names. To find settings you can adjust, try searching this documentation
    for `"settings class" <./search.html?q=settings+class>`_.

Declaring Settings
==================

Settings are declared using an EDSL reminiscent of that used to
specify Django models.

Settings subclasses consist of:

* An assignment to the class attribute ``_ns_``, which stands for "namespace"
  and controls the name used for the section in the configuration file.
* One or more class attributes of type `~stem.core.nconfig.Field`, as detailed
  below.

.. autoclass:: Field
    :noindex:


.. Field(type, default=None, safe=False, docs=None)
..  
..  Mark a field as having the given type, default value, and
..  docstring, as well as marking whether it is safe to load
..  from an untrusted contextual configuration file.

.. warning:: 
    It is generally speaking unwise to use a mutable type as a field.
    Mutating a value in place will cause the changes to propagate upwards
    through the configuration hierarchy, rather than being restricted to the
    scope where the change was made.
    

Observing Settings
==================

You may observe the fields of a settings object by using its
`~stem.core.nconfig.Settings.value_changed` signal. This signal is emitted
whenever the value of a field changes, even if it was changed by reading a
configuration file or by modifying an ancestor configuration.

Further Reading
===============

* `Django 1.7 Documentation: Models <https://docs.djangoproject.com/en/1.7/topics/db/models/>`_ (design inspiration)
* `IPython Configuration <http://ipython.org/ipython-doc/dev/development/config.html>`_ (a case of convergent evolution)

