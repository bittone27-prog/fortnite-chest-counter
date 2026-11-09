# Fortnite Chest Counter

Compteur de coffres Fortnite pour PC (Windows), directement dans le navigateur.

## Utilisation

1. Dans Fortnite : Paramètres vidéo → Mode d'affichage : **Plein écran fenêtré** (le plein écran exclusif ne peut pas être capturé).
2. Ouvrez l'application dans **Chrome ou Edge**.
3. Cliquez sur **Start** et choisissez la fenêtre Fortnite (ou l'écran entier).
4. Ajustez **Sensibilité** et **Taille min.** si besoin. Cochez « Afficher les zones » pour voir ce que l'algorithme repère.

## Raccourcis

| Touche | Action |
|---|---|
| `+` | Ajouter un coffre |
| `-` | Retirer un coffre |
| `Espace` | Start / Pause |
| `R` | Reset |

## Fonctionnalités

- Détection automatique par analyse d'image (lueur dorée des coffres), suivi temporel et anti-doublon
- Compteur géant avec animation et son à chaque coffre
- Coffres par minute, durée de partie, historique détaillé
- Meilleur record personnel et 10 dernières parties (stockés en `localStorage`)
- Mode manuel complet si la détection n'est pas adaptée

## Éthique et sécurité

L'application analyse uniquement les pixels de votre écran via l'API de capture du navigateur (`getDisplayMedia`), comme OBS ou Discord.

- Aucune lecture de la mémoire du jeu
- Aucune injection de code
- Aucun fichier Fortnite modifié
- Aucune information supplémentaire par rapport à ce que vous voyez déjà à l'écran

## Limites

La détection par couleur est approximative (effets dorés, coffres très lointains). Le compteur « Ouverts » est une estimation. Une amélioration possible : remplacer la détection par un modèle TensorFlow.js / YOLO entraîné sur des captures de coffres.
