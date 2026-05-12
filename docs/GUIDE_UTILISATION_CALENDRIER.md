# 📖 Guide d'Utilisation : Création de Cron Trigger depuis le Calendrier

## 🎯 Scénario : Créer un événement pour le 1er mai

### Étape 1 : Naviguer vers le Calendrier
```
Dashboard → Cron Calendar
```

### Étape 2 : Cliquer sur la Date Souhaitée
```
┌─────────────────────────────────────────────────────┐
│                    Mai 2026                         │
├─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────────┤
│ Lun │ Mar │ Mer │ Jeu │ Ven │ Sam │ Dim │         │
├─────┼─────┼─────┼─────┼─────┼─────┼─────┼─────────┤
│     │     │     │     │  1  │  2  │  3  │         │
│     │     │     │     │ [👆]│     │     │ ← Clic  │
├─────┼─────┼─────┼─────┼─────┼─────┼─────┼─────────┤
│  4  │  5  │  6  │  7  │  8  │  9  │ 10  │         │
└─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────────┘
```

### Étape 3 : Le Formulaire s'Ouvre Automatiquement

```
┌────────────────────────────────────────────────────┐
│  New Cron Trigger                            [✕]   │
│  Add a new cron trigger to a ScaledObject          │
├────────────────────────────────────────────────────┤
│                                                    │
│  SCALEDOBJECT                                      │
│  ┌──────────────────────────────────────────────┐ │
│  │ appreadiness-manager (appreadiness)      [▼] │ │
│  └──────────────────────────────────────────────┘ │
│                                                    │
│  ┌──────────────────────────────────────────────┐ │
│  │ 📅 Date sélectionnée: 1 mai 2026            │ │
│  │ 💡 Ajustez les heures de début et de fin    │ │
│  └──────────────────────────────────────────────┘ │
│                                                    │
│  HEURE DE DÉBUT          HEURE DE FIN             │
│  ┌──────────────────┐   ┌──────────────────┐     │
│  │ 08:00        [🕐]│   │ 20:00        [🕐]│     │
│  └──────────────────┘   └──────────────────┘     │
│                                                    │
│  CRON START EXPRESSION                             │
│  ┌──────────────────────────────────────────────┐ │
│  │ 0 8 1 5 *                                    │ │
│  └──────────────────────────────────────────────┘ │
│                                                    │
│  CRON END EXPRESSION                               │
│  ┌──────────────────────────────────────────────┐ │
│  │ 0 20 1 5 *                                   │ │
│  └──────────────────────────────────────────────┘ │
│                                                    │
│  DESIRED REPLICAS        TIMEZONE                  │
│  ┌──────────────────┐   ┌──────────────────┐     │
│  │ 10               │   │ UTC          [▼] │     │
│  └──────────────────┘   └──────────────────┘     │
│                                                    │
│                    [ Cancel ]  [ Create ]          │
└────────────────────────────────────────────────────┘
```

### Étape 4 : Ajuster les Heures (Optionnel)

#### Option A : Utiliser les Sélecteurs d'Heures
```
Clic sur le champ "Heure de début"
┌──────────────────┐
│ 08:00        [🕐]│ ← Clic
└──────────────────┘
        ↓
┌──────────────────┐
│ 09:30        [🕐]│ ← Nouvelle heure
└──────────────────┘

Résultat automatique :
Expression cron mise à jour : 0 8 1 5 * → 30 9 1 5 *
```

#### Option B : Modifier Directement l'Expression Cron
```
CRON START EXPRESSION
┌──────────────────────────────────────────────┐
│ 0 8 1 5 *                                    │ ← Édition manuelle
└──────────────────────────────────────────────┘
        ↓
┌──────────────────────────────────────────────┐
│ 30 9 1 5 *                                   │
└──────────────────────────────────────────────┘
```

### Étape 5 : Créer le Trigger
```
Clic sur [ Create ]
        ↓
✅ Notification : "Trigger updated"
        ↓
Le calendrier se rafraîchit automatiquement
```

### Étape 6 : Vérifier dans le Calendrier
```
┌─────────────────────────────────────────────────────┐
│                    Mai 2026                         │
├─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────────┤
│ Lun │ Mar │ Mer │ Jeu │ Ven │ Sam │ Dim │         │
├─────┼─────┼─────┼─────┼─────┼─────┼─────┼─────────┤
│     │     │     │     │  1  │  2  │  3  │         │
│     │     │     │     │ ┌─┐ │     │     │         │
│     │     │     │     │ │1│ │     │     │ ← Badge │
│     │     │     │     │ └─┘ │     │     │         │
│     │     │     │     │09:30│     │     │ ← Heure │
│     │     │     │     │app..│     │     │ ← Nom   │
├─────┼─────┼─────┼─────┼─────┼─────┼─────┼─────────┤
```

