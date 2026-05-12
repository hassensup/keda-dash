# Guide de Correction - Ajout d'Événements Cron

## 🎯 Problème Résolu

L'erreur 422 lors de l'ajout d'événements cron depuis le calendrier a été corrigée.

### Erreurs Corrigées
1. ✅ Champ `soId` invalide envoyé à l'API Kubernetes
2. ✅ Valeurs null envoyées pour tous les champs (scaleTargetRef.name, etc.)
3. ✅ ScaledObject supprimé lors de l'ajout d'événements (corrigé précédemment)

## 📦 Déploiement

### Statut Actuel
- ✅ Code corrigé et commité (commit 47cea3e)
- ✅ Poussé vers GitHub
- ⏳ Build CI/CD en cours
- ⏳ Déploiement ArgoCD en attente

### Prochaines Étapes

#### 1. Vérifier le Build GitHub Actions (5-10 minutes)
```bash
# Vérifier sur GitHub
https://github.com/hassensup/keda-dash/actions

# L'image sera disponible à:
ghcr.io/hassensup/keda-dash-backend:okta-auth-rbac
# ou
ghcr.io/hassensup/keda-dash-backend:feature-okta-auth-rbac-47cea3e
```

#### 2. Vérifier le Déploiement ArgoCD (2-5 minutes après le build)
```bash
# Vérifier le statut de synchronisation ArgoCD
kubectl get application keda-dashboard -n argocd -o jsonpath='{.status.sync.status}'

# Forcer la synchronisation si nécessaire
kubectl patch application keda-dashboard -n argocd --type merge -p '{"operation":{"initiatedBy":{"username":"admin"},"sync":{"revision":"HEAD"}}}'
```

#### 3. Vérifier le Déploiement avec le Script
```bash
# Exécuter le script de vérification
./verify_cron_fix_deployment.sh

# Le script vérifie:
# - L'image déployée contient le bon commit
# - Le pod est en cours d'exécution
# - Le pod est prêt
# - Pas d'erreurs dans les logs
# - Les ScaledObjects sont présents
```

#### 4. Tester l'Ajout d'Événements Cron

Une fois le déploiement terminé:

1. **Ouvrir l'interface KEDA Dashboard**
   ```
   http://[votre-ingress-url]
   ```

2. **Naviguer vers la vue Calendrier**

3. **Sélectionner un ScaledObject**
   - Choisir un ScaledObject existant dans le namespace "test"
   - Ou créer un nouveau ScaledObject si nécessaire

4. **Ajouter un Événement Cron**
   - Cliquer sur une date dans le calendrier
   - Remplir les détails de l'événement:
     - Nom de l'événement
     - Heure de début
     - Heure de fin
     - Nombre de réplicas souhaité
     - Fuseau horaire

5. **Vérifier le Succès**
   - ✅ Pas d'erreur 422
   - ✅ Le ScaledObject n'est PAS supprimé
   - ✅ L'événement apparaît dans le calendrier
   - ✅ Le trigger cron est ajouté au ScaledObject

## 🔍 Vérifications Détaillées

### Vérifier l'Image Déployée
```bash
kubectl get deployment keda-dashboard-backend -n test -o jsonpath='{.spec.template.spec.containers[0].image}'
```

### Vérifier les Logs du Pod
```bash
# Logs en temps réel
kubectl logs -n test -l app=keda-dashboard-backend --tail=100 -f

# Rechercher des erreurs
kubectl logs -n test -l app=keda-dashboard-backend --tail=200 | grep -i "error\|exception"
```

### Vérifier le ScaledObject
```bash
# Lister les ScaledObjects
kubectl get scaledobjects -n test

# Voir les détails d'un ScaledObject
kubectl get scaledobject test -n test -o yaml

# Vérifier les triggers
kubectl get scaledobject test -n test -o jsonpath='{.spec.triggers}' | jq .
```

### Vérifier les Événements Kubernetes
```bash
# Événements récents dans le namespace
kubectl get events -n test --sort-by='.lastTimestamp' | tail -20

# Événements du pod
kubectl describe pod -n test -l app=keda-dashboard-backend
```

## 🐛 Dépannage

### Le Build GitHub Actions Échoue
```bash
# Vérifier les logs du build sur GitHub
https://github.com/hassensup/keda-dash/actions

# Vérifier le Dockerfile
docker build -t test-build --target backend-final .
```

### ArgoCD Ne Synchronise Pas
```bash
# Vérifier le statut de l'application
kubectl get application keda-dashboard -n argocd -o yaml

# Forcer la synchronisation
kubectl patch application keda-dashboard -n argocd --type merge -p '{"operation":{"initiatedBy":{"username":"admin"},"sync":{"revision":"HEAD"}}}'

# Vérifier les logs ArgoCD
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-application-controller
```

