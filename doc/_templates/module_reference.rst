{{ fullname | escape | underline}}

Overview
--------

.. automodule:: {{ fullname }}
   :imported-members:

   {% block attributes %}
   {% if attributes %}
   .. rubric:: Module Attributes

   .. autosummary::
      :template: module_reference.rst
   {% for item in attributes -%}
      {{ item }}
   {%- endfor %}
   {% endif %}
   {% endblock %}

   {% block functions %}
   {% if functions %}
   .. rubric:: {{ _('Functions') }}

   .. autosummary::
      :template: module_reference.rst
      {% for item in functions %}
      {{ item }}
      {%- endfor %}

   {% endif %}
   {% endblock %}

   {% block classes %}
   {% if classes %}
   .. rubric:: {{ _('Classes') }}

   .. autosummary::
      :template: module_reference.rst
      {% for item in classes %}
      {{ item }}
      {%- endfor %}

   {% endif %}
   {% endblock %}

   {% block exceptions %}
   {% if exceptions %}
   .. rubric:: {{ _('Exceptions') }}

   .. autosummary::
      :template: module_reference.rst
      {% for item in exceptions %}
      {{ item }}
      {%- endfor %}

   {% endif %}
   {% endblock %}

{% block modules %}
{% if modules %}
.. rubric:: Public modules

.. autosummary::
   :template: module_reference.rst
   :toctree:
   :recursive:
   {% for item in modules %}
   {{ item }}
   {%- endfor %} {% endif %} {% endblock %}

{% if functions or classes %}

Details
--------

{% block function_details %}
{% if functions %}

Functions
..................

{% for item in functions %}
.. autofunction:: {{ item }}

{%- endfor %}
{% endif %}
{% endblock %}

{% block class_details %}
{% if classes %}

Classes
..................

{% for item in classes %}

.. autoclass:: {{ item }}
    :members:

{%- endfor %}
{% endif %}
{% endblock %}

{% endif %}
