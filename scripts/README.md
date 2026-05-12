# 🔧 Scripts du Projet KEDA Dashboard

Ce dossier contient tous les scripts utilitaires pour le déploiement, la configuration et le dépannage du projet.

## 📋 Liste des Scripts

### 🚀 Déploiement

#### **redeploy-frontend.sh**
Redéploie le frontend avec la nouvelle interface.
```bash
./scripts/redeploy-frontend.sh
```
**Usage** : Après modification du code frontend
**Durée** : ~5 minutes

#### **deploy_with_ingress.sh**
Déploie l'application avec configuration Ingress.
```bash
./scripts/deploy_with_ingress.sh
```
**Usage** : Déploiement initial ou mise à jour Ingress

#### **restart-deployment.sh**
Redémarre les déploiements Kubernetes.
```bash
./scripts/restart-deployment.sh
```
**Usage** : Redémarrage rapide des pods

#### **verify_deployment.sh**
Vérifie que le déploiement est correct.
```bash
./scripts/verify_deployment.sh
```
**Usage** : Après chaque déploiement

#### **verify_cron_fix_deployment.sh**
Vérifie le déploiement des corrections cron.
```bash
./scripts/verify_cron_fix_deployment.sh
```
**Usage** : Après correction des cron triggers

### 🔐 Configuration Okta

#### **configure_okta.sh**
Configure l'authentification Okta.
```bash
./scripts/configure_okta.sh
```
**Usage** : Configuration initiale Okta

#### **diagnose_okta_config.sh**
Diagnostique la configuration Okta.
```bash
./scripts/diagnose_okta_config.sh
```
**Usage** : Dépannage de l'authentification

#### **fix_frontend_url_now.sh**
Corrige l'URL du frontend dans la configuration Okta.
```bash
./scripts/fix_frontend_url_now.sh
```
**Usage** : Correction des redirections Okta

### 🔍 Monitoring et Logs

#### **check_okta_logs.sh**
Vérifie les logs d'authentification Okta.
```bash
./scripts/check_okta_logs.sh
```
**Usage** : Dépannage de l'authentification

#### **watch_okta_logs.sh**
Surveille les logs Okta en temps réel.
```bash
./scripts/watch_okta_logs.sh
```
**Usage** : Monitoring en temps réel

#### **debug_okta_redirect.sh**
Debug les problèmes de redirection Okta.
```bash
./scripts/debug_okta_redirect.sh
```
**Usage** : Dépannage des redirections

### 🧪 Tests et Vérification

#### **test_okta_url.sh**
Teste la configuration des URLs Okta.
```bash
./scripts/test_okta_url.sh
```
**Usage** : Vérification de la configuration

#### **check_frontend_url.sh**
Vérifie l'URL du frontend.
```bash
./scripts/check_frontend_url.sh
```
**Usage** : Vérification de l'accessibilité

### 📤 Git et Versioning

#### **push-changes.sh**
Commit et push les modifications vers Git.
```bash
./scripts/push-changes.sh
```
**Usage** : Après modification du code
**Interactif** : Demande confirmation

## 🎯 Workflows Courants

### Workflow 1 : Déploiement d'une Nouvelle Fonctionnalité

```bash
# 1. Commit et push le code
./scripts/push-changes.sh

# 2. Redéployer le frontend
./scripts/redeploy-frontend.sh

# 3. Vérifier le déploiement
./scripts/verify_deployment.sh
```

### Workflow 2 : Configuration Initiale Okta

```bash
# 1. Configurer Okta
./scripts/configure_okta.sh

# 2. Tester la configuration
./scripts/test_okta_url.sh

# 3. Vérifier les logs
./scripts/check_okta_logs.sh
```

### Workflow 3 : Dépannage Okta

```bash
# 1. Diagnostiquer
./scripts/diagnose_okta_config.sh

# 2. Surveiller les logs
./scripts/watch_okta_logs.sh

# 3. Corriger si nécessaire
./scripts/fix_frontend_url_now.sh
```

### Workflow 4 : Redémarrage Rapide

