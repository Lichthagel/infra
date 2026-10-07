# LiteLLM provider authentication

ArgoCD manages this chart on sumireko. Models are stored in the LiteLLM database
and can still be managed through the UI.

## Persistent authentication files

The chart creates the provider-neutral `litellm-provider-auth` PVC and mounts it
at `/var/lib/litellm/provider-auth`. Each provider should use a separate
subdirectory. Configure its documented token-directory environment variable
through `litellm-helm.envVars`; only providers that support file-based credentials
and a configurable path can use this arrangement.

The claim uses 10 MiB with `ReadWriteOnce` access and the cluster default storage class. Keep its fixed name aligned with `litellm-helm.volumes`. The mount path and provider paths use the upstream chart values.

The current deployment uses one replica and the cluster's default local-path
storage. Recreate prevents old and new proxy pods from overlapping during an
update, at the cost of a short outage. Do not increase replicas for this setup.
Multiple replicas require suitable shared storage AND provider support for
concurrent token refresh; ReadWriteMany alone does not provide locking.

The pod's fsGroup makes the volume accessible through group 65534, including
when using an image running as that non-root user. If you change the runtime
user/group, check permissions of existing token files as well.

The claim is excluded from automatic ArgoCD pruning because it contains mutable
credentials. Explicitly delete it only when the stored logins are no longer
needed. local-path storage is tied to its node; it does not survive loss of the
underlying disk. Include the volume in your encrypted backup process.

## ChatGPT login

Sync the storage and deployment changes before adding a ChatGPT model.
Choose the sumireko kubectl context, then locate the proxy pod and its container:

```bash
kubectl -n litellm get pods
kubectl -n litellm get pod <pod-name> -o jsonpath='{.spec.containers[*].name}'
kubectl -n litellm exec -it <pod-name> -c <proxy-container> -- \
  python -c "from litellm.llms.chatgpt.authenticator import Authenticator; Authenticator().get_access_token()"
```

Open the printed verification URL and enter the device code.
CHATGPT_TOKEN_DIR places auth.json in the chatgpt subdirectory on the PVC.
The proxy refreshes tokens in that writable file. Do not put tokens in Git or
copy the same login to independently refreshed files.

Once login succeeds, register an available `chatgpt/` model through the UI
(e.g. `chatgpt/gpt-5.4`, Responses mode). If a previously registered deployment
failed to initialize before login, restart the proxy after authentication.
To reauthenticate, run the same command; if the existing session is invalid,
the authenticator requests another device login. Changing or deleting a token
file should be done while the proxy is stopped to avoid concurrent refreshes.

No credential-seeding init container is needed: login writes directly to the
persistent volume. Other providers require their own documented login procedure.

References:
- https://docs.litellm.ai/docs/providers/chatgpt
- https://github.com/BerriAI/litellm/tree/v1.104.0/helm/litellm-helm
