# Demandes et Vision du Projet

Recapitulatif de toutes les demandes et retours du joueur, avec references aux screenshots d'Old Greg's Tavern comme inspiration.

---

## 1. Intelligence de l'IA

### Probleme constate
- L'IA (Llama 3.2 3B) est trop bete : elle joue a la place du joueur, invente des stats, se repete, genere des headers markdown, pose "Qu'est-ce que tu fais ?" et ajoute des remarques meta.
- L'IA doit etre **autonome et intelligente** : elle doit decider elle-meme la longueur de sa reponse, le ton, le niveau de detail. Pas de limitation arbitraire de tokens.

### Ce qui est demande
- L'IA doit **cogiter, raisonner, "think" avant de repondre** : comparer differentes possibilites de reponse, s'assurer de la coherence, verifier ce qu'elle a ecrit.
- Le jeu doit etre **completement automatise** : le moteur gere tout, l'IA narre, le joueur joue. Pas d'intervention manuelle.
- Upgrade vers le meilleur modele possible (Qwen 3 8B choisi, en cours de test).

### Statut
- [x] Upgrade vers Qwen 3 8B (telecharge, configure)
- [ ] Tester le nouveau modele et ajuster si necessaire
- [ ] Si insuffisant, tester Gemma 3 12B ou Mistral Nemo 12B

---

## 2. Moteur de jeu : personnage, stats, inventaire

### Probleme constate
- Le joueur est cense avoir un personnage avec une fiche complete, des stats, un inventaire, de l'equipement. Le backend gere tout ca mais l'interface ne l'exploite pas encore.
- L'IA invente les possessions du joueur ("Tu as 5 pieces d'argent, une epee de base") au lieu d'utiliser les vraies donnees du moteur.

### Ce qui est demande (inspire des screenshots Old Greg's Tavern)

#### Fiche personnage (screenshot 3 - onglet 2)
- Portrait du personnage (image)
- Nom + classe (ex: "Iron Fist Monk")
- Barres PV / Ame (mana) / XP avec valeurs numeriques
- Diagramme radar des attributs (hexagone)
- Arbre de competences par categorie :
  - AVENTURIER : Investigation, Escalade, Visee, Maitrise des Betes
  - BRUTE : Combat Rapproche, A Distance, Une Main, Deux Mains
  - VOLEUR : Acrobatie, Prestidigitation, Discretion, Crochetage
  - SILVER TONGUE : Tromperie, Persuasion, Representation, Intimidation, Seduction, Negociation
- Chaque competence a un modificateur (+/-), une barre de progression, un niveau (ex: 0/12)

