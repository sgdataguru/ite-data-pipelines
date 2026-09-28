{#
  Hash a personal-data column with a salt from the environment.

  Usage in a model:
      select {{ mask_pii('nric') }} as nric_hash from ...

  PII_SALT is set in the Codespace (see .devcontainer/devcontainer.json). The
  salt is deliberately kept out of the code so the compiled SQL under
  target/compiled/ shows only a placeholder — you can verify this in the
  Lab 1 demo.
#}
{% macro mask_pii(column) %}
    sha256(upper(trim({{ column }})) || '{{ env_var("PII_SALT") }}')
{% endmacro %}