### Le Pod Ne Démarre Pas
```bash
# Vérifier le statut du pod
kubectl get pods -n test -l app=keda-dashboard-backend

# Voir les événements du pod
kubectl describe pod -n test -l app=keda-dashboard-backend

# Vérifier les logs
kubectl logs -n test -l app=keda-dashboard-backend --previous
```

### L'Erreur 422 Persiste
```bash
# Vérifier que la bonne image est déployée
kubectl get deployment keda-dashboard-backend -n test -o jsonpath='{.spec.template.spec.containers[0].image}'

# Doit contenir: 47cea3e ou okta-auth-rbac

# Vérifier les logs pour voir la requête envoyée
kubectl logs -n test -l app=keda-dashboard-backend --tail=200 | grep "DEBUG K8s"

# Vérifier le ScaledObject dans Kubernetes
kubectl get scaledobject test -n test -o yaml
```

## 📝 Détails Techniques de la Correction

### Correction 1: Nettoyage du Champ `soId`
Le frontend ajoute un champ `soId` aux triggers pour le tracking interne, mais KEDA ne reconnaît pas ce champ.

**Avant:**
```json
{
  "type": "cron",
  "soId": "test/test",  // ❌ Champ invalide
  "metadata": {...}
}
```

**Après:**
```python
# backend/k8s_service.py (ligne ~335)
cleaned_triggers = []
for trigger in data["triggers"]:
    cleaned_trigger = {k: v for k, v in trigger.items() if k != "soId"}
    cleaned_triggers.append(cleaned_trigger)
spec["triggers"] = cleaned_triggers
```

### Correction 2: Mise à Jour Conditionnelle des Champs
Seuls les champs explicitement fournis sont mis à jour, évitant d'envoyer des valeurs null.

**Avant:**
```python
# Tous les champs envoyés, même null
spec["scaleTargetRef"] = {"name": data.get("target_deployment")}  # ❌ Peut être null
```

**Après:**
```python
# backend/k8s_service.py (ligne ~320)
if "target_deployment" in data and data["target_deployment"] is not None:
    spec["scaleTargetRef"] = {"name": data["target_deployment"]}
```

### Correction 3: Utilisation de `exclude_unset=True`
Le serveur n'envoie que les champs explicitement fournis par le frontend.

**Avant:**
```python
# backend/server.py
update_data = data.model_dump(exclude_unset=False)  # ❌ Envoie tous les champs
```

**Après:**
```python
# backend/server.py (ligne ~618)
update_data = data.model_dump(exclude_unset=True)  # ✅ Seulement les champs fournis
```

## 📊 Résumé des Corrections

| Problème | Cause | Solution | Fichier |
|----------|-------|----------|---------|
| Champ `soId` invalide | Frontend ajoute un champ non reconnu par KEDA | Nettoyer le champ avant envoi | `k8s_service.py:335` |
| Valeurs null envoyées | `exclude_unset=False` envoie tous les champs | Utiliser `exclude_unset=True` | `server.py:618` |
| Champs requis null | Mise à jour inconditionnelle | Mise à jour conditionnelle | `k8s_service.py:320` |

## ✅ Checklist de Vérification

- [ ] Build GitHub Actions terminé avec succès
- [ ] Image Docker disponible dans ghcr.io
- [ ] ArgoCD a synchronisé l'application
- [ ] Pod backend en cours d'exécution (Running)
- [ ] Pod backend prêt (Ready)
- [ ] Pas d'erreurs dans les logs
- [ ] ScaledObjects présents dans le namespace
- [ ] Interface UI accessible
- [ ] Ajout d'événement cron réussit
- [ ] ScaledObject non supprimé
- [ ] Trigger cron visible dans Kubernetes

## 🚀 Commandes Rapides

```bash
# Tout-en-un: vérifier le déploiement
./verify_cron_fix_deployment.sh

# Surveiller les pods
kubectl get pods -n test -w

# Suivre les logs
kubectl logs -n test -l app=keda-dashboard-backend -f

# Vérifier ArgoCD
kubectl get application keda-dashboard -n argocd

# Tester l'API directement
curl -X PUT http://[ingress-url]/api/scaled-objects/test/test \
  -H "Authorization: Bearer [token]" \
  -H "Content-Type: application/json" \
  -d '{"triggers": [{"type": "cron", "metadata": {...}}]}'
```

## 📞 Support

Si le problème persiste après le déploiement:

1. Exécuter `./verify_cron_fix_deployment.sh`
2. Collecter les logs: `kubectl logs -n test -l app=keda-dashboard-backend --tail=500 > logs.txt`
3. Vérifier le ScaledObject: `kubectl get scaledobject test -n test -o yaml > scaledobject.yaml`
4. Partager les fichiers de diagnostic

---

**Dernière mise à jour**: 30 avril 2026, 09:40 GMT
**Commit**: 47cea3e
**Branche**: feature/okta-auth-rbac
