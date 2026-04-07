{{/*
Common labels
*/}}
{{- define "osint.labels" -}}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end }}

{{/*
Backend selector labels
*/}}
{{- define "osint.backend.selectorLabels" -}}
app.kubernetes.io/name: osint-backend
app.kubernetes.io/component: backend
{{- end }}

{{/*
Frontend selector labels
*/}}
{{- define "osint.frontend.selectorLabels" -}}
app.kubernetes.io/name: osint-frontend
app.kubernetes.io/component: frontend
{{- end }}

{{/*
Worker selector labels
*/}}
{{- define "osint.worker.selectorLabels" -}}
app.kubernetes.io/name: osint-worker
app.kubernetes.io/component: worker
{{- end }}

{{/*
PostgreSQL selector labels
*/}}
{{- define "osint.postgresql.selectorLabels" -}}
app.kubernetes.io/name: osint-postgresql
app.kubernetes.io/component: database
{{- end }}

{{/*
Redis selector labels
*/}}
{{- define "osint.redis.selectorLabels" -}}
app.kubernetes.io/name: osint-redis
app.kubernetes.io/component: cache
{{- end }}

{{/*
Database host — resolves to the postgresql service name if not overridden
*/}}
{{- define "osint.databaseHost" -}}
{{- if .Values.database.host -}}
{{ .Values.database.host }}
{{- else -}}
{{ .Release.Name }}-postgresql
{{- end -}}
{{- end }}