```bash
# 1. Redémarrer les pods
./scripts/restart-deployment.sh

# 2. Vérifier
./scripts/verify_deployment.sh
```

## 📊 Tableau Récapitulatif

| Script | Catégorie | Durée | Interactif |
|--------|-----------|-------|------------|
| redeploy-frontend.sh | Déploiement | 5 min | Non |
| deploy_with_ingress.sh | Déploiement | 3 min | Non |
| restart-deployment.sh | Déploiement | 1 min | Non |
| verify_deployment.sh | Test | 30 sec | Non |
| verify_cron_fix_deployment.sh | Test | 30 sec | Non |
| configure_okta.sh | Configuration | 2 min | Oui |
| diagnose_okta_config.sh | Diagnostic | 1 min | Non |
| fix_frontend_url_now.sh | Correction | 1 min | Non |
| check_okta_logs.sh | Monitoring | 30 sec | Non |
| watch_okta_logs.sh | Monitoring | Continu | Non |
| debug_okta_redirect.sh | Diagnostic | 1 min | Non |
| test_okta_url.sh | Test | 30 sec | Non |
| check_frontend_url.sh | Test | 30 sec | Non |
| push-changes.sh | Git | 1 min | Oui |

## 🔧 Prérequis

### Outils Nécessaires
- **bash** : Shell Unix
- **docker** : Pour les builds et déploiements
- **kubectl** : Pour les opérations Kubernetes
- **git** : Pour le versioning
- **curl** : Pour les tests HTTP

### Variables d'Environnement
Certains scripts nécessitent des variables d'environnement. Voir [../docs/ENVIRONMENT_VARIABLES.md](../docs/ENVIRONMENT_VARIABLES.md)

## 💡 Conseils d'Utilisation

### Rendre les Scripts Exécutables
```bash
chmod +x scripts/*.sh
```

### Exécuter depuis la Racine du Projet
```bash
# Depuis la racine
./scripts/nom-du-script.sh

# Ou depuis le dossier scripts
cd scripts
./nom-du-script.sh
```

### Voir l'Aide d'un Script
```bash
./scripts/nom-du-script.sh --help
# Ou
./scripts/nom-du-script.sh -h
```

### Mode Debug
```bash
# Exécuter en mode verbose
bash -x ./scripts/nom-du-script.sh
```

## 🚨 Sécurité

### Bonnes Pratiques
- ✅ Toujours vérifier le contenu d'un script avant de l'exécuter
- ✅ Ne jamais commiter de secrets dans les scripts
- ✅ Utiliser des variables d'environnement pour les données sensibles
- ✅ Limiter les permissions des scripts (`chmod 750`)

### Scripts Sensibles
Ces scripts manipulent des données sensibles :
- `configure_okta.sh` - Configuration d'authentification
- `fix_frontend_url_now.sh` - Modification de configuration

## 📝 Maintenance

### Ajouter un Nouveau Script
1. Créer le script dans `scripts/`
2. Ajouter le shebang : `#!/bin/bash`
3. Rendre exécutable : `chmod +x scripts/nouveau-script.sh`
4. Documenter dans ce README
5. Tester le script
6. Commiter

### Conventions de Nommage
- Utiliser des tirets (`-`) pour séparer les mots
- Utiliser des noms descriptifs
- Suffixe `.sh` obligatoire
- Préfixe par catégorie (optionnel) : `deploy-`, `test-`, `fix-`

## 🔗 Liens Utiles

- **Documentation** : [../docs/](../docs/)
- **README principal** : [../README.md](../README.md)
- **Guide de déploiement** : [../docs/DEPLOYMENT_INSTRUCTIONS.md](../docs/DEPLOYMENT_INSTRUCTIONS.md)

## 📞 Support

Pour toute question sur les scripts :
1. Consulter la documentation dans [../docs/](../docs/)
2. Vérifier les logs d'exécution
3. Contacter l'équipe DevOps

---

**Dernière mise à jour** : 2 mai 2026
**Nombre de scripts** : 14
**Mainteneur** : Équipe KEDA Dashboard
