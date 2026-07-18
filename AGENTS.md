# Infra — OpenCode Instructions

Kubernetes GitOps repo. ArgoCD manages everything; no `helm install`, no `kubectl apply`.

## Architecture

- **Clusters:** `hizuru`, `shinobu`, `tsubasa`, `sumireko`
- **Deployment pattern:** Each cluster has a directory under `clusters/<name>/` containing ArgoCD `Application` manifests. These point to paths under `apps/`.
  - `hizuru`, `shinobu`, `tsubasa`: flat YAML files (one per app)
  - `sumireko`: Helm chart (`Chart.yaml` + `templates/*.yaml`) parameterized via `clusters/sumireko/values.yaml`
- **Apps:** live under `apps/<name>/`. Two formats:
  - Standalone K8s manifests (+ optional `kustomization.yaml`, config files)
  - Helm charts (with `Chart.yaml`, `values.yaml`, templates/) — bundled as tgz in `apps/<name>/charts/`
- **Domain:** `.licht.moe`

## Commands

```bash
mise install          # install toolchain (helm)
```

No test/lint/typecheck commands exist. This is pure YAML infra.

## Adding an app

1. Create `apps/<name>/` with manifests or a Helm chart
2. Add an ArgoCD Application in the appropriate cluster directory:
   - For flat clusters (`hizuru`, `shinobu`, `tsubasa`): create `clusters/<cluster>/<app>.yaml`
   - For sumireko: add a template to `clusters/sumireko/templates/` and pass values via `values.yaml`

## Gotchas

- **Helm chart deps are vendored as tgz** in `apps/<name>/charts/`. Don't delete them; they're the actual charts ArgoCD installs.
- **Secrets use file mounts**, not inline values. Pattern: `password: file:///secrets/postgres/password` with a secret volume mounting the key to that path.
- **ArgoCD apps reference their own repo** (`repoURL: https://github.com/Lichthagel/infra`). This is self-hosted GitOps — ArgoCD bootstraps itself from this same repo.
- **Cilium CNI** is used on `hizuru` and `sumireko` with `kubeProxyReplacement: true`, dual-stack IPv4/IPv6, and Hubble enabled.
- **Renovate** auto-updates image versions in all YAML files (configured via `kubernetes` + `argocd` managers matching `*.yaml`).
