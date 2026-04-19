# Devonn.ai Production Runbook

This runbook covers day-to-day operations, incident response, and recovery procedures for the Devonn.ai EKS production environment.

---

## Infrastructure Overview

| Component | Detail |
|---|---|
| **EKS Cluster** | `devonn-eks-prod`, us-west-2, Kubernetes v1.33 |
| **Node Group** | `dev_nodes`, `t3.small` × 2–6 nodes (autoscaling) |
| **Namespace** | `devonn` |
| **Workloads** | `devonn-backend` (2 replicas), `devonn-frontend` (2 replicas), `envoy-proxy` (3 replicas) |
| **ALB** | `devonn-alb-managed-*` — managed by AWS Load Balancer Controller |
| **WAF** | `devonn-prod-waf` — OWASP Core Rule Set + Rate Limit 2000 req/5min |
| **ECR** | `211125423223.dkr.ecr.us-west-2.amazonaws.com/production/devonn-ai` |
| **DocumentDB** | `devonn-docdb-prod.cluster-c9sk8giu2yuv.us-west-2.docdb.amazonaws.com:27017` |
| **ElastiCache Redis** | `devonn-redis-prod.ikwxkt.0001.usw2.cache.amazonaws.com:6379` |
| **Secrets Manager** | `devonn/prod/app-secrets`, `devonn/prod/external-services` |
| **CloudWatch Alarms** | 9 alarms → SNS topic `devonn-prod-alerts` |

---

## Quick Reference Commands

### Check cluster health
```bash
export AWS_PROFILE=devonn && export AWS_DEFAULT_REGION=us-west-2
kubectl get pods -n devonn
kubectl get nodes
kubectl get ingress -n devonn
```

### Check live health endpoint
```bash
curl -s http://devonn-alb-managed-2012536228.us-west-2.elb.amazonaws.com/api/health | python3 -m json.tool
```

### Check HPA status
```bash
kubectl get hpa -n devonn
```

### Check recent events
```bash
kubectl get events -n devonn --sort-by='.lastTimestamp' | tail -20
```

---

## Deployment Procedures

### Standard Deployment (CI/CD)
Push to `main` branch — the `devonn-prod-deploy` GitHub Actions workflow will:
1. Build and push the Docker image to ECR with tag `backend-<sha>` and `frontend-<sha>`
2. Update the EKS deployment image
3. Wait for rollout to complete (300s timeout)
4. Verify ALB `/api/health` returns 200
5. Auto-rollback if health check fails

### Manual Deployment
```bash
export AWS_PROFILE=devonn && export AWS_DEFAULT_REGION=us-west-2
IMAGE="211125423223.dkr.ecr.us-west-2.amazonaws.com/production/devonn-ai:backend-<sha>"
kubectl set image deployment/devonn-backend devonn-backend=$IMAGE -n devonn
kubectl rollout status deployment/devonn-backend -n devonn --timeout=300s
```

### Deploy Only Backend or Frontend
Trigger a manual workflow dispatch from GitHub Actions with the `service` input set to `backend` or `frontend`.

---

## Rollback Procedures

### Immediate Rollback (last good revision)
```bash
export AWS_PROFILE=devonn && export AWS_DEFAULT_REGION=us-west-2
kubectl rollout undo deployment/devonn-backend -n devonn
kubectl rollout undo deployment/devonn-frontend -n devonn
kubectl rollout status deployment/devonn-backend -n devonn --timeout=120s
```

### Rollback to a Specific Revision
```bash
# List revision history
kubectl rollout history deployment/devonn-backend -n devonn

# Roll back to revision 3
kubectl rollout undo deployment/devonn-backend -n devonn --to-revision=3
```

### Rollback to a Specific Image
```bash
IMAGE="211125423223.dkr.ecr.us-west-2.amazonaws.com/production/devonn-ai:backend-<known-good-sha>"
kubectl set image deployment/devonn-backend devonn-backend=$IMAGE -n devonn
kubectl rollout status deployment/devonn-backend -n devonn --timeout=120s
```

