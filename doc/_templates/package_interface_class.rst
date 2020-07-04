{{ fullname | escape | underline}}

This class is exported in ``{{ module }}.__init__.py``,
thus it is part of the public interface of package :mod:`{{ module }}`.
It is defined in a submodule of the package.

*Usage:*

    from {{ module }} import {{ name }}

.. currentmodule:: {{ module }}

.. autoclass:: {{ objname }}
   :noindex:

   {% block methods %}
   {% if methods %}
   .. rubric:: {{ _('Methods overview') }}

   .. autosummary::
   {% for item in methods %}
      ~{{ name }}.{{ item }}
   {%- endfor %}
   {% endif %}
   {% endblock %}

   {% block attributes %}
   {% if attributes %}
   .. rubric:: {{ _('Attributes overview') }}

   .. autosummary::
   {% for item in attributes %}
      ~{{ name }}.{{ item }}
   {%- endfor %}
   {% endif %}
   {% endblock %}

   {% block method_details %}
   {% if methods %}
   .. rubric:: {{ _('Method details') }}

   {% for item in methods %}
   .. automethod:: {{ name }}.{{ item }}
   {%- endfor %}
   {% endif %}
   {% endblock %}

   {% block attribute_details %}
   {% if attributes %}
   .. rubric:: {{ _('Attribute details') }}

   {% for item in attributes %}
   .. autoattribute:: {{ name }}.{{ item }}
   {%- endfor %}
   {% endif %}
   {% endblock %}

