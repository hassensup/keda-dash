# 🧪 Plan de Tests : Présélection de Date dans le Calendrier

## 📋 Checklist de Tests

### ✅ Tests Fonctionnels

#### Test 1 : Création d'un Nouveau Trigger
- [ ] Ouvrir la page Cron Calendar
- [ ] Cliquer sur une date du mois en cours
- [ ] Vérifier que le formulaire s'ouvre
- [ ] Vérifier que la bannière bleue affiche la bonne date
- [ ] Vérifier que les sélecteurs d'heures sont visibles
- [ ] Vérifier que l'heure de début est 08:00
- [ ] Vérifier que l'heure de fin est 20:00
- [ ] Vérifier que l'expression cron correspond à la date sélectionnée

**Résultat attendu :**
```
Date cliquée : 1er mai 2026
Bannière : "Date sélectionnée: 1 mai 2026"
Heure début : 08:00
Heure fin : 20:00
Cron start : 0 8 1 5 *
Cron end : 0 20 1 5 *
```

#### Test 2 : Modification des Heures
- [ ] Créer un nouveau trigger (voir Test 1)
- [ ] Modifier l'heure de début à 09:30
- [ ] Vérifier que l'expression cron est mise à jour : `30 9 1 5 *`
- [ ] Modifier l'heure de fin à 17:45
- [ ] Vérifier que l'expression cron est mise à jour : `45 17 1 5 *`

**Résultat attendu :**
```
Heure début : 09:30 → Cron : 30 9 1 5 *
Heure fin : 17:45 → Cron : 45 17 1 5 *
```

#### Test 3 : Modification Directe de l'Expression Cron
- [ ] Créer un nouveau trigger
- [ ] Modifier directement le champ "Cron Start Expression" à `15 10 1 5 *`
- [ ] Vérifier que le sélecteur d'heure affiche 10:15
- [ ] Modifier directement le champ "Cron End Expression" à `30 18 1 5 *`
- [ ] Vérifier que le sélecteur d'heure affiche 18:30

**Résultat attendu :**
```
Synchronisation bidirectionnelle fonctionnelle
```

#### Test 4 : Création du Trigger
- [ ] Remplir tous les champs requis
- [ ] Cliquer sur "Create"
- [ ] Vérifier le message de succès : "Trigger updated"
- [ ] Vérifier que le formulaire se ferme
- [ ] Vérifier que le calendrier se rafraîchit
- [ ] Vérifier que l'événement apparaît dans la bonne cellule

**Résultat attendu :**
```
✅ Trigger créé avec succès
✅ Événement visible dans le calendrier
```

#### Test 5 : Édition d'un Trigger Existant
- [ ] Cliquer sur un événement existant dans le calendrier
- [ ] Vérifier que le formulaire s'ouvre en mode édition
- [ ] Vérifier que la bannière bleue N'est PAS affichée
- [ ] Vérifier que les sélecteurs d'heures NE sont PAS affichés
- [ ] Vérifier que seules les expressions cron sont visibles
- [ ] Modifier l'expression cron
- [ ] Cliquer sur "Update"
- [ ] Vérifier que les modifications sont sauvegardées

**Résultat attendu :**
```
Mode édition : Interface classique (sans sélecteurs d'heures)
```

#### Test 6 : Différentes Dates
Tester avec plusieurs dates :
- [ ] 1er du mois (ex: 1er mai)
- [ ] Milieu du mois (ex: 15 juin)
- [ ] Fin du mois (ex: 31 décembre)
- [ ] Mois à 1 chiffre (ex: 5 janvier → mois = 1)
- [ ] Mois à 2 chiffres (ex: 15 novembre → mois = 11)

**Résultat attendu :**
```
Toutes les dates génèrent des expressions cron correctes
```

#### Test 7 : Heures Limites
- [ ] Tester avec 00:00 (minuit)
- [ ] Tester avec 12:00 (midi)
- [ ] Tester avec 23:59 (fin de journée)
- [ ] Tester avec des minutes : 08:15, 14:30, 20:45

**Résultat attendu :**
```
Toutes les heures sont correctement converties en expressions cron
```

### ✅ Tests d'Interface

#### Test 8 : Affichage de la Bannière
- [ ] Vérifier que la bannière est bleue (bg-blue-50)
- [ ] Vérifier que la date est en français
- [ ] Vérifier que le texte d'aide est présent
- [ ] Vérifier que la bannière est responsive

**Résultat attendu :**
```
Bannière claire et informative
```

#### Test 9 : Sélecteurs d'Heures
- [ ] Vérifier que les champs sont de type "time"
- [ ] Vérifier que les labels sont corrects
- [ ] Vérifier que les champs sont côte à côte (grid-cols-2)
- [ ] Vérifier que les champs sont accessibles au clavier

**Résultat attendu :**
```
Interface intuitive et accessible
```

#### Test 10 : Responsive Design
- [ ] Tester sur écran large (desktop)
- [ ] Tester sur tablette
- [ ] Tester sur mobile
- [ ] Vérifier que le formulaire reste lisible

**Résultat attendu :**
```
Interface adaptée à tous les écrans
```

### ✅ Tests de Régression

#### Test 11 : Fonctionnalités Existantes
- [ ] Vérifier que le filtre ScaledObject fonctionne toujours
- [ ] Vérifier que le bouton "Refresh" fonctionne
- [ ] Vérifier que le bouton "Hide Recurring" fonctionne
- [ ] Vérifier que la navigation mois précédent/suivant fonctionne
- [ ] Vérifier que l'affichage des événements existants fonctionne

