# EKD School Manager — application mobile

Application Flutter pour le personnel de l'établissement et les parents. Elle
consomme l'API Django du dossier `backend/` ; elle ne double aucune logique
métier — les calculs de moyennes, de rangs et d'écolage restent côté serveur.

## Démarrer

```bash
flutter pub get

# Émulateur Android : 10.0.2.2 est l'alias de la machine hôte (valeur par défaut)
flutter run

# Téléphone physique sur le même réseau : indiquez l'IP du poste de développement
flutter run --dart-define=API_URL=http://192.168.1.10:8000/api
```

Le serveur Django doit écouter sur toutes les interfaces pour qu'un téléphone
puisse le joindre :

```bash
python manage.py runserver 0.0.0.0:8000
```

> **HTTP en clair.** Android bloque le HTTP non chiffré depuis la version 9.
> [`network_security_config.xml`](android/app/src/main/res/xml/network_security_config.xml)
> ouvre l'exception pour `10.0.2.2`, `localhost` et `127.0.0.1` seulement. Pour
> tester sur un téléphone physique via une IP locale, ajoutez cette IP au
> fichier. En production, servez l'API en HTTPS plutôt que d'élargir la liste.

## Rôles et écrans

Les écrans ne sont pas attribués rôle par rôle : chaque rôle porte un ensemble
de **capacités**, et chaque écran demande une capacité. C'est ce qui fait que
certains écrans sont partagés sans duplication de code — proviseur, censeur et
propriétaire pilotent le même établissement, enseignant et surveillant font le
même appel.

La matrice vit dans [`lib/core/roles.dart`](lib/core/roles.dart) et reproduit
les contrôles d'accès des vues Django. Elle ne les remplace pas : le serveur
reste seul juge, la matrice évite seulement d'afficher un écran qui répondrait
« permission refusée ».

| Écran | Enseignant | Comptable | Surveillant | Censeur | Proviseur | Propriétaire | Parent |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| Accueil | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Notes (consultation + saisie) | ✓ | | | ✓ | ✓ | ✓ | |
| Appel | ✓ | | ✓ | ✓ | ✓ | ✓ | |
| Discipline | ✓ | | ✓ | ✓ | ✓ | ✓ | |
| Écolage (encaissements, recouvrement) | | ✓ | | | ✓ | ✓ | |
| Dépenses | | ✓ | | | ✓ | ✓ | |
| Bulletins | | | | ✓ | ✓ | ✓ | |
| Élèves | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | |
| Emploi du temps (général) | | | ✓ | ✓ | ✓ | ✓ | |
| Mes cours | ✓ | | | | | | |
| Mes enfants | | | | | | | ✓ |
| Profil | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

Le censeur configure l'écolage mais ne l'encaisse pas — `ensure_fee_configurator`
l'autorise, `ensure_finance_manager` ne le liste pas. La matrice reflète cette
distinction.

**Le rôle dépend de l'école.** Une même personne peut être enseignante dans un
établissement et censeur dans un autre : c'est `user_role` de l'appartenance
qui commande, pas le rôle du compte. Changer d'école change les onglets.

## État de l'espace parent

⚠️ **Les écrans parent affichent des données de démonstration**, signalées par
un bandeau dans l'application. Le backend n'expose aujourd'hui aucun accès
parent :

- `accessible_schools()` ne reconnaît que les propriétaires et les membres du
  personnel ; un parent n'est rattaché à une école que par
  `StudentEnrollment.guardian` et reçoit donc une liste d'écoles vide ;
- aucun endpoint ne renvoie « mes enfants » — `ParentListView` est l'annuaire
  des parents à l'usage du personnel, pas la vue d'un parent sur sa famille.

La forme des données de [`demo_data.dart`](lib/screens/parent/demo_data.dart)
anticipe celle des futurs endpoints : le branchement consistera à remplacer
`demoChildren` par un appel de service.

## Organisation

```
lib/
  core/        config, thème, rôles et capacités, table de navigation
  api/         client HTTP (jeton, en-têtes école/année) et services
  models/      types de l'API
  state/       session : jeton, école, année, capacités
  screens/     shared/ teacher/ finance/ discipline/ direction/ parent/
  widgets/     briques communes (états vides, erreurs, tuiles, ossature)
```

Le client API porte le jeton et l'en-tête `X-Academic-Year-ID` que la plupart
des vues Django exigent, et ferme la session quand le serveur rejette le jeton.

## Vérifier

```bash
flutter analyze   # aucune remarque attendue
flutter test      # matrice des rôles et navigation
flutter build apk --debug
```
