# DNS Configuration

This directory contains the DNS infrastructure for the cluster using AdGuard Home with Unbound as the upstream recursive resolver.

## Architecture

1. **Unbound** - Recursive DNS resolver that queries root nameservers directly
   - Runs on port 53 (internally 5353)
   - Provides privacy-focused DNS resolution
   - 2 replicas for high availability

2. **AdGuard Home** - DNS filtering and ad-blocking
   - Uses Unbound as upstream resolver
   - Provides web interface on <https://adguard.dns.licht.moe>
   - **Plain DNS (port 53) is DISABLED** - secure protocols only
   - **DNS-over-HTTPS (DoH)** available at `https://dns.licht.moe/dns-query`
   - **DNS-over-TLS (DoT)** available at `dns.licht.moe:853` (service: `aghome-dot.aghome.svc.cluster.local:853`)
   - Fallback to Cloudflare DNS if Unbound is unavailable

## Configuring Cluster DNS with DoT

Since plain DNS is disabled on AdGuard Home, CoreDNS must be configured to use DNS-over-TLS.

Edit the CoreDNS ConfigMap:

```bash
kubectl edit configmap coredns -n kube-system
```

Configure the forward section to use DNS-over-TLS with fallback:

```text
.:53 {
    errors
    health {
        lameduck 5s
    }
    ready
    kubernetes cluster.local in-addr.arpa ip6.arpa {
        pods insecure
        fallthrough in-addr.arpa ip6.arpa
        ttl 30
    }
    prometheus :9153
    # Forward to AdGuard Home via DNS-over-TLS with Cloudflare fallback
    forward . tls://aghome-dot.aghome.svc.cluster.local:853 1.1.1.1 1.0.0.1 {
        tls_servername dns.licht.moe
        policy sequential
        health_check 30s
    }
    cache 30
    loop
    reload
    loadbalance
}
```

Then restart CoreDNS:

```bash
kubectl rollout restart deployment coredns -n kube-system
```

### Verify DNS Configuration

Test DNS resolution from a pod:

```bash
# Create a test pod
kubectl run -it --rm debug --image=busybox --restart=Never -- sh

# Inside the pod, test DNS
nslookup google.com
nslookup kubernetes.default.svc.cluster.local

# Check which DNS server is being used
cat /etc/resolv.conf
```

### DNS Flow

```text
Pod DNS Query
    ↓
CoreDNS (kube-system) - via DNS-over-TLS
    ↓
AdGuard Home (adguard namespace) - DoT/DoH only
    ↓
Unbound (unbound namespace)
    ↓
Root DNS Servers

Fallback paths:
- If AdGuard Home is down: CoreDNS → Cloudflare DNS (1.1.1.1, 1.0.0.1)
- If Unbound is down: AdGuard Home → Cloudflare DNS
```

## Access AdGuard Home Web Interface

1. Navigate to <https://adguard.dns.licht.moe> in your browser
2. Complete the initial setup wizard
3. The default configuration already points to Unbound as the upstream DNS

## Using Secure DNS Protocols

### DNS-over-HTTPS (DoH)

Configure your browser or system to use DoH:

**URL:** `https://dns.licht.moe/dns-query`

**Browser Configuration:**

- **Firefox:** Settings → Privacy & Security → DNS over HTTPS → Custom → `https://dns.licht.moe/dns-query`
- **Chrome/Edge:** Settings → Privacy and security → Security → Use secure DNS → Custom → `https://dns.licht.moe/dns-query`

**Command-line test:**

```bash
# Using curl
curl -H "accept: application/dns-json" "https://dns.licht.moe/dns-query?name=google.com&type=A"

# Using dog (modern DNS client)
dog google.com --https @https://dns.licht.moe/dns-query
```

### DNS-over-TLS (DoT)

Configure your system or DNS client to use DoT:

**Server:** `dns.licht.moe`
**Port:** `853`

**Command-line test:**

```bash
# Using kdig (from knot-dnsutils)
kdig @dns.licht.moe +tls google.com

# Using dog
dog google.com --tls @dns.licht.moe
```

**Android/iOS:**

- Android 9+: Settings → Network & Internet → Private DNS → `dns.licht.moe`
- iOS: Install a DoT-capable DNS app like DNSCloak or configure via profile

## Monitoring

Monitor the DNS services:

```bash
# Check AdGuard Home logs
kubectl logs -n adguard -l app=adguard -f

# Check Unbound logs
kubectl logs -n unbound -l app=unbound -f

# Check DNS service endpoints
kubectl get endpoints -n adguard adguard-dns
kubectl get endpoints -n unbound unbound

# Test DNS resolution
kubectl run -it --rm dnstest --image=busybox --restart=Never -- nslookup google.com adguard-dns.adguard.svc.cluster.local
```

## Notes

- The AdGuard Home deployment uses `strategy: Recreate` to avoid conflicts with the PersistentVolumeClaims
- Initial setup requires completing the web interface wizard at <https://adguard.dns.licht.moe>
- The ConfigMap provides a default configuration, but settings will be persisted to the PVCs after initial setup
- Unbound runs on port 5353 internally to avoid conflicts and is exposed as port 53 via the service
- CoreDNS configuration should be version controlled separately as it's typically managed by cluster provisioning tools
- **DoH and DoT are enabled** using the existing `dns-tls` certificate for `dns.licht.moe` and `*.dns.licht.moe`
- **Plain DNS (port 53) is DISABLED** for enhanced security - only encrypted protocols are available
- DoT is exposed via NodePort on port 853 for direct external access
- DoH uses the standard HTTPS port (443) and is accessible via the `/dns-query` endpoint through Traefik
- CoreDNS uses DoT to communicate with AdGuard Home for encrypted cluster DNS traffic
