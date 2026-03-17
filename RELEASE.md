# Publication de Releases AMORA

Ce document explique comment publier une nouvelle version de l'application AMORA.

## Prérequis

- Les secrets GitHub doivent être configurés (une seule fois) :
  - `TAURI_SIGNING_PRIVATE_KEY` : La clé de signature privée
  - `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` : Le mot de passe de la clé (peut être vide)

## Workflow Automatique

Le workflow GitHub Actions (`.github/workflows/release.yml`) se déclenche automatiquement quand vous poussez un tag commençant par `v`.

### Étapes pour publier une nouvelle version

1. **Mettre à jour le numéro de version** dans `frontend/src-tauri/tauri.conf.json` :

   ```json
   {
     "version": "0.2.0"
   }
   ```

2. **Commiter les changements** :

   ```bash
   git add .
   git commit -m "chore: bump version to 0.2.0"
   git push
   ```

3. **Créer et pousser le tag** :

   ```bash
   git tag v0.2.0
   git push origin v0.2.0
   ```

4. **Attendre le build** - Vous pouvez suivre la progression sur :
   ```
   https://github.com/Jedanns/amora/actions
   ```

5. **Vérifier la release** - Une fois terminé, la release sera disponible sur :
   ```
   https://github.com/Jedanns/amora/releases
   ```

## Mise à jour Automatique côté Utilisateur

Les utilisateurs ayant une version précédente de l'application :

1. Voient "Recherche de mises à jour..." au démarrage
2. Si une mise à jour existe, une barre de progression apparaît pendant le téléchargement
3. L'application redémarre automatiquement après l'installation

Le tout sans intervention manuelle.

## Structure d'une Release GitHub

Le workflow génère automatiquement :

| Fichier | Description |
|---------|-------------|
| `AMORA_X.X.X_x64-setup.exe` | Installeur NSIS (recommandé) |
| `AMORA_X.X.X_x64_en-US.msi` | Installeur MSI alternatif |
| `latest.json` | Métadonnées pour l'auto-update |

## Développement Local

Pour tester en mode développement (hot-reload sans recompiler) :

```bash
cd frontend
npm run tauri dev
```

## Rétrograder une Version

Par défaut, l'updater n'accepte que les versions plus récentes. Pour permettre un rollback, vous devez modifier le comparateur de version dans le code Rust.

## Dépannage

### Le build GitHub Actions échoue

- Vérifiez que les secrets `TAURI_SIGNING_PRIVATE_KEY` et `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` sont bien configurés dans Settings > Secrets and variables > Actions
- Vérifiez que la clé privée correspond à la clé publique dans `tauri.conf.json`

### L'updater ne trouve pas de mise à jour

- Vérifiez que `latest.json` existe dans la release GitHub
- Vérifiez que l'URL dans `tauri.conf.json` pointe vers `https://github.com/Jedanns/amora/releases/latest/download/latest.json`

### Erreur de signature

Si vous perdez la clé privée, vous devrez :
1. Générer une nouvelle paire de clés
2. Mettre à jour la clé publique dans `tauri.conf.json`
3. Publier une nouvelle version majeure (ex: v1.0.0)
4. Les utilisateurs devront réinstaller manuellement (la mise à jour automatique sera cassée pour les anciennes versions)

## Générer de Nouvelles Clés de Signature

```bash
npm run tauri signer generate -w ~/.tauri/amora.key --ci -p ""
```

cela génère :
- `~/.tauri/amora.key` (privée, à garder secrète)
- `~/.tauri/amora.key.pub` (publique, à mettre dans `tauri.conf.json`)

N'oubliez pas de mettre à jour le secret GitHub avec la nouvelle clé privée.