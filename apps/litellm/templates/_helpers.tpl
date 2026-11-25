{{/* Keep the existing Deployment's immutable selector when migrating from litellm-helm. */}}
{{- define "litellm.proxy.selectorLabels" -}}
app.kubernetes.io/name: litellm
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}
