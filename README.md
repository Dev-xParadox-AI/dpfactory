# Digital Product Factory 🏭

**W pełni zautomatyzowana fabryka produktów cyfrowych dla polskich twórców.**  
Budżet: **0 PLN** | Hosting: **Cloudflare Workers (free) + GitHub Actions (free)** | Publikacja: **Gumroad (free tier + API)**

---

## 🎯 Co to robi?

1. **Generuje** produkty cyfrowe (prompt packs, szablony Notion, workflow n8n, kalendarze contentu, vaults Obsidian) pod polskie nisze
2. **Pakuje** je w PDF, Markdown, JSON, ZIP z licencją i README
3. **Publikuje** na Gumroad przez API (pay-what-you-want lub cena stała)
4. **Działa cyklicznie** (cron 2x/dzień) bez Twojej ingerencji

## 📦 Nisze skonfigurowane (gotowe do odpalenia)

| Nisza | Produkty | Cena | Słowa kluczowe |
|-------|----------|------|----------------|
| `notion-templates-pl` | Dashboards, systemy (Life OS, PARA, CRM) | 0 / 29 / 49 PLN | notion szablon, dashboard, organizacja |
| `ai-prompts-pl` | Pakiety promptów, cheatsheety, workflowy AI | 0 / 19 / 39 PLN | prompty chatgpt, prompt engineering, midjourney |
| `obsidian-pkm-pl` | Vaults, konfiguracje pluginów, systemy PKM | 0 / 29 / 59 PLN | obsidian vault, pkm polski, drugi mózg |
| `automation-n8n-pl` | Workflows n8n/Make, blueprinty automatyzacji | 0 / 49 / 99 PLN | n8n workflow, automatyzacja make, no-code |
| `content-templates-pl` | Szablony LinkedIn, newsletter, blog, hooki, kalendarze | 0 / 29 / 59 PLN | szablony linkedin, content calendar, haki |

---

## 🚀 Szybki start (5 min)

### 1. Sklonuj i skonfiguruj

```bash
git clone <twoje-repo> dpfactory
cd dpfactory
cp .env.example .env
# Edytuj .env - wpisz swoje tokeny (patrz sekcja niżej)
```

### 2. Tokeny do uzyskania (wszystkie **za darmo**)

| Serwis | Co pobrać | Gdzie |
|--------|-----------|-------|
| **Gumroad** | `Access Token`, `Application ID` | https://app.gumroad.com/settings/applications → New Application |
| **Cloudflare** | `Account ID`, `API Token` (Workers AI) | https://dash.cloudflare.com/profile/api-tokens → Create Token → "Workers AI" |

> 💡 **Gumroad Free Tier**: 0% prowizji przy płatnościach "pay what you want", 10% + 0,25$ przy cenie stałej. Bez opłat miesięcznych.

### 3. Test lokalny (dry run)

```bash
pip install -r requirements.txt
# Windows: może potrzebować Visual C++ Build Tools dla WeasyPrint
python -m src.scheduler.factory_scheduler --dry-run --count 1 --niches notion-templates-pl
```

Powinno wygenerować produkt w `products/` i zalogować sukces.

### 4. Wdróż na GitHub Actions (automatyczny cron)

1. Push do GitHub
2. Repo → Settings → Secrets and variables → Actions → New repository secret:
   - `GUMROAD_ACCESS_TOKEN`
   - `GUMROAD_APPLICATION_ID`
   - `CF_ACCOUNT_ID`
   - `CF_API_TOKEN`
3. Actions → "Digital Product Factory" → Run workflow (lub czekaj na cron: 06:00 i 18:00 CET)

### 5. (Opcjonalnie) Cloudflare Workers dla AI generation

Jeśli chcesz odciążyć GitHub Actions (limit 2000 min/miesiąc):

```bash
# Wrangler CLI
npm install -g wrangler
wrangler login
# Skonfiguruj wrangler.toml (patrz niżej)
wrangler deploy
```

---

## ⚙️ Konfiguracja

### `config/settings.yaml` - główna konfiguracja

```yaml
factory:
  products_per_run: 3      # ile produktów na jedną sesję (per niche)
  runs_per_day: 2          # ile razy dziennie (cron)

niches:
  # Dodawaj/usuwaj/edytuj nisze tutaj
  - id: "moja-nowa-nisza"
    name: "Moja Nisza"
    tags: ["tag1", "tag2"]
    target_audience: "grupa docelowa PL"
    product_types: ["template", "guide"]
    price_range_pln: [0, 29, 49]
    seo_keywords: ["slowo1", "slowo2"]

gumroad:
  default_visibility: "public"  # "draft" do recenzji
  default_license: "personal_use"

ai:
  provider: "cloudflare_ai"     # albo "ollama_local"
  models:
    text: "@cf/meta/llama-3-8b-instruct"
    code: "@cf/meta/codellama-7b-instruct"
```

### `wrangler.toml` (Cloudflare Workers)

```toml
name = "dpfactory-ai"
main = "src/workers/ai_worker.js"
compatibility_date = "2024-01-01"

[vars]
AI_PROVIDER = "cloudflare_ai"

[ai]
binding = "AI"  # Workers AI binding
```