**Résultat attendu :**
```
Aucune régression sur les fonctionnalités existantes
```

#### Test 12 : Suppression de Trigger
- [ ] Créer un nouveau trigger
- [ ] Cliquer sur l'événement pour l'éditer
- [ ] Cliquer sur "Delete"
- [ ] Vérifier que le trigger est supprimé
- [ ] Vérifier que le calendrier se rafraîchit

**Résultat attendu :**
```
Suppression fonctionnelle
```

### ✅ Tests de Validation

#### Test 13 : Champs Requis
- [ ] Essayer de créer un trigger sans sélectionner de ScaledObject
- [ ] Vérifier le message d'erreur : "No ScaledObject selected"
- [ ] Essayer de créer un trigger avec une expression cron vide
- [ ] Vérifier le message d'erreur approprié

**Résultat attendu :**
```
Validation des champs fonctionnelle
```

#### Test 14 : Expressions Cron Invalides
- [ ] Entrer une expression cron invalide : "abc def"
- [ ] Essayer de créer le trigger
- [ ] Vérifier le comportement (erreur ou correction automatique)

**Résultat attendu :**
```
Gestion des erreurs appropriée
```

### ✅ Tests de Performance

#### Test 15 : Calendrier avec Beaucoup d'Événements
- [ ] Créer 20+ événements dans le mois
- [ ] Vérifier que le calendrier reste fluide
- [ ] Vérifier que les événements s'affichent correctement
- [ ] Vérifier le badge "+X more" pour les cellules avec >3 événements

**Résultat attendu :**
```
Performance acceptable même avec beaucoup d'événements
```

#### Test 16 : Changement de Mois Rapide
- [ ] Cliquer rapidement sur "mois suivant" plusieurs fois
- [ ] Vérifier qu'il n'y a pas de bug d'affichage
- [ ] Vérifier que les événements se chargent correctement

**Résultat attendu :**
```
Navigation fluide entre les mois
```

## 🐛 Tests de Cas Limites

#### Test 17 : Dates Spéciales
- [ ] 29 février (année bissextile)
- [ ] 31 janvier (mois avec 31 jours)
- [ ] 30 février (invalide - ne devrait pas exister)
- [ ] Changement d'année (31 décembre → 1er janvier)

**Résultat attendu :**
```
Gestion correcte des dates spéciales
```

#### Test 18 : Timezones
- [ ] Créer un trigger avec timezone UTC
- [ ] Créer un trigger avec timezone Europe/Paris
- [ ] Vérifier que les heures sont correctement interprétées
- [ ] Vérifier l'affichage dans le calendrier

**Résultat attendu :**
```
Gestion correcte des timezones
```

#### Test 19 : Caractères Spéciaux
- [ ] Essayer d'entrer des caractères spéciaux dans les champs
- [ ] Vérifier que l'application ne plante pas
- [ ] Vérifier la validation des entrées

**Résultat attendu :**
```
Validation robuste des entrées
```

## 📊 Résultats Attendus

### Critères de Succès
- ✅ Tous les tests fonctionnels passent
- ✅ Aucune régression sur les fonctionnalités existantes
- ✅ Interface intuitive et responsive
- ✅ Performance acceptable
- ✅ Gestion des erreurs appropriée

### Métriques
- **Temps de création d'un trigger** : < 30 secondes
- **Taux d'erreur utilisateur** : < 5%
- **Satisfaction utilisateur** : > 90%

## 🔧 Commandes de Test

### Démarrer le Frontend
```bash
cd frontend
npm start
```

### Accéder à la Page
```
http://localhost:3000/cron-calendar
```

### Vérifier les Logs Console
```javascript
// Ouvrir la console du navigateur (F12)
// Vérifier qu'il n'y a pas d'erreurs JavaScript
```

### Tester avec Différents Navigateurs
- [ ] Chrome
- [ ] Firefox
- [ ] Safari
- [ ] Edge

## 📝 Rapport de Test

### Template de Rapport
```markdown
# Rapport de Test - Présélection de Date Calendrier

**Date** : [Date du test]
**Testeur** : [Nom]
**Version** : [Version de l'application]

## Tests Réussis
- [ ] Test 1 : Création d'un nouveau trigger
- [ ] Test 2 : Modification des heures
- [ ] ...

## Tests Échoués
- [ ] Test X : [Description]
  - **Erreur** : [Description de l'erreur]
  - **Étapes pour reproduire** : [Étapes]
  - **Résultat attendu** : [Résultat]
  - **Résultat obtenu** : [Résultat]

## Bugs Trouvés
1. [Description du bug]
   - **Sévérité** : Critique / Majeur / Mineur
   - **Priorité** : Haute / Moyenne / Basse

## Recommandations
- [Recommandation 1]
- [Recommandation 2]

## Conclusion
[Résumé global des tests]
```

## 🎯 Checklist Finale

Avant de déployer en production :
- [ ] Tous les tests fonctionnels passent
- [ ] Aucune régression détectée
- [ ] Tests sur tous les navigateurs principaux
- [ ] Tests sur mobile et tablette
- [ ] Documentation à jour
- [ ] Code review effectué
- [ ] Build de production réussi
- [ ] Tests de performance OK

---

**Note** : Ce plan de tests est exhaustif. Priorisez les tests critiques (1-7, 11-13) pour une première validation, puis effectuez les tests complémentaires.