## 🎨 Cas d'Usage Courants

### Cas 1 : Événement Ponctuel (Journée Complète)
```
Date : 15 juin 2026
Début : 00:00
Fin : 23:59
→ Cron : 0 0 15 6 * / 59 23 15 6 *
```

### Cas 2 : Heures de Bureau
```
Date : 20 juillet 2026
Début : 09:00
Fin : 17:00
→ Cron : 0 9 20 7 * / 0 17 20 7 *
```

### Cas 3 : Événement de Nuit
```
Date : 31 décembre 2026
Début : 22:00
Fin : 02:00 (lendemain)
→ Cron : 0 22 31 12 * / 0 2 1 1 *
```

### Cas 4 : Demi-Heures
```
Date : 10 août 2026
Début : 08:30
Fin : 18:45
→ Cron : 30 8 10 8 * / 45 18 10 8 *
```

## 🔄 Comparaison Avant/Après

### Avant (Méthode Manuelle)
```
1. Clic sur date                    [5 sec]
2. Calculer le jour du mois         [10 sec]
3. Calculer le numéro du mois       [5 sec]
4. Écrire l'expression cron         [30 sec]
5. Vérifier la syntaxe              [20 sec]
6. Corriger les erreurs             [30 sec]
7. Créer le trigger                 [5 sec]
────────────────────────────────────────────
Total : ~105 secondes (1m45s)
Risque d'erreur : Élevé ⚠️
```

### Après (Méthode Automatique)
```
1. Clic sur date                    [5 sec]
2. Ajuster l'heure de début         [5 sec]
3. Ajuster l'heure de fin           [5 sec]
4. Créer le trigger                 [5 sec]
────────────────────────────────────────────
Total : ~20 secondes
Risque d'erreur : Très faible ✅
```

**Gain de temps : 85% 🚀**

## 💡 Astuces

### Astuce 1 : Heures par Défaut
Les heures par défaut (8h-20h) correspondent à une journée de travail standard. Si vous créez souvent des événements avec ces heures, vous n'avez rien à modifier !

### Astuce 2 : Expressions Cron Avancées
Pour des patterns récurrents (tous les lundis, tous les jours, etc.), vous pouvez toujours modifier directement l'expression cron après la création initiale.

### Astuce 3 : Édition Rapide
Cliquez sur un événement existant dans le calendrier pour l'éditer rapidement.

### Astuce 4 : Filtrage
Utilisez le filtre "ScaledObject" en haut à droite pour voir uniquement les événements d'un objet spécifique.

### Astuce 5 : Masquer les Récurrents
Cliquez sur "Hide Recurring" pour masquer les événements qui se répètent quotidiennement et voir uniquement les événements ponctuels.

## ❓ FAQ

### Q : Puis-je toujours créer des cron récurrents ?
**R :** Oui ! Après avoir créé l'événement pour une date spécifique, vous pouvez éditer l'expression cron pour la rendre récurrente. Par exemple, changer `0 8 1 5 *` en `0 8 * * 1-5` pour tous les jours de semaine.

### Q : Que se passe-t-il si je clique sur une date du mois précédent/suivant ?
**R :** Le formulaire s'ouvre uniquement pour les dates du mois en cours. Les dates grisées (mois précédent/suivant) ne sont pas cliquables.

### Q : Puis-je créer plusieurs événements pour la même date ?
**R :** Oui ! Cliquez à nouveau sur la date et créez un nouveau trigger. Ils apparaîtront tous dans la cellule du calendrier.

### Q : Comment supprimer un événement ?
**R :** Cliquez sur l'événement dans le calendrier, puis sur le bouton "Delete" dans le formulaire d'édition.

### Q : Les heures sont-elles en heure locale ou UTC ?
**R :** Par défaut, les heures sont en UTC. Vous pouvez changer le timezone dans le champ "TIMEZONE" du formulaire.

## 🎓 Comprendre les Expressions Cron

### Format
```
minute  hour  day  month  dayOfWeek
  │      │     │     │        │
  │      │     │     │        └─ Jour de la semaine (0-7, 0=dimanche)
  │      │     │     └────────── Mois (1-12)
  │      │     └──────────────── Jour du mois (1-31)
  │      └────────────────────── Heure (0-23)
  └───────────────────────────── Minute (0-59)
```

### Exemples
```
0 8 1 5 *       → 1er mai à 08:00
30 14 15 12 *   → 15 décembre à 14:30
0 9 * * 1-5     → Tous les jours de semaine à 09:00
0 0 1 * *       → Le 1er de chaque mois à minuit
0 12 * * 0      → Tous les dimanches à midi
```

---

**Bon à savoir** : Cette interface simplifie la création d'événements ponctuels. Pour des patterns complexes, vous pouvez toujours utiliser la syntaxe cron complète ! 🎯
