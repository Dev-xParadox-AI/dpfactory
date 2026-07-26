"""
Digital Product Factory - Product Packager
Packages generated content into PDF, JSON, ZIP formats ready for Gumroad.
"""
import os
import zipfile
import json
import shutil
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.config_loader import config
from src.generators.product_generator import ProductSpec


@dataclass
class PackagedProduct:
    """A fully packaged product ready for publishing."""
    spec: ProductSpec
    content_md: str
    pdf_path: Optional[str]
    json_path: Optional[str]
    zip_path: str
    metadata: Dict[str, Any]
    generated_at: str


class ProductPackager:
    """Packages product content into deliverable formats."""
    
    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = Path(output_dir or config.packaging.get("output_dir", "products"))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.pdf_engine = config.packaging.get("pdf", {}).get("engine", "weasyprint")
        self.templates_dir = Path(config.packaging.get("pdf", {}).get("template_dir", "templates/pdf"))
        self.license_template = config.packaging.get("zip", {}).get("license_template", "templates/licenses/personal_use.md")
    
    def package(self, spec: ProductSpec, content_md: str) -> PackagedProduct:
        """Package a product into all formats."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = self._sanitize_filename(spec.title)
        product_dir = self.output_dir / f"{spec.niche_id}_{safe_title}_{timestamp}"
        product_dir.mkdir(parents=True, exist_ok=True)
        
        # Save markdown source
        md_path = product_dir / "content.md"
        md_path.write_text(content_md, encoding="utf-8")
        
        # Generate PDF
        pdf_path = self._generate_pdf(content_md, spec, product_dir)
        
        # Generate JSON (structured data)
        json_path = self._generate_json(spec, content_md, product_dir)
        
        # Generate ZIP (delivery package)
        zip_path = self._generate_zip(spec, content_md, pdf_path, json_path, product_dir)
        
        # Metadata
        metadata = {
            "spec": asdict(spec),
            "files": {
                "markdown": "content.md",
                "pdf": Path(pdf_path).name if pdf_path else None,
                "json": Path(json_path).name if json_path else None,
                "zip": Path(zip_path).name
            },
            "generated_at": datetime.now().isoformat(),
            "factory_version": "1.0.0"
        }
        meta_path = product_dir / "metadata.json"
        meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        
        return PackagedProduct(
            spec=spec,
            content_md=content_md,
            pdf_path=pdf_path,
            json_path=json_path,
            zip_path=zip_path,
            metadata=metadata,
            generated_at=datetime.now().isoformat()
        )
    
    def _sanitize_filename(self, name: str) -> str:
        """Sanitize filename for cross-platform compatibility."""
        # Replace Polish chars
        pl_chars = {
            'ą': 'a', 'ć': 'c', 'ę': 'e', 'ł': 'l', 'ń': 'n',
            'ó': 'o', 'ś': 's', 'ź': 'z', 'ż': 'z',
            'Ą': 'A', 'Ć': 'C', 'Ę': 'E', 'Ł': 'L', 'Ń': 'N',
            'Ó': 'O', 'Ś': 'S', 'Ź': 'Z', 'Ż': 'Z'
        }
        for pl, en in pl_chars.items():
            name = name.replace(pl, en)
        # Remove unsafe chars
        unsafe = '<>:"/\\|?*'
        for c in unsafe:
            name = name.replace(c, '-')
        # Collapse spaces and dashes
        name = '-'.join(name.split())
        return name[:100]
    
    def _generate_pdf(self, content_md: str, spec: ProductSpec, product_dir: Path) -> Optional[str]:
        """Generate PDF from markdown using weasyprint."""
        try:
            from weasyprint import HTML, CSS
            from weasyprint.text.fonts import FontConfiguration
            
            # Load template
            template_path = self.templates_dir / "product_template.html"
            if template_path.exists():
                template = template_path.read_text(encoding="utf-8")
            else:
                template = self._default_html_template()
            
            # Convert markdown to HTML
            import markdown
            html_content = markdown.markdown(
                content_md,
                extensions=['tables', 'fenced_code', 'codehilite', 'toc', 'meta']
            )
            
            # Inject into template
            full_html = template.replace("{{TITLE}}", spec.title)\
                                .replace("{{CONTENT}}", html_content)\
                                .replace("{{NICHE}}", spec.niche_id)\
                                .replace("{{DATE}}", datetime.now().strftime("%d.%m.%Y"))\
                                .replace("{{TAGS}}", ", ".join(spec.tags))\
                                .replace("{{PRICE}}", f"{spec.price_pln} PLN" if spec.price_pln > 0 else "Zapłać ile chcesz (0 PLN+)")
            
            # Generate PDF
            pdf_path = product_dir / "product.pdf"
            font_config = FontConfiguration()
            HTML(string=full_html).write_pdf(
                str(pdf_path),
                font_config=font_config,
                stylesheets=[CSS(string=self._pdf_styles())]
            )
            return str(pdf_path)
        except ImportError:
            print("WeasyPrint not installed, skipping PDF generation")
            return None
        except Exception as e:
            print(f"PDF generation failed: {e}")
            return None
    
    def _default_html_template(self) -> str:
        return """<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <title>{{TITLE}}</title>
    <style>{{STYLES}}</style>
