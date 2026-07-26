"""
Digital Product Factory - AI Product Generator
Generates digital products (prompt packs, templates, workflows) for Polish niches using AI.
"""
import json
import random
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from src.config_loader import config, NicheConfig


@dataclass
class ProductSpec:
    """Specification for a single product to generate."""
    niche_id: str
    product_type: str
    title: str
    description: str
    tags: List[str]
    seo_keywords: List[str]
    price_pln: int
    content_prompt: str  # Detailed prompt for AI to generate the actual product content
    metadata: Dict[str, Any]


class ProductGenerator:
    """Generates product specifications for each niche."""
    
    # Product templates per niche
    PRODUCT_TEMPLATES = {
        "notion-templates-pl": {
            "template": [
                {
                    "type": "dashboard",
                    "title_patterns": [
                        "System {topic} w Notion – Gotowy Dashboard",
                        "Notion Dashboard: {topic} dla {audience}",
                        "Kompletny system {topic} – Szablon Notion (PL)"
                    ],
                    "topics": [
                        "zarządzanie projektami", "CRM dla freelancerów", "planowanie kwartalne",
                        "budżet domowy", "tracking nawyków", "baza wiedzy (Second Brain)",
                        "zarządzanie klientami", "pipeline sprzedaży", "kalendarz contentu",
                        "zarządzanie zadaniami GTD", "planowanie celów OKR", "inwentarz aktywów"
                    ],
                    "description_template": "Gotowy do użycia szablon Notion do {topic}. Zawiera: {features}. Idealny dla {audience}. Wersja polska, gotowy import jednym kliknięciem.",
                    "features_pool": [
                        "baza danych z gotowymi widokami (Kanban, Tabela, Kalendarz, Galeria)",
                        "zautomatyzowane formuły i rollupy",
                        "gotowe filtry i sortowania",
                        "sekcja dashboard z podsumowaniem KPI",
                        "integracja z Google Calendar / Todoist (via synced databases)",
                        "instrukcja wideo (link do YouTube Shorts)",
                        "wersja mobilna i desktopowa"
                    ]
                },
                {
                    "type": "system",
                    "title_patterns": [
                        "System {topic} – Pełna Implementacja Notion",
                        "{topic}: System Notion od A do Z",
                        "Master System: {topic} (Polska Wersja)"
                    ],
                    "topics": [
                        "zarządzanie życiem (Life OS)", "system produktywności", "baza wiedzy PARA",
                        "zarządzanie finansami osobistymi", "system nauki i rozwoju", "portfolio projektów"
                    ],
                    "description_template": "Kompletny system Notion do {topic}. Składa się z {count} połączonych baz danych, {views} widoków i gotowych automatyzacji. Wdrożenie w 5 minut.",
                    "features_pool": [
                        "architektura PARA / GTD / Second Brain",
                        "tygodniowe i miesięczne revue (gotowe szablony)",
                        "system tagowania i linkowania dwukierunkowego",
                        "dashboard z metrykami i progress bars",
                        "szablony stron dla typowych przypadków użycia"
                    ]
                }
            ]
        },
        "ai-prompts-pl": {
            "template": [
                {
                    "type": "prompt_pack",
                    "title_patterns": [
                        "{count} Promptów do {topic} – Pakiet PL",
                        "Master Prompt Pack: {topic} (Polski)",
                        "Biblioteka Promptów: {topic} – Gotowe do Kopiowania"
                    ],
                    "topics": [
                        "copywriting LinkedIn", "newslettery sprzedażowe", "skrypty Reels/Shorts/TikTok",
                        "SEO blog posts", "email marketing", "landing page copy",
                        "Midjourney photorealism", "Midjourney brand assets", "logo design prompts",
                        "coding assistants (refactoring, tests, docs)", "code review prompts", "architecture decisions",
                        "analiza danych Python", "automatyzacja n8n/Make", "RAG i chatboty",
                        "personal branding", "lead magnety", "webinary i VSL"
                    ],
                    "description_template": "Pakiet {count} gotowych promptów do {topic}. Każdy prompt zawiera: rolę, kontekst, format wyjścia, przykłady few-shot i wersję 'dla leniwych' (one-liner). Testowane na GPT-4o / Claude 3.5 / Gemini 1.5. Wersja polska.",
                    "features_pool": [
                        "system prompts + user prompts",
                        "parametryzowane zmienne (wstawiasz swoje dane)",
                        "wersje dla różnych modeli (OpenAI, Anthropic, Google, lokalne)",
                        "cheatsheet PDF z strukturą promptu",
                        "przykłady wyjść (before/after)",
                        "checklista jakości odpowiedzi"
                    ]
                },
                {
                    "type": "cheatsheet",
                    "title_patterns": [
                        "Cheatsheet: {topic} – A4 do Wydruku",
                        "Ściąga {topic} – Format PDF (PL)",
                        "Quick Reference: {topic} dla Twórców PL"
                    ],
                    "topics": [
                        "prompt engineering framework", "parametry Midjourney v6", "ChatGPT system prompts",
                        "Claude artifacts patterns", "RAG retrieval strategies", "function calling schemas"
                    ],
                    "description_template": "Jednostronicowa ściąga (A4, PDF) do {topic}. Kluczowe wzorce, parametry, triki i anti-patterns. Idealna do nadruku i wklejenia na ścianę.",
                    "features_pool": [
                        "format A4, gotowy do druku",
                        "kolorowe kodowanie sekcji",
                        "kody QR do przykładów online",
                        "wersja jasna i ciemna (dla trybu nocnego)"
                    ]
                },
                {
                    "type": "workflow",
                    "title_patterns": [
                        "Workflow AI: {topic} – Krok po Kroku",
                        "Automatyzacja {topic} z AI (n8n + LLM)",
                        "Pipeline {topic}: Od Zera do Gotowca"
                    ],
                    "topics": [
                        "content repurposing (1 wideo → 20 postów)", "lead research & outreach",
                        "SEO content pipeline", "kodowanie z AI (spec → kod → testy → docs)",
                        "analiza konkurencji", "tworzenie lead magnetów"
                    ],
                    "description_template": "Gotowy workflow do {topic}. Zawiera: diagram Mermaid, JSON n8n/Make, prompty do każdego kroku, checklistę QA. Uruchamiasz i masz gotowy wynik.",
                    "features_pool": [
                        "plik JSON do importu w n8n / Make",
                        "diagram Mermaid (renderuje się w Notion/GitHub/Obsidian)",
                        "prompty do każdego węzła LLM",
                        "test cases i expected outputs",
                        "instrukcja wdrożenia (5 min)"
                    ]
                }
            ]
        },
        "obsidian-pkm-pl": {
            "template": [
                {
                    "type": "vault",
                    "title_patterns": [
                        "Obsidian Vault: {topic} – Gotowy System (PL)",
                        "Drugi Mózg: {topic} – Vault Startowy",
                        "PKM System {topic} – Importuj i Działaj"
                    ],
                    "topics": [
                        "Second Brain PARA", "Zettelkasten uproszczony", "Daily Notes + Periodic Notes",
                        "Project Management", "Research & Literature Notes", "Learning & Courses Tracker",
                        "Personal CRM", "Habit & Routine Tracker", "Decision Journal"
                    ],
                    "description_template": "Gotowy vault Obsidian do {topic}. Zawiera: strukturę folderów, pluginy (Community Plugins), szablony (Templater), dataview queries, CSS snippets. Wersja polska, dokumentacja w vault.",
                    "features_pool": [
                        "plik .obsidian/plugins z gotową konfiguracją",
                        "szablony Templater z dynamicznymi datami",
                        "Dataview queries do dashboardów",
                        "CSS snippets (ukrywanie UI, lepsza typografia)",
                        "Canvas maps (wizualne mapy myśli)",
                        "instrukcja PDF + wideo"
                    ]
                },
                {
                    "type": "plugin_config",
                    "title_patterns": [
                        "Konfiguracja Pluginów Obsidian: {topic}",
                        "Plugin Pack: {topic} – JSON + Instrukcja",
                        "Must-have Plugins do {topic} (PL)"
                    ],
                    "topics": [
                        "produktywność (Tasks, Calendar, Kanban)", "badania (Zotero, Highlights, Dataview)",
                        "pisanie (Outliner, Linter, Style Settings)", "automatyzacja (Shell commands, QuickAdd)"
                    ],
                    "description_template": "Gotowa konfiguracja {count} pluginów do {topic}. Plik JSON do importu + opis każdego pluginu i dlaczego warto. Oszczędzasz godziny trial-and-error.",
                    "features_pool": [
                        "plik community-plugins.json",
                        "plik core-plugins.json",
                        "settings dla każdego pluginu (hotkeys, opcje)",
                        "lista alternatyw (jeśli plugin przestanie działać)"
                    ]
                }
            ]
        },
        "automation-n8n-pl": {
            "template": [
                {
                    "type": "workflow_json",
                    "title_patterns": [
                        "n8n Workflow: {topic} – Gotowy JSON",
                        "Automatyzacja {topic} (n8n/Make) – Import Gotowy",
                        "Workflow {topic} – No-Code dla PL"
                    ],
                    "topics": [
                        "lead generation z LinkedIn", "content repurposing (YT → LinkedIn/Twitter/Newsletter)",
                        "monitoring cen konkurenta", "automatyczne faktury (Google Sheets → PDF → Email)",
                        "sync Notion ↔ Google Calendar", "webhook → AI processing → Slack/Email",
                        "scraping ofert pracy", "backup bazy danych do R2/S3", "raportowanie SEO (GSC + GA4 → Slack)",
                        "onboarding klienta (Typeform → Notion → Email → CRM)"
                    ],
                    "description_template": "Gotowy workflow n8n do {topic}. Plik JSON do importu (1 kliknięcie). Wszystkie node'y skonfigurowane, expressiony przetestowane. Wymaga: darmowe konto n8n.cloud lub self-host. Instrukcja wdrożenia 10 min.",
                    "features_pool": [
                        "plik workflow.json",
                        "plik credentials.json.template (wypełniasz swoje klucze)",
                        "diagram Mermaid architektury",
                        "test data do uruchomienia testowego",
                        "error handling w każdym węźle",
                        "rate limiting i retry logic"
                    ]
                },
                {
                    "type": "blueprint",
                    "title_patterns": [
                        "Blueprint Automatyzacji: {topic} – Schemat + Narzędzia",
                        "Architektura {topic} – Decyzje Techniczne (PL)",
                        "System Design: {topic} dla Solopreneurów"
                    ],
                    "topics": [
                        "personal CRM z AI", "content factory automatyczna", "lead gen system",
                        "finance tracking automat", "learning system z spaced repetition"
                    ],
                    "description_template": "Blueprint systemu {topic}. Zawiera: diagramy architektury, wybór narzędzi (z darmowymi tierami), przepływ danych, szacunkowy koszt (0 PLN), plan wdrożenia krok po kroku. Format PDF + Mermaid.",
                    "features_pool": [
                        "diagramy C4 / Mermaid",
                        "tabela narzędzi z darmowymi limitami",
                        "data flow diagram",
                        "checklista wdrożenia",
                        "ryzyka i mitigacje"
                    ]
                }
            ]
        },
        "content-templates-pl": {
            "template": [
                {
                    "type": "template_pack",
                    "title_patterns": [
                        "{count} Szablonów {topic} – Gotowe do Użycia (PL)",
                        "Baza Szablonów: {topic} – Pakiet PL",
                        "Content Templates: {topic} – Wersja Polska"
                    ],
                    "topics": [
                        "LinkedIn posty (haki, story, authority, sales)", "newslettery (welcome, nurture, sales, re-engagement)",
                        "artykuły blogowe (how-to, listicle, case study, opinion)", "skrypty wideo (Reels, Shorts, YT Long, VSL)",
                        "lead magnety (checklista, cheatsheet, mini-kurs, template)", "landing page sekcje (hero, benefits, social proof, FAQ)",
                        "email sequences (onboarding, abandoned cart, win-back)", "carousels LinkedIn/Instagram"
                    ],
                    "description_template": "Pakiet {count} gotowych szablonów do {topic}. Każdy szablon: struktura + placeholdery + przykład wypełniony + wskazówki copywritingowe. Format: Notion (import 1 klik) + Markdown + Google Docs. Wersja polska.",
                    "features_pool": [
                        "szablony w 3 formatach (Notion, MD, GDocs)",
                        "biblioteka haków (100+ otwieraczy)",
                        "formuły copy (AIDA, PAS, BAB, 4U, QUEST)",
                        "checklista jakości przed publikacją",
                        "kalendarz contentowy (Notion template)"
                    ]
                },
                {
                    "type": "hook_library",
                    "title_patterns": [
                        "Biblioteka Haków: {topic} – 200+ Otwieraczy (PL)",
                        "Haki do {topic} – Gotowe Pierwsze Zdania",
                        "Hook Vault: {topic} – Polskie Wersje"
                    ],
                    "topics": [
                        "LinkedIn (B2B, personal brand)", "newsletter (open rate boosters)",
                        "Reels/Shorts (retencja 3s)", "blog (CTR z SERP)", "sales DM (bez spamowania)"
                    ],
                    "description_template": "Kolekcja {count} haków do {topic}. Podzielone na kategorie: curiosity, authority, story, contrarian, data-driven, pain-point. Gotowe do kopiowania i adaptacji. Format CSV + Notion database.",
                    "features_pool": [
                        "CSV z kolumnami: kategoria, hak, przykład użycia, długość",
                        "Notion database z filtrami i tagami",
                        "tagowanie: B2B/B2C, długie/krótkie, format",
                        "A/B test framework (jak testować haki)"
                    ]
                },
                {
                    "type": "calendar",
                    "title_patterns": [
                        "Kalendarz Contentowy: {topic} – 90 Dni Gotowych Tematów",
                        "Content Calendar {topic} – Plan na Kwartał (PL)",
                        "90 Dni Contentu: {topic} – Zero Myślenia"
                    ],
                    "topics": [
                        "personal branding LinkedIn", "B2B lead gen content", "educational niche",
                        "creator economy", "SaaS marketing", "freelancer portfolio"
                    ],
                    "description_template": "Kalendarz na 90 dni do {topic}. Każdy dzień: temat, format, hak, CTA, słowa kluczowe SEO, szacunkowy czas produkcji. Notion template + CSV + Google Sheets. Wersja polska z polskich świąt i wydarzeń.",
                    "features_pool": [
                        "Notion database z widokami: Kalendarz, Kanban, Tabela",
                        "CSV do importu w Buffer/Hootsuite/Later",
                        "polskie święta i wydarzenia branżowe",
                        "pillar content strategy (4 filary)",
                        "content repurposing map (1 temat → 5 formatów)"
                    ]
                }
            ]
        }
    }

    def __init__(self):
        self.niches_by_id = {n.id: n for n in config.niches}

    def generate_product_specs(self, niche_id: str, count: int = 1) -> List[ProductSpec]:
        """Generate product specifications for a given niche."""
        if niche_id not in self.PRODUCT_TEMPLATES:
            raise ValueError(f"Unknown niche: {niche_id}")
        
        niche = self.niches_by_id[niche_id]
        templates = self.PRODUCT_TEMPLATES[niche_id]["template"]
        specs = []
        
        for _ in range(count):
            # Pick random template
            tmpl = random.choice(templates)
            product_type = tmpl["type"]
            topic = random.choice(tmpl["topics"])
            title_pattern = random.choice(tmpl["title_patterns"])
            
            # Fill title
            title = title_pattern.format(
                topic=topic.title(),
                audience=niche.target_audience.split(",")[0].strip(),
                count=random.randint(50, 200)
            )
            
            # Build description
            features = random.sample(tmpl["features_pool"], k=min(4, len(tmpl["features_pool"])))
            description = tmpl["description_template"].format(
                topic=topic,
                features=", ".join(features[:-1]) + " oraz " + features[-1] if len(features) > 1 else features[0],
                audience=niche.target_audience,
                count=random.randint(50, 200),
                views=random.randint(5, 15)
            )
            
            # Price
            price_pln = random.choice(niche.price_range_pln)
            
            # Content generation prompt for AI
            content_prompt = self._build_content_prompt(niche, product_type, topic, features, title)
            
            # Tags & SEO
            tags = niche.tags + [product_type, topic.replace(" ", "-")]
            seo_keywords = niche.seo_keywords + [topic, f"{topic} polski", f"{topic} szablon"]
            
            spec = ProductSpec(
                niche_id=niche_id,
                product_type=product_type,
                title=title,
                description=description,
                tags=tags,
                seo_keywords=seo_keywords,
                price_pln=price_pln,
                content_prompt=content_prompt,
                metadata={
                    "template_used": tmpl["type"],
                    "topic": topic,
                    "generated_at": datetime.now().isoformat(),
                    "version": "1.0"
                }
            )
            specs.append(spec)
        
        return specs

    def _build_content_prompt(self, niche: NicheConfig, product_type: str, topic: str, features: List[str], title: str) -> str:
        """Build detailed prompt for AI to generate actual product content."""
        base = f"""Jesteś ekspertem ds. produktów cyfrowych dla polskich twórców. Stwórz kompletny, gotowy do sprzedaży produkt: "{title}".

Nisza: {niche.name}
Cel: {niche.target_audience}
Temat: {topic}
Typ produktu: {product_type}
Kluczowe cechy do uwzględnienia: {', '.join(features)}

Wymagania:
1. Język: 100% polski (naturalny, nieprzetłumaczony z angielskiego)
2. Format: Markdown (gotowy do konwersji do PDF/Notion)
3. Struktura: Tytuły H1/H2/H3, listy, tabele, bloki kodu gdzie potrzebne
4. Wartość: Klient musi móc użyć tego OD RAZU po zakupie – zero "dokończ sam"
5. Długość: kompleksowe (minimum 2000 słów dla pakietów, 500 dla cheatsheetów)
6. SEO: naturalne wplecenie słów kluczowych: {', '.join(niche.seo_keywords[:5])}

Zwróć TYLKO treść produktu w Markdown. Bez wstępu, bez "oto produkt", bez komentarzy."""
        return base

    def generate_all_niches(self, products_per_niche: int = 1) -> Dict[str, List[ProductSpec]]:
        """Generate products for all configured niches."""
        result = {}
        for niche in config.niches:
            result[niche.id] = self.generate_product_specs(niche.id, products_per_niche)
        return result


# CLI for testing
if __name__ == "__main__":
    gen = ProductGenerator()
    all_specs = gen.generate_all_niches(products_per_niche=2)
    for niche_id, specs in all_specs.items():
        print(f"\n=== {niche_id} ===")
        for s in specs:
            print(f"  - {s.title} ({s.product_type}) – {s.price_pln} PLN")
            print(f"    Tags: {', '.join(s.tags[:5])}...")