---

## Incident Response

### ALB Returning 502 Bad Gateway

**Cause:** Pod IPs changed after a rollout but the ALB target group was not updated (should not happen with LBC installed, but can occur if LBC is down).

**Diagnosis:**
```bash
# Check target group health
aws elbv2 describe-target-health \
  --target-group-arn $(aws elbv2 describe-target-groups \
    --names devonn-backend-tg-ip \
    --query 'TargetGroups[0].TargetGroupArn' --output text \
    --region us-west-2 --profile devonn-root) \
  --region us-west-2 --profile devonn-root

# Check LBC is running
kubectl get pods -n kube-system -l app.kubernetes.io/name=aws-load-balancer-controller
```

**Fix:**
```bash
# Restart LBC to re-sync target groups
kubectl rollout restart deployment/aws-load-balancer-controller -n kube-system

# Or force a rollout to trigger target re-registration
kubectl rollout restart deployment/devonn-backend deployment/devonn-frontend -n devonn
```

---

### Pod CrashLoopBackOff

**Diagnosis:**
```bash
kubectl describe pod <pod-name> -n devonn
kubectl logs <pod-name> -n devonn --previous
```

**Common causes and fixes:**

| Error | Fix |
|---|---|
| `FileNotFoundError: global-bundle.pem` | Rebuild image — Dockerfile must `COPY global-bundle.pem /global-bundle.pem` |
| `secretRef not found: devonn-app-secrets-k8s` | CSI driver has not synced yet. Check: `kubectl describe secretproviderclass devonn-app-secrets -n devonn` |
| `CSI token error: serviceAccount.tokens not provided` | Patch CSIDriver: `kubectl patch csidriver secrets-store.csi.k8s.io --type=merge --patch '{"spec":{"tokenRequests":[{"audience":"sts.amazonaws.com"}],"requiresRepublish":true}}'` |
| `gunicorn: Worker failed to boot` | Check full logs for the root Python exception |

---

### Pods Stuck in Pending

**Diagnosis:**
```bash
kubectl describe pod <pod-name> -n devonn | grep -A 10 Events
```

**Common causes:**

| Error | Fix |
|---|---|
| `Insufficient memory` | Check node utilization. Scale ASG: `aws autoscaling update-auto-scaling-group --auto-scaling-group-name <asg> --max-size 6 --region us-west-2 --profile devonn-root` |
| `0/4 nodes are available: 4 Too many pods` | Increase ASG max size or reduce pod resource requests |
| `pod has unbound immediate PersistentVolumeClaims` | Check PVC status: `kubectl get pvc -n devonn` |

---

### DocumentDB Connection Failures

**Diagnosis:**
```bash
# Check health endpoint for mongodb status
curl -s http://devonn-alb-managed-2012536228.us-west-2.elb.amazonaws.com/api/health | python3 -m json.tool

# Check DocumentDB cluster status
aws docdb describe-db-clusters \
  --db-cluster-identifier devonn-docdb-prod \
  --region us-west-2 --profile devonn-root \
  --query 'DBClusters[0].{Status:Status,Endpoint:Endpoint}'
```

**Common causes:**

| Error | Fix |
|---|---|
| `tlsCAFile not found` | Ensure `global-bundle.pem` is in the Docker image at `/global-bundle.pem` |
| `connection refused` | Check security group allows port 27017 from EKS node SG |
| `Authentication failed` | Verify `MONGODB_URI` in `devonn/prod/external-services` Secrets Manager |

---

### Redis Connection Failures

**Diagnosis:**
```bash
# Check health endpoint for redis status
curl -s http://devonn-alb-managed-2012536228.us-west-2.elb.amazonaws.com/api/health | python3 -m json.tool

# Check ElastiCache cluster status
aws elasticache describe-cache-clusters \
  --cache-cluster-id devonn-redis-prod-0001-001 \
  --region us-west-2 --profile devonn-root \
  --query 'CacheClusters[0].{Status:CacheClusterStatus,Endpoint:CacheNodes[0].Endpoint}'
```

