# Analyse des logs de debug - Scaling Behavior

## 🔍 Logs à chercher

Après avoir redéployé et testé, cherchez ces logs dans l'ordre :

### 1. Frontend (Console du navigateur)

```
[DEBUG Frontend] Saving with data: {hasScalingBehavior: true, ...}
[DEBUG Frontend] Update data keys: [...]
[DEBUG Frontend] scaling_behavior in updateData: true/false
```

**Questions :**
- ✅ `hasScalingBehavior` est-il `true` ?
- ✅ `scaling_behavior` est-il dans `updateData` ?

### 2. Backend - Route API (logs du pod)

```
[DEBUG] PUT /scaled-objects/test/test - Raw Pydantic model: ...
[DEBUG] model_dump(exclude_unset=True) keys: [...]
[DEBUG] 'scaling_behavior' in update_data: True/False
[DEBUG] 'triggers' in update_data: True/False
```

**Questions :**
- ✅ `triggers` est-il dans `update_data` ? (devrait être True)
- ❌ `scaling_behavior` est-il dans `update_data` ? (probablement False)

**Si `scaling_behavior` n'est PAS dans `update_data` :**
```
[DEBUG] scaling_behavior NOT in update_data! This is the problem!
[DEBUG] model_dump(exclude_unset=False) keys: [...]
[DEBUG] scaling_behavior IS in exclude_unset=False: {...}
```

Cela signifie que **Pydantic considère `scaling_behavior` comme "unset"** même s'il est envoyé !

### 3. Backend - K8s Service

```
[DEBUG K8s] update_object called with obj_id=test/test
[DEBUG K8s] data keys: [...]
[DEBUG K8s] 'scaling_behavior' in data: True/False
[DEBUG K8s] 'triggers' in data: True/False
```

**Questions :**
- ✅ `triggers` est-il dans `data` ?
- ❌ `scaling_behavior` est-il dans `data` ?

**Si `scaling_behavior` EST dans `data` :**
```
[DEBUG K8s] scaling_behavior value: {...}
[DEBUG K8s] Created scaleUp: {...}
[DEBUG K8s] Added behavior to spec: {...}
[DEBUG K8s] Final spec has 'behavior': True
```

**Si `scaling_behavior` N'EST PAS dans `data` :**
```
[DEBUG K8s] scaling_behavior NOT in data - will not update behavior!
```

## 🎯 Diagnostic

### Scénario 1 : `scaling_behavior` n'est pas dans le frontend

**Symptôme :**
```
[DEBUG Frontend] hasScalingBehavior: false
```

**Cause :** Le formulaire n'a pas de `scaling_behavior` configuré.

**Solution :** Vérifier que vous avez bien cliqué sur "Add" pour scale-up ou scale-down.

### Scénario 2 : `scaling_behavior` est perdu par Pydantic

**Symptôme :**
```
[DEBUG Frontend] scaling_behavior in updateData: true
[DEBUG] 'scaling_behavior' in update_data: False  ← PROBLÈME ICI
[DEBUG] scaling_behavior NOT in update_data! This is the problem!
```

**Cause :** `model_dump(exclude_unset=True)` exclut `scaling_behavior`.

**Solution :** Le code utilise maintenant `model_dump(exclude_unset=False)` comme fallback.

### Scénario 3 : `scaling_behavior` n'arrive pas au K8s Service

**Symptôme :**
```
[DEBUG] 'scaling_behavior' in update_data: True
[DEBUG K8s] 'scaling_behavior' in data: False  ← PROBLÈME ICI
```

**Cause :** Le champ est perdu entre la route API et le service K8s.

**Solution :** Vérifier qu'il n'y a pas de transformation intermédiaire.

### Scénario 4 : `scaling_behavior` arrive mais n'est pas écrit dans K8s

**Symptôme :**
```
[DEBUG K8s] 'scaling_behavior' in data: True
[DEBUG K8s] scaling_behavior value: {...}
[DEBUG K8s] Created scaleUp: {...}
[DEBUG K8s] Added behavior to spec: {...}
[DEBUG K8s] Final spec has 'behavior': True
```

Mais le behavior n'est toujours pas dans le CRD Kubernetes.

**Cause :** Problème lors de l'appel à l'API Kubernetes (`replace_namespaced_custom_object`).

**Solution :** Vérifier les permissions RBAC ou les erreurs Kubernetes.

## 📊 Comparaison triggers vs scaling_behavior

### Pourquoi `triggers` fonctionne :

1. ✅ `triggers` est dans le schéma Pydantic depuis le début
2. ✅ `triggers` est toujours "set" (liste vide par défaut)
3. ✅ `model_dump(exclude_unset=True)` inclut `triggers`

### Pourquoi `scaling_behavior` ne fonctionne pas :

1. ❓ `scaling_behavior` a été ajouté après coup
2. ❓ `scaling_behavior` peut être `None` ou `null`
3. ❌ `model_dump(exclude_unset=True)` exclut `scaling_behavior` si considéré comme "unset"

## 🔧 Solution probable

Le problème est dans le schéma Pydantic `ScaledObjectUpdate`. Il faut s'assurer que `scaling_behavior` est correctement défini :

```python
class ScaledObjectUpdate(BaseModel):
    # ...
    scaling_behavior: Optional[dict] = None  # ← Doit avoir une valeur par défaut
```

Avec `= None`, Pydantic considère le champ comme "set" même s'il est `None`.

## 📝 Actions à effectuer

1. **Redéployer** le backend avec les logs de debug
2. **Tester** en ajoutant un scaling behavior
3. **Consulter** les logs dans l'ordre ci-dessus
4. **Identifier** à quelle étape `scaling_behavior` est perdu
5. **Appliquer** la solution correspondante

## 🎯 Résultat attendu

Après correction, vous devriez voir :

```
[DEBUG Frontend] scaling_behavior in updateData: true
[DEBUG] 'scaling_behavior' in update_data: True
[DEBUG K8s] 'scaling_behavior' in data: True
[DEBUG K8s] Added behavior to spec: {...}
[DEBUG K8s] Final spec has 'behavior': True
```

Et dans Kubernetes :
```bash
kubectl get scaledobject test -n test -o yaml | grep -A 10 "behavior:"
```

Devrait afficher la section `behavior`.