#### Inventaire (screenshot 5 - onglet 3)
- Panneau stats rapides : Couronnes (or), CA (classe d'armure), Degats, Bonus main
- Section EQUIPE : slots visuels (arme main 1, arme main 2) + slots armure (Tete, Torse, Bras, Jambes, Cape) avec nom + bonus
- Section ARMES : liste d'armes avec nom, type, slot, valeur, bouton equiper/desequiper
- Section ARMURE : idem pour les armures
- Section CONSUMABLES : potions etc. avec bouton "Use"
- Onglet SPELLBOOK pour les sorts

#### Relations PNJ (screenshot 6 - onglet 4)
- Liste des PNJ rencontres avec :
  - Portrait
  - Nom (ex: "Aldric le Forgeron")
  - Etat emotionnel / disposition (ex: "Curious", "Guarded")
  - Barre de relation (R1 a R10)
- Section OSSUARY (PNJ morts)
- Barre de recherche

### Statut
- [x] Backend : personnage, stats, inventaire, equipement existent dans le code
- [ ] Injecter les vraies stats du personnage dans le prompt de l'IA
- [ ] Refaire l'UI avec les onglets style Old Greg's Tavern
- [ ] Systeme de competences par categorie
- [ ] Systeme de relations PNJ
- [ ] Portraits de personnages

---

## 3. Application desktop (.exe)

### Probleme constate
- Le joueur ne veut pas ouvrir un navigateur et aller sur localhost:8000 pour jouer.

### Ce qui est demande
- Une **application .exe native** sur Windows, pas un site web.
- Solution recommandee : Tauri (Rust) qui wrappe le HTML/JS en .exe natif, leger et rapide.

### Statut
- [ ] Installer Rust + outils Tauri
- [ ] Wrapper l'app web existante en .exe
- [ ] Lancement en un clic (lance KoboldCPP + API + fenetre)

---

## 4. Hub / ecran d'accueil (inspire screenshot 1)

### Ce qui est demande
- Un **ecran d'accueil** au lancement avec :
  - "Bienvenue, [Pseudo]"
  - Message d'accroche ("Vos quetes vous attendent...")
  - Bouton "Nouvelle Campagne"
  - Liste "Vos Campagnes" avec pour chaque campagne :
    - Nom de la campagne
    - Portrait du personnage
    - Tags (Demo, nombre de joueurs...)
    - Date de derniere partie
    - Bouton "Jouer"
  - Filtre / tri des campagnes

### Statut
- [ ] Backend : systeme de sessions multiples existe deja
- [ ] Creer l'ecran d'accueil / hub
- [ ] Persistence des campagnes avec leur propre historique et memoire
- [ ] Chaque personnage a ses propres infos et son propre monde

---

## 5. Interface de jeu principale (inspire screenshot 2)

### Ce qui est demande
- Layout 3 colonnes comme Old Greg's Tavern :
  - **Gauche** : panneau lateral avec onglets (1: Quetes, 2: Personnage, 3: Inventaire, 4: Relations)
  - **Centre** : zone de narration principale avec :
    - Label "Maitre du Donjon" en haut
    - Info contextuelle (lieu, moment de la journee)
    - Texte narratif avec mise en forme :
      - Noms de PNJ en couleur (ex: "Aldric" en or/jaune)
      - Nom du joueur en couleur (ex: "Lucas" en rouge)
      - Dialogues entre guillemets
      - Mots-cles importants en couleur (ex: "forgeron", "Mercenaires de la Main de Fer")
    - Icone son/TTS optionnelle
  - **Droite** : fiche personnage rapide (portrait, classe, PV, Ame, niveau)

### Panneau quetes (screenshot 2 - onglet 1)
- Liste des quetes actives avec :
  - Nom de la quete
  - Niveau + XP de recompense
  - Description en italique
  - Recompense
  - Boutons accepter/refuser/marquer
- Section RUMEURS (quetes potentielles)
- Notes du MJ (bullet points de ce que les PNJ ont dit)

### Statut
- [x] Layout 3 colonnes basique existe
- [x] Coloration syntaxique basique (dialogues, noms PNJ, lieux, items)
- [ ] Onglets dans le panneau gauche (Quetes/Perso/Inventaire/Relations)
- [ ] Panneau quetes complet
- [ ] Info contextuelle (lieu + moment) dans la zone de narration
- [ ] Panneau personnage dans la colonne droite
- [ ] Style visuel plus proche d'Old Greg's Tavern (fond noir, bordures dorees)

---

## 6. Coloration et mise en forme du texte narratif

### Ce qui est demande
- Code couleur pour les elements importants dans le texte du MJ :
  - **Noms de PNJ** : couleur distinctive (rouge/or)
  - **Nom du joueur** : autre couleur
  - **Lieux** : vert
  - **Items / objets** : bleu
  - **Mots-cles de quetes / factions** : couleur speciale (ex: "Mercenaires de la Main de Fer" en or souligne)
  - **Dialogues** : entre guillemets, italique jaune
  - **References de des** : or

### Statut
- [x] Systeme de coloration basique implemente (dialogues, PNJ, lieux, items, des)
- [x] Detection automatique de nouveaux noms/lieux/items
- [ ] Coloration du nom du joueur
- [ ] Coloration des factions/organisations
- [ ] Style plus raffine (soulignement, gras contextuel)

---

## Resume des priorites

1. **Tester Qwen 3 8B** et valider la qualite (EN COURS)
2. **Connecter le moteur de jeu** : injecter les vraies stats dans le prompt
3. **Refaire l'UI** style Old Greg's Tavern avec onglets
4. **Hub / ecran d'accueil** avec gestion des campagnes
5. **Application .exe** avec Tauri
6. **Systemes avances** : competences, relations PNJ, portraits