---

## Scaling Procedures

### Manual Scale-Out
```bash
# Scale backend to 4 replicas
kubectl scale deployment/devonn-backend --replicas=4 -n devonn

# Scale ASG for more nodes
aws autoscaling update-auto-scaling-group \
  --auto-scaling-group-name <asg-name> \
  --max-size 8 \
  --region us-west-2 --profile devonn-root
```

### HPA Tuning
```bash
# Check current HPA
kubectl get hpa -n devonn

# Update CPU threshold
kubectl patch hpa devonn-backend -n devonn --type=merge --patch '{"spec":{"metrics":[{"type":"Resource","resource":{"name":"cpu","target":{"type":"Utilization","averageUtilization":70}}}]}}'
```

---

## Secrets Management

### Update a Secret
```bash
aws secretsmanager update-secret \
  --secret-id devonn/prod/external-services \
  --secret-string '{"OPENAI_API_KEY":"sk-...","MONGODB_URI":"...","REDIS_URL":"...","GH_TOKEN":"...","GH_TOKEN_WRITE":"..."}' \
  --region us-west-2 --profile devonn-root

# Restart pods to pick up new secrets
kubectl rollout restart deployment/devonn-backend deployment/devonn-frontend -n devonn
```

### Rotate DocumentDB Password
```bash
# 1. Generate new password
NEW_PASS=$(openssl rand -base64 24)

# 2. Update DocumentDB master password
aws docdb modify-db-cluster \
  --db-cluster-identifier devonn-docdb-prod \
  --master-user-password "$NEW_PASS" \
  --apply-immediately \
  --region us-west-2 --profile devonn-root

# 3. Update Secrets Manager
aws secretsmanager update-secret \
  --secret-id devonn/prod/external-services \
  --secret-string "{\"MONGODB_URI\":\"mongodb://devonnadmin:${NEW_PASS}@devonn-docdb-prod.cluster-c9sk8giu2yuv.us-west-2.docdb.amazonaws.com:27017/?tls=true&tlsCAFile=/global-bundle.pem&replicaSet=rs0&readPreference=secondaryPreferred&retryWrites=false\"}" \
  --region us-west-2 --profile devonn-root

# 4. Restart pods
kubectl rollout restart deployment/devonn-backend deployment/devonn-frontend -n devonn
```

---

## Monitoring

### CloudWatch Alarms
9 alarms are configured in CloudWatch. Subscribe to receive notifications:
```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:us-west-2:211125423223:devonn-prod-alerts \
  --protocol email \
  --notification-endpoint your@email.com \
  --region us-west-2 --profile devonn-root
```

### View Container Logs in CloudWatch
- Log group: `/aws/containerinsights/devonn-eks-prod/application`
- Filter: `{ $.kubernetes.namespace_name = "devonn" }`

### View Metrics in CloudWatch
- Navigate to CloudWatch → Container Insights → EKS Clusters → `devonn-eks-prod`

---

## HTTPS Activation (Pending Domain Delegation)

Once you update your domain registrar to use Route53 nameservers, the ACM certificate will auto-validate. Then run:

```bash
# Check cert status
aws acm describe-certificate \
  --certificate-arn arn:aws:acm:us-west-2:211125423223:certificate/<cert-id> \
  --region us-west-2 --profile devonn-root \
  --query 'Certificate.Status'

# Update Ingress to re-enable HTTPS (edit ingress.yaml to add cert annotation)
kubectl annotate ingress devonn-ingress -n devonn \
  "alb.ingress.kubernetes.io/certificate-arn=arn:aws:acm:us-west-2:211125423223:certificate/<cert-id>" \
  "alb.ingress.kubernetes.io/ssl-redirect=443" \
  --overwrite
```

Route53 nameservers for `devonn.ai`:
```
ns-491.awsdns-61.com
ns-1803.awsdns-33.co.uk
ns-1042.awsdns-02.org
ns-823.awsdns-38.net
```
