# MASTERPLAN.md — Spécifications Techniques Complètes

> **Version**: 1.2.0  
> **Dernière mise à jour**: Mars 2026  
> **Statut**: Planification active  
> **Cible matérielle**: ASUS ROG Zephyrus G14 GA403UU  
> **Modèle principal**: Llama 4 Scout (MoE Offloading + IQ2_XXS)

---

## Table des matières

1. [Vision et objectifs](#1--vision-et-objectifs)
2. [Architecture technique](#2--architecture-technique)
3. [Modèle de données](#3--modèle-de-données)
4. [Gestion d'état](#4--gestion-détat)
5. [Système Lorebook](#5--système-lorebook)
6. [Mécaniques de jeu](#6--mécaniques-de-jeu)
7. [Intégration LLM](#7--intégration-llm)
8. [Mémoire et contexte](#8--mémoire-et-contexte)
9. [Gestion des erreurs](#9--gestion-des-erreurs)
10. [Sécurité](#10--sécurité)
11. [Performance](#11--performance)
12. [Tests](#12--tests)
13. [Logging et monitoring](#13--logging-et-monitoring)
14. [Configuration](#14--configuration)
15. [Plan de déploiement](#15--plan-de-déploiement)
16. [Gestion des risques](#16--gestion-des-risques)
17. [Feuille de route](#17--feuille-de-route)
18. [Standards de qualité](#18--standards-de-qualité)
19. [Annexes](#annexes)

---

## 1 · Vision et objectifs

### 1.1 Objectif principal

Créer un moteur de jeu de rôle narratif alimenté par IA, 100% local, avec:
- Cohérence narrative sur des campagnes longues (100+ heures)
- Mécaniques de jeu validées (jets de dés, stats, inventaire)
- Extensibilité (ajout de mondes, règles, classes)
- Performance optimisée pour RTX 4050 (6GB VRAM) + Ryzen 9 8945HS

### 1.2 Objectifs mesurables

| Métrique | Cible | Seuil critique |
|----------|-------|-----------------|
| Temps de réponse LLM | < 5 secondes (premier token) | > 15s |
| Injection lore | < 100ms | > 500ms |
| Sauvegarde session | < 500ms | > 2s |
| Chargement session | < 2s | > 10s |
| Recherche RAG | < 200ms | > 1s |
| Calcul de stats | < 10ms | > 100ms |
| Vitesse génération | > 8 tokens/sec | < 5 tok/s |
| Utilisation RAM | < 20 GB (reserve pour OS) | > 24 GB |
| Utilisation VRAM | < 5.5 GB (reserve système) | > 5.8 GB |

### 1.4 Configuration matérielle cible

**Matériel détecté:**

| Composant | Spécification | Impact |
|-----------|---------------|--------|
| **OS** | Windows11 Professionnel (Build 26200) | Natif, pas de WSL requis |
| **CPU** | AMD Ryzen 9 8945HS (8c/16t, 4.0GHz) | Multithreading pour offloading |
| **GPU** | NVIDIA RTX 4050 Laptop (6GB VRAM) |Contrainte principale pour modèles |
| **iGPU** | AMD Radeon 780M | Non utilisable pour ML (pas de ROCm laptop) |
| **RAM** | 32GB DDR5 (~24GBdisponible) | Offloading généreux possible |
| **Stockage** | SSD NVMe (assumé) | Chargement rapide modèles |
| **Sécurité** | VBS/HVCI activé | Peut impacter Docker/WSL2 |

**Allocation mémoire recommandée:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ALLOCATION MÉMOIRE (32GB RAM)                            │
│                                                                             │
│  VRAM RTX 4050 (6GB)                                                        │
│  ├── Modèle Q4_K_M (3.5-4GB)                                               │
│  ├── Contexte KV Cache 4-bit (1-1.5GB)                                     │
│  └── Réserve système (0.5-1GB)                                              │
│                                                                             │
│  RAM système (32GB total, ~24GB utilisables)                               │
│  ├── OS + applications (4-6GB)                                             │
│  ├── Modèle offloaded (si nécessaire) (8-12GB)                             │
│  ├── Lorebook + embeddings RAG (2-4GB)                                     │
│  ├── Cache contexte + état (1-2GB)                                        │
│  └── Réserve (2-4GB)                                                        │
│                                                                             │
│  ════════════════════════════════════════════════════════════════════════  │
│  CAPACITÉ MAX: Modèle 12B en Q3/Q4 avec offloading                         │
│  RECOMMANDÉ: Modèle 7-8B en Q5_K_M (GPU uniquement)                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.5 Implications de la configuration

**Avantages:**
- CPU 8 cœurs → Multithreading efficace pour prétraitement
- 32GB RAM → Offloading généreux, modèles 12-20B possibles
- RTX 4050 Ada Lovelace → Architecture moderne, DLSS disponible
- SSD NVMe → Temps de chargement minimisés

**Contraintes:**
- **VRAM limitée (6GB)** → Modèles ≤8B recommandés enfull GPU, ≤12B en hybrid
- **iGPU AMD** → Pas utilisable pour ML (ROCmlimité aux GPU desktop)
- **VBS activé** → Peut réduire performance Docker/WSL2 de 5-15%
- **Laptop** → Thermiques à surveiller sous charge longue

**Recommandations spécifiques:**

| Aspect | Recommandation | Raison |
|--------|----------------|--------|
| **Modèle principal** | **Llama 4 Scout IQ2_XXS** | 17B actifs, 10M contexte, multimodal, français natif |
| Modèle alternatif | Mistral 7B Q4_K_M | GPU pur, plus rapide |
| Modèle léger | Llama 3.2 3B Q5_K_M | Tâches secondaires, embeddings |
| Contexte max | 10k-16k tokens | Avec KV Cache 4-bit |
| Embeddings RAG | all-MiniLM-L6-v2 | CPU, rapide |

### 1.6 Llama 4 Scout — Configuration détaillée

**Architecture MoE (Mixture-of-Experts):**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    LLAMA 4 SCOUT — ARCHITECTURE MoE                         │
│                                                                             │
│  Paramètres totaux: 109B                                                    │
│  Paramètres actifs par token: 17B                                           │
│  Nombre d'experts: 16                                                       │
│  Experts actifs par token: 1-2                                              │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    VRAM (6GB RTX 4050)                              │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │  Attention Layers (~2GB)                                    │   │   │
│  │  │  ├── Self-attention                                        │   │   │
│  │  │  ├── Layer norm                                            │   │   │
│  │  │  └── Position embeddings                                   │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │  KV Cache Q4 (~1GB pour 16k tokens)                         │   │   │
│  │  │  └── Contexte de conversation compressé                     │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │  Flash Attention buffers (~0.5GB)                           │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │  Réserve système (~2.5GB)                                   │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    RAM (24GB disponibles)                           │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │  Experts MoE (~8-10GB en IQ2_XXS)                          │   │   │
│  │  │  ├── 16 experts × ~500MB chacun                            │   │   │
│  │  │  └── Chargés à la demande (lazy loading)                   │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │  Lorebook + Embeddings RAG (~2-4GB)                         │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │  Cache contexte + État (~1-2GB)                            │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Techniques d'optimisation pour 6GB VRAM:**

| Technique | Description | Gain |
|-----------|-------------|------|
| **MoE Offloading** | Experts en RAM, attention en VRAM | Permet 109B modèle sur 6GB |
| **IQ2_XXS** (2.4-bit) | Quantization ultra-aggressive | Taille ÷2 vs Q4, perte minime |
| **BitNet b1.58** | Quantization native 1.58-bit | Modèle ~3-4GB (si disponible) |
| **KV Cache Q4** | Contexte compressé4-bit | 16k tokens dans ~1GB |
| **Flash Attention 2** | Optimisation mémoire attention | -20-30% VRAM |

**Performance estimée (RTX 4050):**

| Configuration | VRAM | Contexte | Vitesse estimée |
|---------------|------|----------|-----------------|
| Scout IQ2_XXS + MoE Offload | ~6GB | 10k tokens | 10-15 tok/s |
| Scout IQ2_XXS + MoE Offload | ~6GB | 16k tokens | 8-12 tok/s |
| Scout BitNet (si dispo) | ~4GB | 16k tokens | 15-20 tok/s |
| Mistral 7B Q4 (comparaison) | ~4GB | 16k tokens | 25-35 tok/s |

**Avantages de Llama 4 Scout pour le RPG:**

1. **Contexte 10M tokens natif** → Campagnes entières en mémoire
2. **17B paramètres actifs** → Qualité narrative supérieure
3. **Multimodal natif** → Peut analyser images (cartes, portraits)
4. **12 langues natives** → Français optimal
5. **MoE efficace** → 17B actifs sur109B = meilleure qualité/token

### 1.6 Périmètre

### 1.6 Périmètre

**Inclus:**
- Moteur de jeu solo (1 joueur + IA)
- Interface via SillyTavern / interface custom
- Système de règles configurable (D&D-like, custom)
- Gestion multi-joueurs (phase 2)
- API Python pour extensions
- Support natif Windows 11 (pas de WSL requis)

**Exclus:**
- Hébergement cloud (local uniquement)
- Modèles propriétaires (GGUF/open-source uniquement)
- Interface mobile native (web responsive uniquement)
- Support GPU AMD (ROCm non supporté sur laptop)

### 1.7 Spécificités Windows 11

**Sécurité basée sur la virtualisation (VBS):**

La configuration détectée a VBSactivé, ce qui implique:

| Impact | Mitigation |
|--------|------------|
| Performance Docker/WSL2 réduite (5-15%) | Utiliser Python natif plutôt que Docker |
| Isolation mémoire supplémentaire | Plus de sécurité, légèrement plus de RAM |
| Hyper-V détecté | Pas de conflit avec la configuration native |

**Recommandations Windows 11:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CONFIGURATION WINDOWS 11 RECOMMANDÉE                     │
│                                                                             │
│  INSTALLATION                                                               │
│  ├── Python 3.11+ natif (pas WSL)                                           │
│  ├── CUDA Toolkit 12.x (drivers RTX40xx)                                   │
│  ├── KoboldCPP CUDA (release Windows)                                      │
│  └── Pas de Docker requis                                                   │
│                                                                             │
│  OPTIMISATIONS                                                               │
│  ├── Désactiver Game Mode pendant les sessions longues                     │
│  ├── Mode "Haute performance" dans le panneau d'alimentation               │
│  ├── Fermer les applications en arrière-plan (browsers, etc.)              │
│  └── Surveiller les températures (AMD Ryzen peut throttler)                │
│                                                                             │
│  CHEMINS                                                                    │
│  ├── Modèles: C:\Users\<user>\models\                                       │
│  ├── Projet: C:\Users\<user>\Documents\Code\Perso\Project T\               │
│  └── Données: C:\Users\<user>\AppData\Local\rpg-engine\                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Chemins Windows spécifiques:**

| Unix | Windows |
|------|---------|
| `./lore/` | `%PROJECT_ROOT%\lore\` |
| `./data/saves/` | `%LOCALAPPDATA%\rpg-engine\saves\` |
| `./data/logs/` | `%LOCALAPPDATA%\rpg-engine\logs\` |
| `./modeles/` | `%USERPROFILE%\models\` |
| `~/.cache/` | `%LOCALAPPDATA%\cache\` |

---

## 2 · Architecture technique

### 2.1 Vue d'ensemble

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           COUCHE PRÉSENTATION                                │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐ │
│  │   SillyTavern   │  │  Interface Web   │  │      CLI (debug)            │ │
│  │   (frontend)    │  │   (phase 2)     │  │                             │ │
│  └────────┬────────┘  └────────┬────────┘  └──────────────┬──────────────┘ │
│           │                    │                          │                │
└───────────┼────────────────────┼──────────────────────────┼────────────────┘
            │                    │                          │
            ▼                    ▼                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           COUCHE API                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     API Gateway (FastAPI/Express)                   │   │
│  │  • Rate limiting • Auth (local) • Request validation • Routing      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           COUCHE MÉTIER                                     │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐ │
│  │  GameEngine     │  │  Lorebook       │  │      MemoryManager          │ │
│  │  ─────────────  │  │  ────────────    │  │      ──────────────         │ │
│  │  • State        │  │  • Entries      │  │  • Context management       │ │
│  │  • Dice rolls   │  │  • Triggers     │  │  • Summarization            │ │
│  │  • Validation   │  │  • Injection    │  │  • Retrieval (RAG)          │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────────┘ │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐ │
│  │  CharacterMgr   │  │  Inventory      │  │      QuestSystem           │ │
│  │  ─────────────  │  │  ────────────    │  │      ────────────          │ │
│  │  • Stats        │  │  • Items         │  │  • Quest states             │ │
│  │  • Classes      │  │  • Equipment     │  │  • Objectives              │ │
│  │  • Conditions   │  │  • Containers    │  │  • Rewards                 │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────────┘ │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        EventBus (interne)                            │   │
│  │  • Pub/Sub • Async events • Error propagation • State sync           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           COUCHE LLM                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                          LLMGateway                                  │   │
│  │  ─────────────────────────────────────────────────────────────────  │   │
│  │  • Connection management (KoboldCPP, LM Studio, Ollama)             │   │
│  │  • Prompt construction • Streaming • Retry logic • Token counting   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           COUCHE PERSISTANCE                                │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐ │
│  │  SQLite/JSON    │  │  FileStorage    │  │      VectorStore            │ │
│  │  ─────────────  │  │  ────────────    │  │      (RAG embeddings)       │ │
│  │  • Game state   │  │  • Lore files    │  │  • Semantic search         │ │
│  │  • Characters   │  │  • Logs (JSONL)  │  │  • Similarity matching     │ │
│  │  • Sessions     │  │  • Config        │  │                             │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Stack technologique définitive

| Composant | Technologie | Justification |
|-----------|-------------|---------------|
| **Backend** | Python 3.11+ | Écosystème ML mature, typage statique |
| **API** | FastAPI | Async, validation Pydantic, OpenAPI auto |
| **Frontend** | SillyTavern (existant) + Custom (phase 2) | Évite de réinventer, puis customisation |
| **Base de données** | SQLite + JSON files | Simplicité, pas de serveur requis |
| **Vector Store** | ChromaDB (local) | RAG local, pas de cloud |
| **LLM Runtime** | KoboldCPP (recommandé) / LM Studio (alternative) | SmartCache, KV quantization |
| **Embeddings** | sentence-transformers (local) | RAG vectoriel local |
| **Tests** | pytest + hypothesis | Tests unitaires + property-based |
| **Lint/Format** | ruff + mypy | Rapide, type checking strict |
| **Logging** | structlog | JSON structuré, corrélation IDs |

### 2.3 Structure des dossiers

```
mon-rpg-ia/
├── src/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── engine.py              # GameEngine principal
│   │   ├── events.py              # EventBus et événements
│   │   └── exceptions.py          # Exceptions custom
│   │
│   ├── lore/
│   │   ├── __init__.py
│   │   ├── book.py               # Lorebook manager
│   │   ├── entry.py              # Structure d'entrée lore
│   ├── trigger.py              # Logique de déclenchement
│   │   └── injection.py           # Injection contexte
│   │
│   ├── character/
│   │   ├── __init__.py
│   │   ├── manager.py            # Gestion personnages
│   │   ├── stats.py               # Calculs de stats
│   │   ├── class_.py              # Définition classes
│   │   └── condition.py          # États (poison, etc.)
│   │
│   ├── inventory/
│   │   ├── __init__.py
│   │   ├── manager.py            # Gestion inventaire
│   │   ├── item.py               # Structure item
│   │   └── equipment.py          # Emplacements équipement
│   │
│   ├── quest/
│   │   ├── __init__.py
│   │   ├── manager.py            # Gestion quêtes
│   │   ├── objective.py          # Objectifs
│   │   └── reward.py              # Récompenses
│   │
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── context.py            # Gestion fenêtre contexte
│   │   ├── summary.py            # Résumé automatique
│   │   ├── retrieval.py          # RAG retrieval
│   │   └── embeddings.py        # Génération embeddings
│   │
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── gateway.py            # Interface LLM unifiée
│   ├── prompt.py               # Construction prompts
│   │   ├── streaming.py          # Gestion streaming
│   │   └── tokens.py              # Comptage tokens
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py               # Point entrée FastAPI
│   │   ├── routes/
│   │   │   ├── game.py
│   │   │   ├── character.py
│   │   │   ├── lore.py
│   │   │   └── llm.py
│   │   ├── schemas/
│   │   │   ├── requests.py
│   │   │   └── responses.py
│   │   └── middleware/
│   │       ├── error_handler.py
│   │       └── request_logger.py
│   │
│   └── persistence/
│       ├── __init__.py
│       ├── database.py           # SQLite operations
│       ├── files.py               # JSON/JSONL handling
│       └── migrations/            # Schema migrations
│
├── lore/
│   ├── monde/
│   │   └── monde_principal.json
│   ├── personnages/
│   │   └── *.json
│   ├── lieux/
│   │   └── *.json
│   ├── objets/
│   │   └── *.json
│   └── regles/
│       ├── systeme_base.json
│       └── classes.json
│
├── data/
│   ├── sessions/                  # Sessions sauvegardées
│   ├── saves/                     # Sauvegardes joueur
│   ├── logs/                       # Logs applicatifs
│   └── cache/                     # Cache embeddings
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   └── fixtures/
│
├── config/
│   ├── default.yaml
│   ├── logging.yaml
│   └── llm/
│       ├── koboldcpp.yaml
│       └── lmstudio.yaml
│
├── scripts/
│   ├── init_db.py
│   ├── validate_lore.py
│   └── benchmark_context.py
│
├── docs/
│   ├── architecture.md
│   ├── api.md
│   ├── lorebook.md
│   └── contributing.md
│
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── ruff.toml
├── mypy.ini
└── README.md
```

---

## 3 · Modèle de données

### 3.1 Schéma JSON principal

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "definitions": {
    "Identifier": {
      "type": "string",
      "pattern": "^[a-z0-9_]+$",
      "description": "Identifiant unique snake_case"
    },
    "LocalizedString": {
      "type": "object",
      "additionalProperties": { "type": "string" },
      "required": ["fr", "en"],
      "description": "Support multilingue"
    },
    "DiceNotation": {
      "type": "string",
      "pattern": "^(\\d+)?d(100|20|12|10|8|6|4)([+-]\\d+)?$",
      "examples": ["d20", "2d6", "1d8+3", "4d6-1"]
    }
  }
}
```

### 3.2 Entité Character

```typescript
// Schéma TypeScript pour référence (implémentation Python)
interface Character {
  id: string;                    // Unique ID
  name: string;
  player_id: string | null;      // null = NPC
  
  class: CharacterClass;
  level: number;
  experience: number;
  
  stats: {
    hp: StatPool;
    mana: StatPool;
    stamina: StatPool;
    attributes: Attributes;
  };
  
  inventory: Inventory;
  equipment: EquipmentSlots;
  
  conditions: Condition[];       // États actifs
  skills: Skill[];
  quests: QuestProgress[];
  
  location: LocationRef;
  relationships: Relationship[];
  
  metadata: CharacterMetadata;
}

interface StatPool {
  current: number;
  max: number;
  temporary_bonus: number;
  temporary_max_increase: number;
}

interface Attributes {
  strength: number;
  dexterity: number;
  constitution: number;
  intelligence: number;
  wisdom: number;
  charisma: number;
}

interface Character {
  id: string;
  name: string;
  player_id: string | null;
  class: CharacterClass;
  level: number;
  experience: number;
  stats: {
    hp: StatPool;
    mana: StatPool;
    stamina: StatPool;
    attributes: Attributes;
  };
  inventory: Inventory;
  equipment: EquipmentSlots;
  conditions: Condition[];
  skills: Skill[];
  quests: QuestProgress[];
  location: LocationRef;
  relationships: Relationship[];
  metadata: CharacterMetadata;
}
```

**Règles métier Character:**
- `hp.current` ne peut pas dépasser `hp.max + hp.temporary_max_increase`
- `hp.current` minimum =0 (jamais négatif)
- Suppression logique: `metadata.is_deleted = true`
- Immutable: `id`, `created_at`
- Mutable: tout le reste avec validation

### 3.3 Entité Item

```typescript
interface Item {
  id: string;
  template_id: string;           // Référence au template d'objet
  name: LocalizedString;
  description: LocalizedString;
  
  type: ItemType;
  subtype: ItemSubtype | null;
  rarity: Rarity;
  
  stackable: boolean;
  max_stack: number;
  quantity: number;               // Dans le stack actuel
  
  weight: number;
  value: number;                  // En pièces d'or
  
  stats: ItemStats | null;
  effects: ItemEffect[] ;
  
  requirements: Requirements | null;
  metadata: ItemMetadata;
}

type ItemType = 
  | "weapon" | "armor" | "accessory"
  | "consumable" | "quest_item"
  | "material" | "misc";

type Rarity = 
  | "common" | "uncommon" | "rare" 
  | "epic" | "legendary" | "artifact";
```

### 3.4 Entité LorebookEntry

```typescript
interface LorebookEntry {
  id: string;
  name: string;
  category: LorebookCategory;
  
  keys: string[];                 // Mots-clés déclencheurs
  secondary_keys: string[];       // Déclencheurs secondaires
  regex_keys: string[];           // Patterns regex
  
  content: string;                // Texte à injecter
  extensions: LoreExtension[];    // Métadonnées structurées
  
  priority: number;                // 0-1000, plus haut = plus important
  order: number;                  // Ordre d'injection
  position: InjectionPosition;
  
  trigger_chance: number;         // 0-100, probabilité de déclenchement
  conditions: Condition[];        // Conditions métier
  
  use_probability: boolean;
  scan_depth: number;             // Nombre de messages à scanner
  case_sensitive: boolean;
  
  metadata: EntryMetadata;
}
type InjectionPosition = 
  | "after_system" | "after_scenario"
  | "before_example" | "after_example";
```

### 3.5 Entité Quest

```typescript
interface Quest {
  id: string;
  name: LocalizedString;
  description: LocalizedString;
  
  type: QuestType;
  chapter: string | null;
  
  objectives: Objective[];
  rewards: Reward[];
  
  prerequisites: QuestPrerequisite[];
  unlocks: string[];              // IDs de quêtes débloquées
  
  time_limit: number | null;       // En tours, null = illimité
  repeatable: boolean;
  
  metadata: QuestMetadata;
}

interface Objective {
  id: string;
  description: LocalizedString;
  type: ObjectiveType;
  target: string;                  // Ce qu'il faut atteindre/tuer/ramasser
  count: number;                  // Quantité requise
  optional: boolean;
  hidden: boolean;                // Objectif secret
}
```

### 3.6 Structure de session

```typescript
interface Session {
  id: string;
  name: string;
  created_at: string;              // ISO8601
  updated_at: string;
  
  players: PlayerSession[];
  active_character: string;       // ID du personnage actif
  
  world_id: string;
  lorebook_ids: string[];
  
  history: HistoryEntry[];
  summary: SessionSummary | null;
  
  state: GameState;
  settings: SessionSettings;
  
  metadata: SessionMetadata;
}

interface HistoryEntry {
  id: string;
  timestamp: string;
  type: "user" | "assistant" | "system" | "roll" | "action";
  
  content: string;
  metadata: HistoryMetadata;
}

interface SessionSummary {
  last_summarized_at: string;
  message_count_since: number;
  summary_text: string;
  key_facts: string[];
}
```

---

## 4 · Gestion d'état

### 4.1 Principe de state immuable

L'état du jeu est **immutabledans le sens suivant:**
- Chaque modification crée une nouvelle version de l'état
- L'historique des états est préservé (audit trail)
- Rollback possible à n'importe quel point

```python
# Exemple conceptuel
class GameStateManager:
    def __init__(self):
        self._states: deque[GameState] = deque(maxlen=100)
        self._current_index: int = 0
    
    def apply_action(self, action: Action) -> GameState:
        new_state = self.current_state.apply(action)
        self._states.append(new_state)
        self._current_index = len(self._states) - 1
        return new_state
    
    def rollback(self, steps: int) -> GameState:
        self._current_index = max(0, self._current_index - steps)
        return self._states[self._current_index]
```

### 4.2 Sources de vérité

| Donnée | Source de vérité | Synchronisation |
|--------|------------------|-----------------|
| Stats personnage | Base de données | Immédiate |
| Inventaire | Base de données | Immédiate |
| Position | Base de données | Immédiate |
| Contexte LLM | Mémoire + injection | Par message |
| Historique | Fichiers JSONL | Par message |
| Lore | Fichiers JSON | Au démarrage |

### 4.3 Validation de l'état

**Règles invariantes:**
```python
INVARIANTS = [
    "HP >= 0",
    "HP <= max_hp",
    "inventaire_weight <= carry_capacity",
    "level >= 1",
    "experience >= 0",
    "location in valid_locations",
]
```

**Validation avantchaque sauvegarde:**
```python
def validate_state(state: GameState) -> ValidationResult:
    errors = []
    for invariant in INVARIANTS:
        if not invariant.check(state):
            errors.append(InvariantViolation(invariant, state))
    return ValidationResult(errors)
```

### 4.4 Gestion des conflits (multi-joueur)

```python
class ConflictResolution:
    STRATEGIES = {
        "last_write_wins": LastWriteWinsStrategy,
        "merge": MergeStrategy,
        "reject": RejectConflictStrategy,
    }
    
    def resolve(self, local: GameState, remote: GameState) -> GameState:
        # Pour phase 1 (solo): last_write_wins
        # Pour phase 2 (multi): merge avec timestamps
        pass
```

---

## 5 · Système Lorebook

### 5.1 Pipeline d'injection

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PIPELINE D'INJECTION                                │
│                                                                             │
│  1. TRIGGER DETECTION                                                       │
│     ├── Scan du message utilisateur                                        │
│     ├── Recherche de mots-clés (exact + fuzzy)                             │
│     ├── Évaluation des regex                                               │
│     └── Filtrage par conditions (état du jeu)                              │
│                                                                             │
│  2. ENTRY SELECTION                                                         │
│     ├── Application des probabilités (trigger_chance)                      │
│     ├── Déduplication (une entrée par ID)                                  │
│     └── Calcul de la priorité effective                                    │
│                                                                             │
│  3. CONTENT PREPARATION                                                     │
│     ├── Résolution des variables ({{player_name}}, etc.)                   │
│     ├── Interpolation des stats dynamiques                                 │
│     └── Génération du texte final                                          │
│                                                                             │
│  4. ORDERING & INJECTION                                                    │
│     ├── Tri par priorité (desc) puis ordre (asc)                            │
│     ├── Calcul du budget de tokens                                          │
│     ├── Troncature si nécessaire (respect priorité)                        │
│     └── Injection à la position définie                                    │
│                                                                             │
│  5. CONTEXT ASSEMBLY                                                        │
│     └── Assemblage final: system + lore + history + user prompt           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Algorithmes de déclenchement

**Recherche exacte:**
```python
def match_exact(text: str, keys: list[str], case_sensitive: bool = False) -> bool:
    search_text = text if case_sensitive else text.lower()
    for key in keys:
        search_key = key if case_sensitive else key.lower()
        if search_key in search_text:
            return True
    return False
```

**Recherche fuzzy (tolérance typos):**
```python
def match_fuzzy(text: str, keys: list[str], threshold: float = 0.85) -> bool:
    for key in keys:
        ratio = levenshtein_ratio(text.lower(), key.lower())
        if ratio >= threshold:
            return True
    return False
```

**Recherche sémantique (RAG):**
```python
def match_semantic(
    text: str, 
    query_embedding: np.ndarray,
    lore_embeddings: dict[str, np.ndarray],
    threshold: float = 0.75
) -> list[str]:
    text_embedding = embed(text)
    scores = {
        entry_id: cosine_similarity(text_embedding, lore_emb)
        for entry_id, lore_emb in lore_embeddings.items()
    }
    return [eid for eid, score in scores.items() if score >= threshold]
```

### 5.3 Gestion du budget de tokens

```python
class TokenBudget:
    MAX_CONTEXT: int = 8192  # Selon modèle
    
    RESERVE: int = 512        # Pour réponse
    SYSTEM_PROMPT: int = 200 # Prompt système fixe
    
    def calculate_available(self) -> int:
        return self.MAX_CONTEXT - self.RESERVE - self.SYSTEM_PROMPT
    
    def allocate(self, entries: list[LoreEntry]) -> list[LoreEntry]:
        budget = self.calculate_available()
        allocated = []
        
        # Trier par priorité décroissante
        sorted_entries = sorted(entries, key=lambda e: e.priority, reverse=True)
        
        for entry in sorted_entries:
            entry_tokens = count_tokens(entry.content)
            if entry_tokens <= budget:
                allocated.append(entry)
                budget -= entry_tokens
            elif entry.truncatable and entry.min_tokens:
                # Tronquer mais garder minimum
                if entry.min_tokens <= budget:
                    allocated.append(entry.truncate(budget))
                    budget = 0
                    break
        
        return allocated
```

### 5.4 Catégories de lore

| Catégorie | Priorité | Scan Depth | Trigger Chance |
|-----------|----------|------------|----------------|
| Constant |1000 | 0 | 100% |
| Character Active | 900 | 10 | 100% |
| Quest State | 800 | 5 | 100% |
| Location Active | 700 | 15 | 100% |
| NPC Present | 600 | 20 | 100% |
| Conditional | 400 | 30 | Variable |
| Ambient | 200 | 50 | Variable |
| Secret/Hidden | Variable | Variable | Variable |

---

## 6 · Mécaniques de jeu

### 6.1 Système de jets de dés

**Types de dés supportés:**
```python
DICE_TYPES = {
    "d4": 4,
    "d6": 6,
    "d8": 8,
    "d10": 10,
    "d12": 12,
    "d20": 20,
    "d100": 100,
}
```

**Structure d'un jet:**
```typescript
interface DiceRoll {
  id: string;
  notation: string;          // ex: "2d6+3"
  dice: DiceComponent[];
  modifier: number;
  total: number;
  
  context: RollContext;
  result: RollResult;
  
  metadata: RollMetadata;
}

interface DiceComponent {
  type: string;               // "d20"
  count: number;             // 1 pour "d20", 2 pour "2d6"
  rolls: number[];           // [15] ou [3, 4]
  dropped: number[];         // Pour "4d6 drop lowest"
}
```

**Déterminisme vs aléatoire:**
```python
class RandomSource(Protocol):
    def roll(self, sides: int) -> int: ...

class SeededRandom(RandomSource):
    def __init__(self, seed: int):
        self._rng = random.Random(seed)
    
    def roll(self, sides: int) -> int:
        return self._rng.randint(1, sides)

class LLMRandom(RandomSource):
    """Pour les jets où le LLM décide du résultat"""
    def __init__(self, llm: LLMGateway):
        self._llm = llm
    
    def roll(self, sides: int) -> int:
        # Le LLM génère un résultat "narrativement cohérent"
        pass
```

**Validation des jets:**
- Un jet ne peut pas être modifié après création
- Le hashCode du jet doit être vérifiable
- Stockage immuable dans l'historique

### 6.2 Système de combat

**Structure d'un combat:**
```typescript
interface CombatState {
  id: string;
  participants: Combatant[];
  turn_order: string[];        // IDs dans l'ordre
  current_turn: number;
  round: number;
  
  terrain: TerrainModifiers | null;
  status: CombatStatus;
  
  log: CombatLogEntry[];
}

interface Combatant {
  character_id: string;
  initiative: number;
  actions_per_turn: number;
  actions_remaining: number;
  conditions: CombatCondition[];
  
  position: Position2D | null;  // Pour combat tactique
}
```

**Pipeline d'action de combat:**
```
Action déclarée → Validation → Jets de dés →Application effets →Narration
     ↓                ↓              ↓                ↓                ↓
 "J'attaque"    Stats OK?    Roll d20+str   Damage calculation   LLM génère
                               vs AC
```

### 6.3 Système d'inventaire

**Contraintes:**
```python
class InventoryConstraints:
    MAX_SLOTS: int = 100
    MAX_WEIGHT: float = 100.0# En kg
    
    def can_add(self, inventory: Inventory, item: Item) -> bool:
        if not item.stackable and inventory.count_item(item.id) > 0:
            return False  # Pas de double stack pour non-stackable
        
        new_weight = inventory.total_weight + item.weight * item.quantity
        if new_weight > self.MAX_WEIGHT:
            return False
        
        if len(inventory.items) >= self.MAX_SLOTS:
            # Vérifier si on peut stacker
            if item.stackable and inventory.count_item(item.id) > 0:
                return True
            return False
        
        return True
```

**Opérations:**
- `add(item)` → Ajoute un item
- `remove(item_id, quantity)` → Retire des items
- `transfer(item_id, quantity, target_inventory)` → Transfert entre inventaires
- `equip(item_id, slot)` → Équipe un item
- `unequip(slot)` → Déséquipe

### 6.4 Système de conditions

```typescript
interface Condition {
  id: string;
  name: LocalizedString;
  type: ConditionType;
  
  duration: Duration;           // permanent, rounds, time
  remaining: number | null;
  
  effects: ConditionEffect[];
  stacks: boolean;
  current_stacks: number;
  max_stacks: number;
  
  source: string | null;        // ID de la source
  dispellable: boolean;
}

type ConditionType = 
  | "buff" | "debuff" 
  | "poison" | "disease" 
  | "curse" | "blessing";
```

---

## 7 · Intégration LLM

### 7.1 Interface unifiée

```python
from abc import ABC, abstractmethod
from typing import AsyncIterator

class LLMProvider(ABC):
    @abstractmethod
    async def generate(
        self, 
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        stop_sequences: list[str] | None = None,
    ) -> str: ...
    
    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        stop_sequences: list[str] | None = None,
    ) -> AsyncIterator[str]: ...
    
    @abstractmethod
    def count_tokens(self, text: str) -> int: ...
    
    @abstractmethod
    async def is_healthy(self) -> bool: ...
```

### 7.2 Providers supportés

| Provider | Classe | Configuration |
|----------|--------|---------------|
| KoboldCPP | `KoboldCPPProvider` | `{"url": "http://localhost:5001"}` |
| LM Studio | `LMStudioProvider` | `{"url": "http://localhost:1234"}` |
| Ollama | `OllamaProvider` | `{"url": "http://localhost:11434"}` |
| OpenAI (fallback) | `OpenAIProvider` | `{"api_key": "..."}` |

### 7.2.1 Modèles recommandés (RTX 4050 6GB)

**Modèle principal: Llama 4 Scout (MoE Offloading)**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│              LLAMA 4 SCOUT — CONFIGURATION OPTIMALE RTX 4050                │
│                                                                             │
│  SPÉCIFICATIONS                                                             │
│  ├── Paramètres totaux: 109B                                                │
│  ├── Paramètres actifs: 17B par token                                       │
│  ├── Experts: 16 (MoE)                                                      │
│  ├── Contexte natif: 10M tokens                                            │
│  └── Multimodal: Texte + Image                                              │
│                                                                             │
│  QUANTIZATION RECOMMANDÉE                                                   │
│  ├── IQ2_XXS (2.4-bit) — Taille: ~6GB                                     │
│  ├── Q3_K_M (3-bit) — Taille: ~7GB (alternative)                           │
│  └── BitNet b1.58 — Taille: ~3-4GB (si disponible)                         │
│                                                                             │
│  CONFIGURATION KoboldCPP/LM Studio                                          │
│  ├── --n-gpu-layers: 32 (attention sur GPU)                                │
│  ├── --n-cpu-moe: 16 (experts en RAM)                                      │
│  ├── --flash-attn: activé                                                  │
│  ├── --ctk q4_1: KV Cache 4-bit                                            │
│  └── --ctx-size: 16384 (max avec KV Q4)                                    │
│                                                                             │
│  PERFORMANCE ESTIMÉE                                                        │
│  ├── Vitesse: 10-15 tokens/sec                                             │
│  ├── Latence premier token: 3-5 secondes                                   │
│  └── Contexte max: 16k tokens (configurable)                               │
│                                                                             │
│  POURQUOI SCOUT POUR LE RPG?                                                │
│  ├── ✅ Contexte 10M tokens = campagnes entières                           │
│  ├── ✅ 17B actifs = qualité narrative supérieure                          │
│  ├── ✅ Multimodal = analyse de cartes/portraits                          │
│  ├── ✅ 12 langues natives = français optimal                              │
│  └── ✅ MoE = efficacité (17B actifs sur 109B)                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Classification par cas d'usage:**

| Usage | Modèle | Quantization | VRAM | RAM | Vitesse |
|-------|--------|--------------|------|-----|---------|
| **Principal (RPG)** | **Llama 4 Scout** | IQ2_XXS | ~6GB | ~10GB | 10-15 tok/s |
| Rapide (assist.) | Llama 3.2 3B | Q5_K_M | ~2.5GB | - | 40-50 tok/s |
| Fallback | Mistral 7B v0.3 | Q4_K_M | ~4GB | - | 25-35 tok/s |
| Résumé | Phi-3 Mini 3.8B | Q5_K_M | ~2.5GB | - | 35-45 tok/s |

**Détails Llama 4 Scout:**

```
Modèle: meta-llama/Llama-4-Scout-17B-16E-Instruct
Architecture: Mixture-of-Experts (MoE)
Taille IQ2_XXS: ~6GB
Taille Q3_K_M: ~7GB
Taille Q4_K_M: ~9GB (non recommandé pour 6GB VRAM)

Configuration GPU Layers:
- Attention: 32couches sur GPU
- Experts: 16 experts sur CPU/RAM (n-cpu-moe)

Activation par token:
- Seuls 1-2 experts actifs sur 16
- => 17B paramètres traités par token (pas 109B)
- => Rapidité proche d'un 7-8B classique
```

**Commande KoboldCPP recommandée:**

```powershell
koboldcpp.exe ^
    --model Llama-4-Scout-17B-16E-Instruct-IQ2_XXS.gguf ^
    --n-gpu-layers 32 ^
    --n-cpu-moe 16 ^
    --flash-attn ^
    --ctk q4_1 ^
    --ctx-size 16384 ^
    --smartcontext ^
    --threads 14 ^
    --port 5001

# OPTIONS AVANCÉES
# --use-cublas        : Accélération CUDA (requis)
# --n-cpu-moe N       : Nombre d'experts en CPU
# --split-mode layer  : Distribution GPU/CPU par couche
```

**Calcul de contexte (RTX 4050 + Llama 4 Scout IQ2_XXS):**

```
VRAM totale: 6144 MB
├── Modèle IQ2_XXS (~6GB): 5500 MB
├── Réserve système: 500 MB
└── Disponible pour contexte: ~144 MB

Sans KV Cache compression: ~300 tokens max
Avec KV Cache Q4: ~12,000-16,000 tokens
Avec KV Cache Q8: ~6,000-8,000 tokens

RECOMMANDATION: KV Cache Q4 pour contexte 10k-16k tokens
```

**Alternative: Llama 4 Maverick**

```
AVERTISSEMENT: Maverick (402B total) n'est PAS recommandé pour 6GB VRAM
- Nécessite minimum RTX 4090 (24GB) en Q4
- En IQ2_XXS: ~20GB, nécessiterait offloading massif
- Performance estimée: <5 tok/s avec offloading complet
- Réservé pour hardware futur ou serveur cloud
```

**Configuration GPU Layers (détail):**

```python
# Pour RTX 4050 (6GB) avec Llama 4 Scout
GPU_LAYERS_CONFIG = {
    "attention_layers": 32,      # Sur GPU
    "layer_norm": 32,            # Sur GPU
    "position_embed": 1,         # Sur GPU
    
    "moe_experts": 0,           # Sur CPU/RAM (n-cpu-moe)
    "moe_router": 1,             # Sur GPU
    
    "total_gpu_layers": 35,     # Approximation
    "expert_offload": True,     # Activer n-cpu-moe
}

# Si OOM (Out of Memory):
# 1. Réduire n-gpu-layers à 28
# 2. Réduire ctx-size à 8192
# 3. Passer de IQ2_XXS à IQ1_S (plus agressif)
```

### 7.3 Construction du prompt

```python
class PromptBuilder:
    def build(
        self,
        system_prompt: str,
        lore_entries: list[LoreEntry],
        conversation_history: list[Message],
        current_input: str,
        character_state: CharacterState,
    ) -> str:
        sections = []
        
        # 1. System prompt (toujours en premier)
        sections.append(f"<system>\n{system_prompt}\n</system>")
        
        # 2. État du personnage (priorité 800+)
        state_text = self._format_character_state(character_state)
        sections.append(f"<character>\n{state_text}\n</character>")
        
        # 3. Lore injecté (trié par priorité)
        lore_text = self._format_lore(lore_entries)
        sections.append(f"<lore>\n{lore_text}\n</lore>")
        
        # 4. Historique compressé si nécessaire
        history_text = self._format_history(conversation_history)
        sections.append(f"<history>\n{history_text}\n</history>")
        
        # 5. Input utilisateur
        sections.append(f"<user>\n{current_input}\n</user>")
        
        return "\n\n".join(sections)
```

### 7.4 Parsing de la réponse

Le LLMpeut retourner du texte narratif + des métadonnées structurées:

```python
class ResponseParser:
    def parse(self, raw_response: str) -> ParsedResponse:
        narrative = ""
        actions = []
        
        # Pattern: [ACTION:damage:player:15]
        action_pattern = r'\[ACTION:(\w+):(\w+):(\d+)\]'
        
        for match in re.finditer(action_pattern, raw_response):
            action_type, target, value = match.groups()
            actions.append(Action(
                type=action_type,
                target=target,
                value=int(value)
            ))
        
        # Retirer les tags d'action du texte narratif
        narrative = re.sub(action_pattern, '', raw_response).strip()
        
        return ParsedResponse(
            narrative=narrative,
            actions=actions,
            raw=raw_response
        )
```

### 7.5 Retry et gestion d'erreurs

```python
class ResilientLLMGateway:
    MAX_RETRIES: int = 3
    RETRY_DELAYS: list[float] = [1.0, 2.0, 5.0]
    
    async def generate(self, prompt: str, **kwargs) -> str:
        last_error: Exception | None = None
        
        for attempt in range(self.MAX_RETRIES):
            try:
                if not await self.provider.is_healthy():
                    raise LLMUnhealthyError()
                
                return await self.provider.generate(prompt, **kwargs)
            
            except (ConnectionError, TimeoutError) as e:
                last_error = e
                await asyncio.sleep(self.RETRY_DELAYS[attempt])
            
            except LLMContentFilterError:
                # Ne pas retry sur filtre contenu
                raise
        
        raise LLMGenerationError(f"Failed after {self.MAX_RETRIES} retries") from last_error
```

---

## 8 · Mémoire et contexte

### 8.1 Stratégie de compression

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FENÊTRE DE CONTEXTE                                 │
│                                                                             │
│  [SYSTEM PROMPT - Fixe ~500 tokens]                                        │
│  │                                                                          │
│  [LORE ACTIF - Variable ~1000-3000 tokens]                                │
│  │  ├── Règles constantes                                                  │
│  │  ├── État personnage                                                     │
│  │  ├── PNJ présents                                                       │
│  │  └── Lieu actuel                                                        │
│  │                                                                          │
│  [HISTORIQUE RÉCENT - Variable ~2000-4000 tokens]                        │
│  │  ├── Derniers N messages complets                                       │
│  │  └── Jets de dés récents                                                │
│  │                                                                          │
│  [RÉSUMÉ - Variable ~500-1000 tokens]                                     │
│  │  ├── Résumé des sessions précédentes                                    │
│  │  └── Faits importants extraits                                          │
│  │                                                                          │
│  [RÉSERVE POUR RÉPONSE - ~512-1024 tokens]                                 │
│                                                                             │
│  ════════════════════════════════════════════════════════════════════════  │
│  TOTAL: ≤ MAX_CONTEXT_TOKENS                                                │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Algorithme de résumé

```python
class Summarizer:
    SUMMARY_THRESHOLD: int = 50# Messages avant résumé
    SUMMARY_EVERY: int = 30# Fréquence des résumés
    
    def should_summarize(self, history: list[Message]) -> bool:
        return len(history) >= self.SUMMARY_THRESHOLD and \
               len(history) % self.SUMMARY_EVERY == 0
    
    async def summarize(
        self, 
        messages: list[Message],
        previous_summary: str | None = None
    ) -> Summary:
        # Utiliser un modèle léger pour le résumé
        prompt = self._build_summary_prompt(messages, previous_summary)
        
        summary_text = await self.llm.generate(
            prompt,
            max_tokens=500,
            temperature=0.3# Plus déterministe
        )
        
        key_facts = await self._extract_key_facts(summary_text)
        
        return Summary(
            text=summary_text,
            key_facts=key_facts,
            message_range=(messages[0].id, messages[-1].id)
        )
```

### 8.3 Extraction de faits

**Types de faitsextraits:**
```typescript
interface KeyFact {
  id: string;
  type: FactType;
  content: string;
  confidence: number;
  source_message_id: string;
  extracted_at: string;
}

type FactType = 
  | "character_relation"  // "Jean est le frère de Marie"
  | "location_visited"    // "Le joueur a visité la taverne"
  | "item_acquired"       // "Le joueur possède l'épée Excalibur"
  | "quest_progress"      // "Quête 'Le Dragon' en cours"
  | "death"               // "Le PNJ 'Garde' est mort"
  | "state_change";       // "Le pont est détruit"
```

### 8.4 RAG pour la recherche lore

```python
class LoreRetriever:
    def __init__(self, embedding_model: str = "all-MiniLM-L6-v2"):
        self.embedder = SentenceTransformer(embedding_model)
        self.index = chromadb.Client()
        self.collection = self.index.get_or_create_collection("lore")
    
    async def index_lore(self, entries: list[LoreEntry]):
        for entry in entries:
            embedding = self.embedder.encode(entry.content)
            self.collection.add(
                ids=[entry.id],
                embeddings=[embedding.tolist()],
                metadatas=[{"priority": entry.priority, "category": entry.category}]
            )
    
    async def search(
        self, 
        query: str, 
        n_results: int = 10,
        where_filter: dict | None = None
    ) -> list[str]:
        query_embedding = self.embedder.encode(query)
        
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=n_results,
            where=where_filter
        )
        
        return results["ids"][0]
```

---

## 9 · Gestion des erreurs

### 9.1 Hiérarchie d'exceptions

```python
class RPGENgineError(Exception):
    """Base exception for all engine errors"""
    pass

class ValidationError(RPGENgineError):
    """Data validation failed"""
    pass

class StateError(RPGENgineError):
    """Invalid game state operation"""
    pass

class LLMError(RPGENgineError):
    """LLM-related errors"""
    pass

class LLMConnectionError(LLMError):
    """Cannot connect to LLM backend"""
    pass

class LLMGenerationError(LLMError):
    """LLM generation failed"""
    pass

class LLMContentFilterError(LLMError):
    """Content blocked by LLM filter"""
    pass

class LoreError(RPGENgineError):
    """Lorebook-related errors"""
    pass

class LoreInjectionError(LoreError):
    """Failed to inject lore"""
    pass

class LoreCycleError(LoreError):
    """Circular dependency in lore entries"""
    pass

class InventoryError(RPGENgineError):
    """Inventory operation failed"""
    pass

class InsufficientSpaceError(InventoryError):
    """Not enough space in inventory"""
    pass
```

### 9.2 Stratégies de récupération

| Erreur | Stratégie | Action |
|--------|-----------|--------|
| `LLMConnectionError` | Retry avec backoff | 3 tentatives, délai exponentiel |
| `LLMGenerationError` | Fallback | Prompt simplifié, puis message d'erreur |
| `ValidationError` | Refus | Message utilisateur explicite |
| `StateError` | Rollback | Retour à l'état précédent valide |
| `LoreInjectionError` | Graceful degradation | Continuer sans cette entrée lore |
| `InsufficientSpaceError` | Refus | Message avec suggestion |

### 9.3 Logging structuré

```python
import structlog

logger = structlog.get_logger()

# Exemple de log structuré
logger.info(
    "action_performed",
    action_type="attack",
    actor_id="char_001",
    target_id="enemy_002",
    roll_result=17,
    damage=12,
    session_id="sess_abc123"
)
```

---

## 10 · Sécurité

### 10.1 Menaces identifiées

| Menace | Impact | Mitigation |
|--------|--------|------------|
| Injection de prompts LLM | Haute | Sanitization, validation stricte |
| Corrompre les fichiers de sauvegarde | Moyenne | Validation JSON, backup auto |
| Accès non autorisé aux données | Basse | Local uniquement, pas de réseau |
| Injection de code via lore | Moyenne | Pas d'exécution dynamique |
| Épuisement des ressources LLM | Moyenne | Rate limiting, queue |

### 10.2 Sanitization des entrées

```python
class InputSanitizer:
    MAX_INPUT_LENGTH: int = 10000
    FORBIDDEN_PATTERNS: list[str] = [
        r'<system>',
        r'\[ACTION:',
        r'{{.*}}',# Empêcher l'injection de variables
    ]
    
    def sanitize(self, text: str) -> str:
        if len(text) > self.MAX_INPUT_LENGTH:
            raise ValidationError(f"Input exceeds {self.MAX_INPUT_LENGTH} characters")
        
        for pattern in self.FORBIDDEN_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                raise ValidationError(f"Forbidden pattern detected: {pattern}")
        
        return text.strip()
```

### 10.3 Isolation des sauvegardes

```python
class SaveManager:
    def save(self, session: Session) -> str:
        # Générer un nom de fichier sûr
        safe_id = re.sub(r'[^a-zA-Z0-9_-]', '', session.id)
        filename = f"{safe_id}_{datetime.now().isoformat()}.json"
        
        # Valider le contenu avant sauvegarde
        validation = validate_session(session)
        if not validation.is_valid:
            raise ValidationError(validation.errors)
        
        # Écriture atomique
        temp_path = self.save_dir / f".tmp_{filename}"
        final_path = self.save_dir / filename
        
        with open(temp_path, 'w') as f:
            json.dump(session.to_dict(), f)
        
        temp_path.rename(final_path)
        return str(final_path)
```

---

## 11 · Performance

### 11.1 Objectifs de performance

| Métrique | Cible | Seuil critique |
|----------|-------|-----------------|
| Temps de réponse LLM | < 3s (premier token) | > 10s |
| Injection lore | < 100ms | > 500ms |
| Sauvegarde session | < 500ms | > 2s |
| Chargement session | < 2s | > 10s |
| Recherche RAG | < 200ms | > 1s |
| Calcul de stats | < 10ms | > 100ms |

### 11.2 Optimisation du contexte

```python
class ContextOptimizer:
    def __init__(self, max_tokens: int):
        self.max_tokens = max_tokens
        self.cache: dict[str, int] = {}# Cache de token count
    
    def count_tokens(self, text: str) -> int:
        if text not in self.cache:
            self.cache[text] = self._tokenize(text)
        return self.cache[text]
    
    def optimize(
        self, 
        entries: list[LoreEntry],
        reserve: int = 512
    ) -> list[LoreEntry]:
        budget = self.max_tokens - reserve
        
        # 1. Toujours inclure les entrées constantes
        constant = [e for e in entries if e.category == "constant"]
        remaining = [e for e in entries if e.category != "constant"]
        
        # 2. Calculer le budget restant
        used = sum(self.count_tokens(e.content) for e in constant)
        budget -= used
        
        # 3. Ajouter par priorité décroissante
        result = constant.copy()
        for entry in sorted(remaining, key=lambda e: e.priority, reverse=True):
            tokens = self.count_tokens(entry.content)
            if tokens <= budget:
                result.append(entry)
                budget -= tokens
        
        return result
```

### 11.3 Caching

```python
from functools import lru_cache
from cachetools import TTLCache

# Cache en mémoire pour les stats calculées
@lru_cache(maxsize=1024)
def calculate_stat_modifier(stat_value: int) -> int:
    return (stat_value - 10) // 2

# Cache TTL pour les embeddings RAG
embedding_cache = TTLCache(maxsize=1000, ttl=3600)  # 1 heure

def get_embedding(text: str) -> np.ndarray:
    cache_key = hash(text)
    if cache_key in embedding_cache:
        return embedding_cache[cache_key]
    
    embedding = model.encode(text)
    embedding_cache[cache_key] = embedding
    return embedding
```

### 11.4 Lazy loading

```python
class LazyLorebook:
    def __init__(self, lore_dir: Path):
        self.lore_dir = lore_dir
        self._cache: dict[str, LoreEntry] = {}
        self._loaded: bool = False
    
    def get_entry(self, entry_id: str) -> LoreEntry:
        if entry_id not in self._cache:
            self._load_entry(entry_id)
        return self._cache[entry_id]
    
    def _load_entry(self, entry_id: str):
        path = self.lore_dir / f"{entry_id}.json"
        with open(path) as f:
            self._cache[entry_id] = LoreEntry.from_json(f.read())
    
    def preload_category(self, category: str):
        # Précharger une catégorie complète
        for path in (self.lore_dir / category).glob("*.json"):
            entry_id = path.stem
            if entry_id not in self._cache:
                self._load_entry(entry_id)
```

---

## 12 · Tests

### 12.1 Stratégie de test

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PYRAMIDE DE TESTS                                   │
│                                                                             │
│                    ╔═══════════════════════════╗                           │
│                    ║    TESTS E2E (5%)        ║                           │
│                    ║  Scénarios complets      ║                           │
│                    ╚═══════════════════════════╝                           │
│                 ╔═══════════════════════════════════╗                      │
│                 ║     TESTS INTÉGRATION (15%)      ║                      │
│                 ║  Composants ensemble            ║                      │
│                 ╚═══════════════════════════════════╝                      │
│            ╔═════════════════════════════════════════════╗                │
│            ║          TESTS UNITAIRES (80%)             ║                │
│            ║  Fonctions isolées, logique pure          ║                │
│            ╚═════════════════════════════════════════════╝                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 12.2 Tests unitaires

```python
# tests/unit/test_dice.py

import pytest
from hypothesis import given, strategies as st

from src.core.dice import DiceRoller, DiceNotation

class TestDiceRoller:
    def test_simple_d20(self):
        roller = DiceRoller(seed=42)
        result = roller.roll("d20")
        assert 1 <= result.total <= 20
    
    def test_modifiers(self):
        roller = DiceRoller(seed=42)
        result = roller.roll("d20+5")
        assert result.modifier == 5
        assert 6 <= result.total <= 25
    
    @given(
        count=st.integers(min_value=1, max_value=10),
        sides=st.sampled_from([4, 6, 8, 10, 12, 20, 100]),
        modifier=st.integers(min_value=-10, max_value=10)
    )
    def test_valid_ranges(self, count: int, sides: int, modifier: int):
        roller = DiceRoller(seed=42)
        notation = f"{count}d{sides}{'+' if modifier >= 0 else ''}{modifier}"
        result = roller.roll(notation)
        
        min_roll = count * 1 + modifier
        max_roll = count * sides + modifier
        assert min_roll <= result.total <= max_roll
    
    def test_invalid_notation(self):
        roller = DiceRoller()
        with pytest.raises(ValidationError):
            roller.roll("d30")# Dés non supportés
    
    def test_deterministic_with_seed(self):
        roller1 = DiceRoller(seed=123)
        roller2 = DiceRoller(seed=123)
        
        for _ in range(10):
            assert roller1.roll("d20").total == roller2.roll("d20").total
```

### 12.3 Tests d'intégration

```python
# tests/integration/test_lore_injection.py

import pytest
from src.lore import Lorebook, LoreEntry
from src.memory import ContextManager

class TestLoreInjection:
    @pytest.fixture
    def lorebook(self):
        return Lorebook.from_directory("tests/fixtures/lore")
    
    @pytest.fixture
    def context_manager(self):
        return ContextManager(max_tokens=4096)
    
    def test_trigger_injection(self, lorebook, context_manager):
        message = "Je cherche des informations sur Excalibur."
        context = context_manager.build(
            lorebook=lorebook,
            user_message=message,
            history=[],
            character_state={}
        )
        
        assert "Excalibur" in context
        assert "épée légendaire" in context
    
    def test_priority_ordering(self, lorebook, context_manager):
        # Contexte trop petit pour tout contenir
        context_manager_small = ContextManager(max_tokens=100)
        
        message = "Je suis dans la taverne."
        context = context_manager_small.build(
            lorebook=lorebook,
            user_message=message,
            history=[],
            character_state={}
        )
        
        # Les entrées haute priorité doivent être préservées
        assert "règles fondamentales" in context.lower()
```

### 12.4 Tests E2E

```python
# tests/e2e/test_game_session.py

import pytest
from src.core import GameEngine
from src.llm import MockLLMProvider

class TestGameSession:
    @pytest.fixture
    def engine(self):
        llm = MockLLMProvider(responses=[
            "Le garde vous regarde avec suspicion.",
            "Il hoche la tête et vous laisse passer.",
            "Derrière la porte, vous découvrez une grande salle."
        ])
        return GameEngine(llm_provider=llm)
    
    @pytest.mark.asyncio
    async def test_complete_quest(self, engine):
        # Démarrer une session
        session = await engine.create_session(world="fantasy_base")
        
        # Interaction 1
        response1 = await engine.process_input(
            session.id, 
            "Je m'approche du garde."
        )
        assert "garde" in response1.narrative.lower()
        
        # Interaction 2
        response2 = await engine.process_input(
            session.id,
            "Je le salue poliment."
        )
        assert "passe" in response2.narrative.lower()
        
        # Vérifier l'état final
        final_state = await engine.get_state(session.id)
        assert final_state.location == "grande_salle"
```

### 12.5 Coverage cible

| Module | Coverage minimum |
|--------|------------------|
| `core/engine.py` | 95% |
| `lore/` |90% |
| `character/` | 90% |
| `inventory/` | 90% |
| `memory/` | 85% |
| `llm/` | 80% (mock LLM) |
| `api/` | 75% |

---

## 13 · Logging et monitoring

### 13.1 Configuration structlog

```python
# config/logging.py

import structlog

def configure_logging():
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )
```

### 13.2 Événements loggés

| Événement | Niveau | Champs |
|-----------|--------|--------|
| Session créée | INFO | session_id, player_id, world_id |
| Message utilisateur | DEBUG | session_id, message_length, tokens |
| Lore injecté | DEBUG | session_id, entries_count, tokens_used |
| Réponse LLM | INFO | session_id, response_time_ms, tokens_generated |
| Erreur validation | WARNING | session_id, error_type, user_input_preview |
| Erreur LLM | ERROR | session_id, error_type, retry_count |
| Sauvegarde | INFO | session_id, file_size_kb |
| Jet de dés | DEBUG | session_id, notation, result |

### 13.3 Métriques collectées

```python
# Métriques Prometheus-style
METRICS = {
    "rpg_session_requests_total": Counter,
    "rpg_llm_response_time_seconds": Histogram,
    "rpg_llm_tokens_generated_total": Counter,
    "rpg_lore_injection_count": Histogram,
    "rpg_dice_rolls_total": Counter,
    "rpg_errors_total": Counter,
    "rpg_active_sessions": Gauge,
}
```

---

## 14 · Configuration

### 14.1 Structure de configuration

```yaml
# config/default.yaml
# Configuration optimisée pour RTX 4050 (6GB VRAM) + Llama 4 Scout

app:
  name: "mon-rpg-ia"
  version: "0.1.0"
  debug: false

llm:
  provider: "koboldcpp"
  url: "http://localhost:5001"
  model: "Llama-4-Scout-17B-16E-Instruct-IQ2_XXS.gguf"
  
  # Configuration MoE Offloading
  n_gpu_layers: 32          # Attention sur GPU
  n_cpu_moe: 16             # Experts en RAM
  flash_attention: true
  kv_cache_quant: "q4_1"    # KV Cache 4-bit
  
  # Contexte
  max_context_tokens: 16384
  max_response_tokens: 512
  
  # Génération
  temperature: 0.7
  top_p: 0.9
  top_k: 40
  
  retry:
    max_attempts: 3
    delay_seconds: [1, 2, 5]

lore:
  directory: "./lore"
  cache_embeddings: true
  embedding_model: "all-MiniLM-L6-v2"  # Léger, CPU
  
memory:
  max_context_tokens: 12288   # Laisse de la marge
  summary_threshold: 50
  summary_model: null          # Utilise le modèle principal

game:
  dice:
    seed: null# null = aléatoire
    log_rolls: true
  
  inventory:
    max_slots: 100
    max_weight: 100
  
  character:
    max_level: 20
    base_stats:
      hp_per_level: 10
      mana_per_level: 5

persistence:
  database: "sqlite://./data/game.db"
  saves_directory: "./data/saves"
  backup:
    enabled: true
    interval_hours: 6
    max_backups: 10

logging:
  level: "INFO"
  format: "json"
  file: "./data/logs/app.log"
  rotation:
    max_size_mb: 100
    backup_count: 5

api:
  host: "0.0.0.0"
  port: 8000
  cors_origins: ["http://localhost:8000"]
  rate_limit:
    requests_per_minute: 60
```

### 14.2 Validation de configuration

```python
from pydantic import BaseModel, Field, validator

class LLMConfig(BaseModel):
    provider: str
    url: str
    model: str
    max_context_tokens: int = Field(ge=512, le=131072)
    max_response_tokens: int = Field(ge=64, le=4096)
    temperature: float = Field(ge=0.0, le=2.0)
    
    @validator("provider")
    def validate_provider(cls, v):
        if v not in ["koboldcpp", "lmstudio", "ollama", "openai"]:
            raise ValueError(f"Unsupported provider: {v}")
        return v
    
    @validator("url")
    def validate_url(cls, v):
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v
```

---

## 15 · Plan de déploiement

### 15.1 Prérequis système

**Configuration cible (ASUS ROG Zephyrus G14):**

| Composant | Spécification | Notes |
|-----------|---------------|-------|
| OS | Windows 11 Professionnel | Build 26200+ |
| CPU | AMD Ryzen 9 8945HS |8c/16t, 4.0GHz boost |
| GPU | NVIDIA RTX 4050 Laptop | 6GB VRAM, Ada Lovelace |
| RAM | 32GB DDR5 | ~24GB disponibles |
| Stockage | SSD NVMe | 20+ GB libres requis |
| Python | 3.11+ | 64-bit obligatoire |
| CUDA | 12.x | Drivers RTX 40xx compatibles |

**Prérequis logiciels Windows:**

| Logiciel | Version | Commande de vérification |
|----------|---------|--------------------------|
| Python | 3.11+ | `python --version` |
| pip | 23.0+ | `pip --version` |
| Git | 2.40+ | `git --version` |
| CUDA Toolkit | 12.x | `nvcc --version` |
| Drivers NVIDIA | 535.0+ | `nvidia-smi` |

### 15.2 Installation (Windows 11 natif)

```powershell
# PRÉREQUIS: Ouvrir PowerShell en administrateur

# 1. Vérifier les prérequis
python --version  # Doit afficher 3.11+
nvidia-smi        # Doit afficher RTX 4050 avec ~6GB VRAM

# 2. Cloner le repository
cd C:\Users\$env:USERNAME\Documents\Code\Perso
git clone https://github.com/user/mon-rpg-ia.git
cd mon-rpg-ia

# 3. Créer l'environnement virtuel
python -m venv venv
.\venv\Scripts\Activate.ps1

# 4. Installer les dépendances
pip install --upgrade pip
pip install -r requirements.txt

# 5. Installer PyTorch avec CUDA 12.x
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# 6. Initialiser la base de données
python scripts/init_db.py

# 7. Télécharger les embeddings RAG
python scripts/download_embeddings.py

# 8. Lancer l'application
python -m src.api.main
```

### 15.3 Configuration KoboldCPP (Windows) — Llama 4 Scout

```powershell
# Télécharger KoboldCPP CUDA
# https://github.com/LostRuins/koboldcpp/releases

# ============================================================
# CONFIGURATION RECOMMANDÉE — Llama4 Scout IQ2_XXS
# ============================================================

koboldcpp.exe `
    --model "C:\Users\$env:USERNAME\models\Llama-4-Scout-17B-16E-Instruct-IQ2_XXS.gguf" `
    --n-gpu-layers 32 `
    --n-cpu-moe 16 `
    --flash-attn `
    --ctk q4_1 `
    --ctx-size 16384 `
    --smartcontext `
    --use-cublas `
    --threads 14 `
    --port 5001

# ============================================================
# OPTIONS EXPLIQUÉES
# ============================================================
# --n-gpu-layers 32    : Couches d'attention sur GPU
# --n-cpu-moe 16       : Experts MoE en RAM (CRITIQUE pour 6GB)
# --flash-attn         : Optimisation Flash Attention 2
# --ctk q4_1           : KV Cache 4-bit (permet 16k contexte)
# --ctx-size 16384     : Contexte maximum
# --smartcontext       : Évite recalcul complet
# --threads 14         : Utiliser tous les coeurs CPU (-2)

# ============================================================
# ALTERNATIVE — Contexte étendu (8k seulement)
# ============================================================

koboldcpp.exe `
    --model "Llama-4-Scout-17B-16E-Instruct-IQ2_XXS.gguf" `
    --n-gpu-layers 35 `
    --n-cpu-moe 16 `
    --flash-attn `
    --ctk q4_1 `
    --ctx-size 8192 `
    --use-cublas `
    --threads 14 `
    --port 5001

# Plus de GPU layers = plus rapide, mais contexte réduit

# ============================================================
# SI OOM (Out of Memory)
# ============================================================

# Solution 1: Réduire GPU layers
--n-gpu-layers 28

# Solution 2: Réduire contexte
--ctx-size 8192

# Solution 3: Quantization plus agressive (IQ1_S)
# Nécessite modèle IQ1_S (non disponible pour l'instant)
```

### 15.4 Téléchargement du modèle Llama 4 Scout

```powershell
# 1. Accéder à HuggingFace
# https://huggingface.co/meta-llama/Llama-4-Scout-17B-16E-Instruct

# 2. Accepter la licence (requis)
# Cliquer "Access repository" et accepter les termes

# 3. Télécharger via huggingface-cli
pip install huggingface_hub

huggingface-cli login
# Entrerer le token HuggingFace

# 4. Télécharger le modèle (version GGUF quantized)
# Les versions quantized sont faites par la communauté
# Chercher sur: https://huggingface.co/models?search=llama-4-scout-iq2

# Alternative: utiliser LM Studio pour le téléchargement automatique
# LM Studio > Models > Search "Llama 4 Scout IQ2"
```

### 15.5 Configuration LM Studio (alternative)

```yaml
# settings.yaml pour LM Studio

model: "Llama-4-Scout-17B-16E-Instruct-IQ2_XXS.gguf"
n_ctx: 16384

# MoE Offloading (CRITIQUE pour 6GB)
n_gpu_layers: 32
n_cpu_moe: 16    # Experts en RAM
offload_kqv: true

# Optimisations
flash_attention: true
kv_cache_quant: "q4_1"

# Performance
batch_size: 512
n_threads: 14
```

### 15.6 Où trouver les modèles quantized

| Source | Modèles disponibles | Qualité |
|--------|---------------------|---------|
| HuggingFace (Bartowski) | IQ2_XXS, IQ3_M, Q3_K_M | ⭐⭐⭐⭐⭐ |
| HuggingFace (MaziyarPanahi) | IQ2_XXS, Q4_K_M | ⭐⭐⭐⭐ |
| LM Studio Model Hub | Auto-quantized | ⭐⭐⭐ |
| Ollama Library | (à vérifier) | ⭐⭐⭐ |

**Recherche Google:**
```
"Llama 4 Scout IQ2_XXS GGUF site:huggingface.co"
"Llama-4-Scout-17B-16E quantized GGUF"
```

### 15.4 Checklist de production

- [ ] Configuration `debug: false`
- [ ] Secrets dans variables d'environnement
- [ ] Logs en mode JSON
- [ ] Backups configurés
- [ ] Rate limiting activé
- [ ] CORS configuré pour le domaine de production
- [ ] Tests passants
- [ ] Documentation API générée

---

## 16 · Gestion des risques

### 16.1 Risques identifiés

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|------------|
| Dérive narrative de l'IA | Élevée | Élevé | Système de règles strict, validation des actions |
| Perte de cohérence mémoire | Moyenne | Élevé | Résumé automatique, extraction de faits |
| Saturation du contexte LLM | Moyenne | Moyen | Optimisation aggressive, compression |
| Corruption de sauvegarde | Basse | Élevé | Backups automatiques, validation JSON |
| Performance dégradée | Moyenne | Moyen | Profilage, cache, lazy loading |
| Incompatibilité modèle | Basse | Moyen | Abstraction LLM, tests multi-provider |
| **OOM VRAM (RTX 4050)** | Moyenne | Élevé | Modèles ≤8B, KV Cache Q4, monitoring |
| **Thermal throttling (laptop)** | Moyenne | Moyen | Limiter batch_size, pauses, monitoring température |
| **VBS impact performance** | Basse | Faible | Config native, éviter Docker |

### 16.2 Risques spécifiques à la configuration

**VRAM limitée (6GB):**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         GESTION VRAM LIMITÉE                                │
│                                                                             │
│  PROBLÈME: 6GB ne permettent pas de gros modèles                            │
│                                                                             │
│  SYMPTÔMES:                                                                 │
│  ├── OOM (Out of Memory) au chargement                                     │
│  ├── Ralentissement brutal en milieu de session                            │
│  └── Contexte tronqué inattendu                                            │
│                                                                             │
│  MITIGATIONS:                                                                │
│  ├── 1. Modèles ≤8B en Q4_K_M (recommandé)                                 │
│  ├── 2. KV Cache en Q4 (division par 4 de la mémoire contexte)             │
│  ├── 3. Contexte max 16k (au lieu de 32k)                                  │
│  ├── 4. Flash Attention activé                                             │
│  └── 5. Monitoring temps réel de VRAM                                      │
│                                                                             │
│  FALLBACK:                                                                  │
│  └── Si OOM → réduire n_gpu_layers → hybride GPU/RAM                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Thermal throttling (laptop):**

Le ROG Zephyrus G14 peut throttler sous charge prolongée:

| Symptôme | Mitigation |
|----------|-------------|
| FPS/tokens chute après 10-15min | Mode"Haute performance" Windows |
| Températures >95°C | Limiter `n_gpu_layers` pour utiliser plus de RAM |
| Bruit ventilateur | Acceptable, monitorer avec HWiNFO64 |
| Crash aléatoire | Réduire `batch_size` à256ou 128 |

**Configuration anti-throttling:**

```python
# config/performance.yaml
thermal:
  max_temperature: 92# °C, seuil d'alerte
  throttle_threshold: 95# °C, seuil critique
  monitoring_interval: 30# secondes
  
  actions:
    - temp > 92: "reduce_batch_size"
    - temp > 95: "enable_offloading"
    - temp > 98: "pause_generation"
```

### 16.2 Plan de rollback

```python
class RollbackManager:
    def __init__(self, max_history: int = 10):
        self.history: deque[GameState] = deque(maxlen=max_history)
    
    def checkpoint(self, state: GameState):
        self.history.append(state.copy())
    
    def rollback(self, steps: int = 1) -> GameState:
        if steps > len(self.history):
            raise StateError(f"Cannot rollback {steps} steps, only {len(self.history)} available")
        
        return self.history[-steps]
    
    def save_checkpoint(self, session_id: str):
        # Sauvegarde sur disque
        path = self.save_dir / f"{session_id}_{datetime.now().isoformat()}.json"
        with open(path, 'w') as f:
            json.dump(self.current_state.to_dict(), f)
```

---

## 17 · Feuille de route

### Phase 1 — Fondations (Semaines 1-4)

| Semaine | Objectifs | Livrables |
|---------|-----------|-----------|
| 1 | Architecture de base | Structure projet, CI/CD, config |
| 2 | Gestion d'état | GameEngine, GameState, validation |
| 3 | Système de dés | DiceRoller, types de dés, jets |
| 4 | Persistance | SQLite, JSON, sauvegarde/restauration |

**Pierres milliaires Phase 1:**
- `[ ]` Projet initialisé avec structure complète
- `[ ]` Tests unitaires passants (>80% coverage)
- `[ ]` État de jeu sauvegardable et restaurable
- `[ ]` Jets de dés fonctionnels et loggués

### Phase 2 — Lorebook (Semaines 5-8)

| Semaine | Objectifs | Livrables |
|---------|-----------|-----------|
| 5 | Structure Lorebook | Chargement JSON, entrées |
| 6 | Déclenchement | Mots-clés, regex, conditions |
| 7 | Injection | Ordre, priorité, budget tokens |
| 8 | RAG basique | Embeddings, recherche sémantique |

**Pierres milliaires Phase 2:**
- `[ ]` Lorebook chargé depuis fichiers JSON
- `[ ]` Déclenchement par mots-clés fonctionnel
- `[ ]` Injection ordonnée par priorité
- `[ ]` RAG basique opérationnel

### Phase 3 — Intégration LLM (Semaines 9-12)

| Semaine | Objectifs | Livrables |
|---------|-----------|-----------|
| 9 | Interface LLM | Gateway, providers, streaming |
| 10 | Construction prompt | Templates, assemblage |
| 11 | Parsing réponse | Extraction actions, narration |
| 12 | Gestion erreurs | Retry, fallback, logging |

**Pierres milliaires Phase 3:**
- `[ ]` Connexion KoboldCPP fonctionnelle
- `[ ]` Réponses streamées en temps réel
- `[ ]` Actions parsées et exécutées
- `[ ]` Gestion robuste des erreurs

### Phase 4 — Personnage & Inventaire (Semaines 13-16)

| Semaine | Objectifs | Livrables |
|---------|-----------|-----------|
| 13 | Gestion personnage | Stats, classes, conditions |
| 14 | Inventaire | Items, équipement, poids |
| 15 | Validation état | Invariants, contraintes |
| 16 | Intégration | Actions affectant l'état |

**Pierres milliaires Phase 4:**
- `[ ]` Feuille de personnage complète
- `[ ]` Inventaire avec contraintes
- `[ ]` Actions LLM modifiant l'état
- `[ ]` Rollback sur état invalide

### Phase 5 — Mémoire & Contexte (Semaines 17-20)

| Semaine | Objectifs | Livrables |
|---------|-----------|-----------|
| 17 | Gestion contexte | Fenêtre glissante, compression |
| 18 | Résumé automatique | Extraction, condensation |
| 19 | Faits importants | Extraction, stockage |
| 20 | Optimisation | Cache, lazy loading |

**Pierres milliaires Phase 5:**
- `[ ]` Contexte géré automatiquement
- `[ ]` Résumé après N messages
- `[ ]` Faits extraits et consultables
- `[ ]` Performance <3s premier token

### Phase 6 — Interface & Finalisation (Semaines 21-24)

| Semaine | Objectifs | Livrables |
|---------|-----------|-----------|
| 21 | API REST | Endpoints, documentation |
| 22 | Tests E2E | Scénarios complets |
| 23 | Documentation | README, guides |
| 24 | Polish | Performance, UX |

**Pierres milliaires Phase 6:**
- `[ ]` API complète et documentée
- `[ ]` Suite de tests E2E passante
- `[ ]` Documentation utilisateur complète
- `[ ]` Benchmark de performance validé

---

## 18 · Standards de qualité

### 18.1 Code review checklist

- [ ] Code lisible et auto-documenté
- [ ] Types complets (mypy strict)
- [ ] Tests unitaires pour nouvelle logique
- [ ] Pas de secrets hardcoded
- [ ] Gestion d'erreur appropriée
- [ ] Logs structurés avec contexte
- [ ] Documentation API à jour
- [ ] Pas de dégradation de performance

### 18.2 Definition of Done

Une fonctionnalité estterminée quand:

1. **Code**: Implémentation complète, types stricts, lint clean
2. **Tests**: Coverage ≥80%, tests passants, edge cases couverts
3. **Documentation**: Docstrings, README mis à jour si nécessaire
4. **Review**: Code review approuvé par au moins une personne
5. **Integration**: Intégrée sans casser les tests existants
6. **Performance**: Respecte les benchmarks définis
7. **Logs**: Logging structuré approprié

### 18.3 Métriques de qualité

| Métrique | Cible | Outil |
|----------|-------|-------|
| Test coverage | ≥ 80% | pytest-cov |
| Type coverage | ≥ 95% | mypy --strict |
| Lint errors | 0 | ruff |
| Complexity | ≤ 10 (functions) | radon |
| Documentation | 100% public API | pydocstyle |

---

## Annexes

### A. Glossaire

| Terme | Définition |
|-------|------------|
| **Lorebook** | Base de données d'informations sur le monde, injectées dynamiquement |
| **Contexte** | Fenêtre de tokens visible par le LLMà un instant T |
| **Token** | Unité de texte traitée par le LLM (~0.75 mot) |
| **RAG** | Retrieval-Augmented Generation, recherche sémantique |
| **Injection** | Ajout automatique de texte dans le contexte |
| **Trigger** | Mot-clé ou condition qui déclenche l'injection |

### B. Références

- [KoboldCPP Documentation](https://github.com/LostRuins/koboldcpp)
- [SillyTavern Documentation](https://docs.sillytavern.app/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Structlog Documentation](https://www.structlog.org/)

### C. Changelog du document

| Version | Date | Modifications |
|---------|------|---------------|
| 1.0.0 | Mars 2026 | Création initiale |
| 1.1.0 | Mars 2026 | Configuration matérielle spécifique (RTX 4050, Ryzen 9 8945HS), Windows 11 natif |
| 1.2.0 | Mars 2026 | **Llama 4 Scout comme modèle principal**, MoE Offloading, IQ2_XXS quantization, contexte 10M tokens |

---

### D. Benchmarking RTX 4050 (6GB) — Llama 4 Scout

**Résultats estimés (Llama 4 Scout IQ2_XXS + MoE Offloading):**

| Configuration | VRAM | RAM | Contexte | Tokens/sec (prompt) | Tokens/sec (gen) |
|---------------|------|-----|----------|---------------------|------------------|
| **Scout IQ2_XXS** | ~6GB | ~10GB | 10k | ~30-40 | **10-15** |
| **Scout IQ2_XXS** | ~6GB | ~10GB | 16k | ~25-35 | **8-12** |
| Scout Q3_K_M | ~7GB | ~12GB | 8k | ~20-30 | 6-10 |
| Mistral 7B Q4 (ref) | ~4GB | - | 16k | ~50 | 25-35 |
| Llama 3.2 3B Q5 (ref) | ~2.5GB | - | 16k | ~80 | 40-50 |

**Note importante:** Les performances de Scout sont Impactées par:
- MoE Offloading: Experts chargés depuis RAM (latence)
- Quantization IQ2_XXS: Plus petite mais légèrement moins précise
- Contexte: Plus le contexte est grand, plus la génération est lente

**Pourquoi Scout malgré la vitesse réduite ?**

| Critère | Scout IQ2_XXS | Mistral 7B Q4 | Avantage |
|---------|---------------|---------------|----------|
| Qualité narrative | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Scout+15% |
| Suivi instructions | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Scout+20% |
| Contexte disponible |10M natif | 32k | Scout+300x |
| Multimodal | ✅ | ❌ | Scout unique |
| Français natif | ✅ | ❌ | Scout unique |
| Vitesse | 10-15 tok/s | 25-35 tok/s | Mistral+150% |

**Conclusion:** Scout est plus lent mais OFFRE:
- Meilleure qualité narrative
- Contexte quasi-illimité pour campagnes longues
- Compréhension d'images (cartes, portraits)
- Français natif optimal

**Impact du contexte sur VRAM:**

```
Contexte (tokens) | KV Cache F32 | KV Cache Q4 | KV Cache Q8
------------------|--------------|--------------|-------------
4k                | ~120 MB      | ~30 MB       | ~60 MB
8k                | ~240 MB      | ~60 MB       | ~120 MB
16k               | ~480 MB      | ~120 MB      | ~240 MB
32k               | ~960 MB      | ~240 MB      | ~480 MB
```

**Pour Llama 4 Scout (contexte 10M natif):**
- Les 10M tokens ne sont PAS tous en VRAM
- Seul le contexte actif (window) est chargé
- KV Cache Q4 permet window de 10k-16k tokens
- Le reste est géré par le modèle natif

**Commandes de test:**

```powershell
# Test de performance Scout
python scripts/benchmark_llm.py `
    --model "Llama-4-Scout-IQ2_XXS.gguf" `
    --context 8192 `
    --prompt "Génère une description de tavernemédiévale" `
    --tokens 100

# Test de consommation VRAM
nvidia-smi --query-gpu=memory.used,memory.total --format=csv -l 1

# Test thermique (Zephyrus G14)
# Utiliser HWiNFO64 pour monitorer températures GPU/CPU

# Test MoE Offloading
# Comparer avec/sans n-cpu-moe pour voir l'impact
koboldcpp.exe --model model.gguf --n-gpu-layers 32 --n-cpu-moe 0   # Sans offload
koboldcpp.exe --model model.gguf --n-gpu-layers 32 --n-cpu-moe 16  # Avec offload
```

### E. Configuration matérielle détaillée (Zephyrus G14 GA403UU)

**Spécifications complètes:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│            ASUS ROG Zephyrus G14 GA403UU — Fiche Technique                  │
│                                                                             │
│  PROCESSEUR                                                                 │
│  ├── Model: AMD Ryzen 9 8945HS                                             │
│  ├── Coeurs: 8 | Threads: 16                                                │
│  ├── Base: 4.0 GHz | Boost: 5.2 GHz                                         │
│  ├── Cache L3: 16MB                                                         │
│  ├── TDP: 35-54W (configurable)                                             │
│  └── Architecture: Zen 4 (4nm)                                              │
│                                                                             │
│  GRAPHIQUE DÉDIÉE                                                           │
│  ├── Model: NVIDIA GeForce RTX 4050 Laptop                                  │
│  ├── VRAM: 6GB GDDR6                                                        │
│  ├── CUDA Cores: 2560                                                       │
│  ├── TGP: 75-100W (Dynamic Boost)                                           │
│  └── Architecture: Ada Lovelace (5nm)                                       │
│                                                                             │
│  MÉMOIRE                                                                    │
│  ├── RAM: 32GB DDR5 (assumé LPDDR5)                                         │
│  ├── Vitesse: ~4800 MHz                                                     │
│  └── Utilisable: ~24GB (après réservation système)                          │
│                                                                             │
│  GRAPHIQUE INTÉGRÉE                                                         │
│  ├── Model: AMD Radeon 780M                                                 │
│  ├── Architecture: RDNA 3                                                   │
│  └── Note: Non utilisable pour ML (ROCm non supporté sur mobile)            │
│                                                                             │
│  STOCKAGE (assumé)                                                          │
│  └── SSD NVMe PCIe 4.0 x4                                                   │
│                                                                             │
│  OPTIMISATIONS DISPONIBLES                                                  │
│  ├── ASUS Armory Crate → Mode "Performance"                                 │
│  ├── CPU Boost mode → activé                                                │
│  ├── Fan curve → personnalisable                                            │
│  └── MUX Switch → présente (si modèle 2024)                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Windows 11 Build 26200 spécificités:**

Cette build est une version Windows 11 Canary/Insider avec:
- VBS (Virtualization-Based Security) activé par défaut
- Hyper-V détecté (peut impacter Docker/WSL2)
- Sécurité renforcée (HVCI, Kernel DMA Protection)

**Impact sur le développement:**
- Préférer Python natif plutôt que WSL2
- Si Docker nécessaire: utiliser Docker Desktop avec WSL2 backend (5-15% overhead)
- Désactiver VBS si problèmes de performance (risque sécurité accru)