</head>
<body>
    <header class="cover">
        <h1>{{TITLE}}</h1>
        <p class="subtitle">{{NICHE}} | {{DATE}}</p>
        <p class="price">{{PRICE}}</p>
    </header>
    <main>{{CONTENT}}</main>
    <footer>
        <p>Wygenerowane automatycznie przez Digital Product Factory | {DATE}</p>
    </footer>
</body>
</html>"""
    
    def _pdf_styles(self) -> str:
        return """
        @page { size: A4; margin: 2.5cm; @bottom-center { content: counter(page); font-size: 10pt; color: #666; } }
        body { font-family: 'DejaVu Sans', 'Arial', sans-serif; line-height: 1.6; color: #1a1a1a; }
        .cover { text-align: center; padding: 3rem 0; border-bottom: 3px solid #2563eb; margin-bottom: 2rem; page-break-after: always; }
        .cover h1 { font-size: 2.5rem; color: #1e293b; margin-bottom: 0.5rem; }
        .subtitle { font-size: 1.1rem; color: #64748b; }
        .price { font-size: 1.3rem; font-weight: 600; color: #2563eb; margin-top: 1rem; }
        h1, h2, h3 { color: #1e293b; page-break-after: avoid; }
        h1 { font-size: 2rem; border-bottom: 2px solid #e2e8f0; padding-bottom: 0.5rem; }
        h2 { font-size: 1.5rem; margin-top: 2rem; }
        h3 { font-size: 1.25rem; }
        code { background: #f1f5f9; padding: 0.15rem 0.4rem; border-radius: 4px; font-family: 'JetBrains Mono', monospace; font-size: 0.9em; }
        pre { background: #0f172a; color: #e2e8f0; padding: 1rem; border-radius: 8px; overflow-x: auto; page-break-inside: avoid; }
        pre code { background: none; padding: 0; color: inherit; }
        table { width: 100%; border-collapse: collapse; margin: 1rem 0; page-break-inside: avoid; }
        th, td { border: 1px solid #e2e8f0; padding: 0.75rem; text-align: left; }
        th { background: #f8fafc; font-weight: 600; }
        blockquote { border-left: 4px solid #2563eb; padding-left: 1rem; margin: 1rem 0; color: #475569; font-style: italic; }
        ul, ol { padding-left: 1.5rem; }
        li { margin: 0.25rem 0; }
        footer { margin-top: 3rem; padding-top: 1rem; border-top: 1px solid #e2e8f0; text-align: center; color: #94a3b8; font-size: 0.85rem; }
        .toc { page-break-after: always; }
        .toc ul { list-style: none; padding-left: 0; }
        .toc li { padding: 0.25rem 0; border-bottom: 1px dotted #e2e8f0; }
        """
    
    def _generate_json(self, spec: ProductSpec, content_md: str, product_dir: Path) -> str:
        """Generate structured JSON version of the product."""
        json_data = {
            "product": {
                "id": f"{spec.niche_id}_{self._sanitize_filename(spec.title)}",
                "title": spec.title,
                "description": spec.description,
                "niche": spec.niche_id,
                "type": spec.product_type,
                "tags": spec.tags,
                "seo_keywords": spec.seo_keywords,
                "price_pln": spec.price_pln,
                "license": "personal_use",
                "language": "pl"
            },
            "content": {
                "markdown": content_md,
                "word_count": len(content_md.split()),
                "char_count": len(content_md)
            },
            "metadata": spec.metadata,
            "generated_at": datetime.now().isoformat()
        }
        json_path = product_dir / "product.json"
        json_path.write_text(json.dumps(json_data, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(json_path)
    
    def _generate_zip(self, spec: ProductSpec, content_md: str, pdf_path: Optional[str], 
                      json_path: Optional[str], product_dir: Path) -> str:
        """Create delivery ZIP package."""
        zip_name = f"{spec.niche_id}_{self._sanitize_filename(spec.title)}.zip"
        zip_path = self.output_dir / zip_name
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            # Main content
            zf.writestr("README.md", self._generate_readme(spec))
            zf.writestr("content.md", content_md)
            zf.writestr("product.json", Path(json_path).read_text(encoding="utf-8") if json_path else "{}")
            
            # PDF if exists
            if pdf_path and Path(pdf_path).exists():
                zf.write(pdf_path, "product.pdf")
            
            # License
            license_text = self._generate_license(spec)
            zf.writestr("LICENSE.md", license_text)
            
            # Bonus: prompt used for generation (value add)
            zf.writestr("GENERATION_PROMPT.md", spec.content_prompt)
        
        return str(zip_path)
    
    def _generate_readme(self, spec: ProductSpec) -> str:
        return f"""# {spec.title}

**Nisza:** {spec.niche_id}  
**Typ:** {spec.product_type}  
**Cena:** {spec.price_pln} PLN {"(Zapłać ile chcesz)" if spec.price_pln == 0 else ""}  
**Licencja:** Użytkowanie osobiste  
**Język:** Polski  

## Zawartość paczki
- `content.md` – Pełna treść w Markdown (możesz edytować w Obsidian/Notion/VS Code)
- `product.pdf` – Gotowy do wydruku/czytania PDF (jeśli dostępny)
- `product.json` – Dane strukturalne (dla deweloperów/automatyzacji)
- `LICENSE.md` – Licencja użytkowania osobistego
- `GENERATION_PROMPT.md` – Prompt użyty do wygenerowania (bonus: naucz się promptować)

## Jak używać
1. Otwórz `content.md` w dowolnym edytorze Markdown (Obsidian, Notion, VS Code, Typora)
2. Dostosuj do swoich potrzeb – to Twój produkt do użytku osobistego
3. `product.json` możesz zaimportować do Notion/Airtable/n8n

## Tagi
{', '.join(f'`{t}`' for t in spec.tags)}

## Słowa kluczowe SEO
{', '.join(f'`{k}`' for k in spec.seo_keywords)}

---
*Wygenerowane automatycznie przez Digital Product Factory v1.0*
*Data: {datetime.now().strftime('%Y-%m-%d %H:%M')}*
"""
    
    def _generate_license(self, spec: ProductSpec) -> str:
        return f"""# Licencja Użytkowania Osobistego

**Produkt:** {spec.title}  
**Nisza:** {spec.niche_id}  
**Data zakupu:** {{PURCHASE_DATE}}  
**ID zamówienia:** {{ORDER_ID}}

## Co możesz:
✅ Używać produktu do celów osobistych, edukacyjnych i komercyjnych we własnej działalności  
✅ Modyfikować, dostosowywać i rozbudowywać treść  
✅ Używać fragmentów w swoich materiałach marketingowych, lead magnetach, kursach  
✅ Przechowywać w narzędziach: Notion, Obsidian, Google Drive, GitHub (prywatne repo)

## Czego NIE możesz:
❌ Sprzedawać, dystrybuować, udostępniać lub przesyłać produktu innym osobom  
❌ Publikować produktu (całości lub fragmentów >10%) publicznie w Internecie  
❌ Tworzyć na jego podstawie produkty konkurencyjne do odsprzedaży  
❌ Używać nazwy "Digital Product Factory" lub suggerować autorskie powiązanie

## Ważne
Ten produkt został wygenerowany przez system AI (Digital Product Factory). 
Autor nie ponosi odpowiedzialności za dokładność, kompletność lub przydatność treści.
Używasz na własne ryzyko. Brak gwarancji jakiejkolwiek – ani wyraźnej, ani domniemanej.

## Kontakt
Pytania? Sprawdź profil Gumroad sprzedawcy lub napisz do supportu Gumroad.

---
*Licencja przypisana do konkretnego nabywcy. Naruszenie = odwołanie licencji.*
"""


# CLI test
if __name__ == "__main__":
    from src.generators.product_generator import ProductGenerator
    
    gen = ProductGenerator()
    specs = gen.generate_product_specs("notion-templates-pl", 1)
    spec = specs[0]
    
    packager = ProductPackager()
    # Mock content
    content = f"# {spec.title}\n\nTo jest testowa treść produktu.\n\n## Rozdział 1\nTreść...\n\n## Rozdział 2\nWięcej treści."
    
    packaged = packager.package(spec, content)
    print(f"Packaged: {packaged.zip_path}")
    print(f"PDF: {packaged.pdf_path}")
    print(f"JSON: {packaged.json_path}")