---

## 🏗️ Architektura

```
┌─────────────────────────────────────────────────────────────┐
│                    GITHUB ACTIONS (cron)                    │
│  06:00 CET  •  18:00 CET   •   Manual trigger               │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  FACTORY SCHEDULER                          │
│  1. Load config → 2. Pick niches → 3. Generate specs        │
└─────────────────────────────┬───────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
    ┌─────────────────┐ ┌─────────────┐ ┌─────────────┐
    │  AI GENERATOR   │ │  PACKAGER   │ │  PUBLISHER  │
    │  (Cloudflare AI │ │  (WeasyPrint│ │  (Gumroad   │
    │   or Ollama)    │ │   + Zip)    │ │   API)      │
    └────────┬────────┘ └──────┬──────┘ └──────┬──────┘
             │                 │                │
             └─────────────────┴────────────────┘
                              │
                              ▼
                   ┌─────────────────────┐
                   │   PRODUCTS/LOGS     │
                   │  (Artifacts / R2)   │
                   └─────────────────────┘
```

---

## 📁 Struktura projektu

```
dpfactory/
├── config/
│   └── settings.yaml          # Główna konfiguracja
├── src/
│   ├── config_loader.py       # Ładowanie configu + secrets
│   ├── generators/
│   │   ├── product_generator.py      # Specyfikacje produktów
│   │   └── ai_content_generator.py   # Generowanie treści AI
│   ├── packagers/
│   │   └── product_packager.py       # PDF/JSON/ZIP
│   ├── publishers/
│   │   └── gumroad_publisher.py      # Gumroad API
│   ├── scheduler/
│   │   └── factory_scheduler.py      # Orkiestrator (ENTRYPOINT)
│   └── utils/
├── templates/
│   ├── pdf/product_template.html     # Szablon PDF
│   └── licenses/personal_use.md      # Licencja
├── products/                        # Wygenerowane produkty (gitignored)
├── logs/                            # Logi i raporty
├── .github/workflows/factory.yml    # GitHub Actions cron
├── requirements.txt                 # Python deps
├── .env.example                     # Template zmiennych env
└── wrangler.toml                    # Cloudflare Workers config
```

---

## 🔧 Rozszerzanie

### Dodanie nowej niszy

1. Dopisz do `config/settings.yaml` w sekcji `niches`
2. Dodaj szablony w `src/generators/product_generator.py` → `PRODUCT_TEMPLATES["nowa-nisza"]`
3. Przetestuj: `python -m src.scheduler.factory_scheduler --dry-run --count 1 --niches nowa-nisza`

### Własny model AI

Zmień `ai.provider` na `"ollama_local"` i uruchom `ollama serve` lokalnie (lub na VPS).

### Inna platforma sprzedaży

Zaimplementuj nowy publisher w `src/publishers/` implementując interfejs `publish(packaged) -> PublishResult`.

---

## 📊 Monitoring

- **GitHub Actions**: Logi w zakładce Actions, artefakty `factory-run-reports`
- **Logi lokalne**: `logs/factory.log` + `logs/runs/factory_YYYYMMDD_HHMMSS.json`
- **Raporty**: Każdy run generuje JSON ze szczegółami (model AI, tokeny, latencja, status publikacji)

---

## ⚠️ Ważne ograniczenia (budżet 0 PLN)

| Zasób | Limit darmowy | Wpływ |
|-------|---------------|-------|
| GitHub Actions | 2000 min/miesiąc | ~66 runów po 30 min → OK dla 2x/dzień |
| Cloudflare Workers AI | 100k req/dzień | Bardzo duży margines |
| Cloudflare R2 | 10 GB storage | Produkty są lekkie (KB-MB) |
| Gumroad | 0$ miesięcznie | Prowizja tylko od sprzedaży |
| Ollama (lokalnie) | Twoje GPU/CPU | Fallback gdy CF padnie |

---

## 🛠️ Rozwiązywanie problemów

| Problem | Rozwiązanie |
|---------|-------------|
| `weasyprint` nie instaluje się na Windows | Zainstaluj Visual C++ Build Tools + GTK3 (lub użyj GitHub Actions) |
| Cloudflare AI zwraca 403 | Sprawdź `CF_ACCOUNT_ID` i `CF_API_TOKEN` (permission: Workers AI) |
| Gumroad "Invalid access token" | Sprawdź `GUMROAD_ACCESS_TOKEN` i `GUMROAD_APPLICATION_ID` |
| Produkty nie pojawiają się na Gumroad | Sprawdź `default_visibility: "public"` w configu |
| Cron nie uruchamia się | Sprawdź Actions → Workflow → "Digital Product Factory" → Enable workflow |

---

## 📜 Licencja

MIT – używaj, modyfikuj, sprzedawaj produkty wygenerowane przez tę fabrykę.

---

## 🤝 Wsparcie

- Issues na GitHubie
- Discord/Slack webhook w `.env` dla powiadomień o błędach

---

**Zbudowane z ❤️ dla polskich twórców. Automatyzuj, skaluj, zarabiaj.**