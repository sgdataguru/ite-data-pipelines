{#
  Custom schema resolver.

  Without this override, dbt would prefix every custom schema with the target
  schema, e.g. "main_silver", "main_gold". We want the plain names "silver" and
  "gold" instead. Any model that doesn't set +schema falls back to the target
  schema (main).
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}{{ target.schema }}
    {%- else -%}{{ custom_schema_name | trim }}{%- endif -%}
{%- endmacro %}
