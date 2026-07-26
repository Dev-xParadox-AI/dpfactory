"""
Digital Product Factory - Gumroad Publisher
Publishes packaged products to Gumroad via API (free tier supported).
"""
import os
import json
import time
import requests
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import datetime

from src.config_loader import config
from src.packagers.product_packager import PackagedProduct
from src.generators.product_generator import ProductSpec


@dataclass
class PublishResult:
    success: bool
    product_id: Optional[str] = None
    product_url: Optional[str] = None
    error: Optional[str] = None
    gumroad_response: Optional[Dict[str, Any]] = None


class GumroadPublisher:
    """Publishes products to Gumroad via API."""
    
    def __init__(self):
        self.api_base = config.gumroad.api_base
        self.access_token = config.gumroad.access_token
        self.application_id = config.gumroad.application_id
        self.default_visibility = config.gumroad.default_visibility
        self.default_license = config.gumroad.default_license
        
        if not self.access_token:
            raise ValueError("GUMROAD_ACCESS_TOKEN not configured")
    
    def publish(self, packaged: PackagedProduct) -> PublishResult:
        """Publish a packaged product to Gumroad."""
        spec = packaged.spec
        
        # Step 1: Create product
        create_result = self._create_product(spec)
        if not create_result.success:
            return create_result
        
        product_id = create_result.product_id
        
        # Step 2: Upload files (ZIP as main file)
        upload_result = self._upload_files(product_id, packaged)
        if not upload_result.success:
            # Try to clean up draft product
            self._delete_product(product_id)
            return upload_result
        
        # Step 3: Update product details (price, description, etc.)
        update_result = self._update_product(product_id, spec)
        if not update_result.success:
            return update_result
        
        # Step 4: Publish (if not draft)
        if self.default_visibility == "public":
            publish_result = self._publish_product(product_id)
            if not publish_result.success:
                return publish_result
        
        return PublishResult(
            success=True,
            product_id=product_id,
            product_url=f"https://gumroad.com/l/{product_id}",
            gumroad_response={"product_id": product_id}
        )
    
    def _create_product(self, spec: ProductSpec) -> PublishResult:
        """Create product on Gumroad."""
        url = f"{self.api_base}/products"
        headers = self._auth_headers()
        
        # Build description with SEO
        description = self._build_description(spec)
        
        payload = {
            "name": spec.title,
            "description": description,
            "price": spec.price_pln * 100,  # Gumroad uses cents
            "currency": "PLN",
            "custom_permalink": self._generate_permalink(spec),
            "tags": ",".join(spec.tags[:10]),  # Gumroad limit
            "published": self.default_visibility == "public",
            "require_shipping": False,
            "file_limit": 0,  # unlimited downloads
            "subscription_interval": None,
            "offer_type": "fixed" if spec.price_pln > 0 else "pay_what_you_want",
            "minimum_price_cents": 0 if spec.price_pln == 0 else spec.price_pln * 100,
            "suggested_price_cents": spec.price_pln * 100 if spec.price_pln > 0 else 0
        }
        
        try:
            response = requests.post(url, headers=headers, data=payload, timeout=30)
            if response.status_code == 200:
                data = response.json()
                product = data.get("product", {})
                return PublishResult(
                    success=True,
                    product_id=product.get("id") or product.get("permalink"),
                    gumroad_response=data
                )
            else:
                return PublishResult(
                    success=False,
                    error=f"Create product failed: HTTP {response.status_code} - {response.text[:500]}"
                )
        except Exception as e:
            return PublishResult(success=False, error=f"Create product exception: {e}")
    
    def _upload_files(self, product_id: str, packaged: PackagedProduct) -> PublishResult:
        """Upload product files to Gumroad."""
        url = f"{self.api_base}/products/{product_id}/files"
        headers = self._auth_headers()
        
        zip_path = Path(packaged.zip_path)
        if not zip_path.exists():
            return PublishResult(success=False, error=f"ZIP file not found: {zip_path}")
        
        try:
            with open(zip_path, 'rb') as f:
                files = {"file": (zip_path.name, f, "application/zip")}
                payload = {"file_type": "main"}
                response = requests.post(url, headers=headers, data=payload, files=files, timeout=60)
            
            if response.status_code == 200:
                return PublishResult(success=True, gumroad_response=response.json())
            else:
                return PublishResult(
                    success=False,
                    error=f"Upload failed: HTTP {response.status_code} - {response.text[:500]}"
                )
        except Exception as e:
            return PublishResult(success=False, error=f"Upload exception: {e}")
    
    def _update_product(self, product_id: str, spec: ProductSpec) -> PublishResult:
        """Update product metadata."""
        url = f"{self.api_base}/products/{product_id}"
        headers = self._auth_headers()
        
        description = self._build_description(spec)
        
        payload = {
            "description": description,
            "tags": ",".join(spec.tags[:10]),
            "custom_permalink": self._generate_permalink(spec),
            "price": spec.price_pln * 100,
            "currency": "PLN",
            "offer_type": "fixed" if spec.price_pln > 0 else "pay_what_you_want",
            "minimum_price_cents": 0 if spec.price_pln == 0 else spec.price_pln * 100,
            "suggested_price_cents": spec.price_pln * 100 if spec.price_pln > 0 else 1900  # 19 PLN suggested
        }
        
        try:
            response = requests.put(url, headers=headers, data=payload, timeout=30)
            if response.status_code == 200:
                return PublishResult(success=True, gumroad_response=response.json())
            else:
                return PublishResult(
                    success=False,
                    error=f"Update failed: HTTP {response.status_code} - {response.text[:500]}"
                )
        except Exception as e:
            return PublishResult(success=False, error=f"Update exception: {e}")
    
    def _publish_product(self, product_id: str) -> PublishResult:
        """Publish product (make public)."""
        url = f"{self.api_base}/products/{product_id}/publish"
        headers = self._auth_headers()
        
        try:
            response = requests.post(url, headers=headers, timeout=30)
            if response.status_code == 200:
                return PublishResult(success=True, gumroad_response=response.json())
            else:
                return PublishResult(
                    success=False,
                    error=f"Publish failed: HTTP {response.status_code} - {response.text[:500]}"
                )
        except Exception as e:
            return PublishResult(success=False, error=f"Publish exception: {e}")
    
    def _delete_product(self, product_id: str) -> bool:
        """Delete a product (cleanup on failure)."""
        url = f"{self.api_base}/products/{product_id}"
        headers = self._auth_headers()
        try:
            response = requests.delete(url, headers=headers, timeout=30)
            return response.status_code == 200
        except Exception:
            return False
    
    def _auth_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "User-Agent": "DigitalProductFactory/1.0"
        }
    
    def _build_description(self, spec: ProductSpec) -> str:
        """Build rich Gumroad description with SEO."""
        features = spec.metadata.get('features', ['Gotowy produkt do immediatego uzycia'])
        features_md = "\n".join(f"✅ {f}" for f in features)
        tags_md = ", ".join(f"#{t.replace(' ', '')}" for t in spec.tags[:15])
        version = spec.metadata.get('version', '1.0')
        date_str = datetime.now().strftime('%Y-%m-%d')
        
        return f"""{spec.description}

---
## Co otrzymujesz:
{features_md}

## Formaty dostepne:
- 📄 **Markdown** – edytowalny w Obsidian, Notion, VS Code, kazdym edytorze
- 📕 **PDF** – gotowy do druku i czytania (jesli dostepny)
- 💾 **JSON** – dane strukturalne do automatyzacji (n8n, Make, Notion API)
- 📦 **ZIP** – cala paczka w jednym pliku

## Dla kogo:
{spec.target_audience}

## Tagi:
{tags_md}

## Licencja:
Uzytkowanie osobiste – mozesz uzywac, modyfikowac, budowac na tym w swoich projektach. Nie mozesz odsprzedawac ani rozpowszechniac.

---
*Produkt wygenerowany przez Digital Product Factory – automatyczna fabryka produktow cyfrowych dla tworcow PL.*
*Wersja: {version} | Data: {date_str}*
"""
    
    def _generate_permalink(self, spec: ProductSpec) -> str:
        """Generate URL-friendly permalink."""
        import re
        base = spec.niche_id.replace("_", "-") + "-" + spec.title.lower()
        base = re.sub(r'[^a-z0-9-]', '-', base)
        base = re.sub(r'-+', '-', base).strip('-')
        # Add timestamp suffix for uniqueness
        suffix = datetime.now().strftime("%m%d%H%M")
        return f"{base}-{suffix}"[:100]
    
    def list_products(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List existing products."""
        url = f"{self.api_base}/products"
        headers = self._auth_headers()
        params = {"limit": limit}
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            if response.status_code == 200:
                return response.json().get("products", [])
            return []
        except Exception:
            return []
    
    def get_sales(self, product_id: str = None, since: str = None) -> List[Dict[str, Any]]:
        """Get sales data."""
        url = f"{self.api_base}/sales"
        headers = self._auth_headers()
        params = {}
        if product_id:
            params["product_id"] = product_id
        if since:
            params["since"] = since
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            if response.status_code == 200:
                return response.json().get("sales", [])
            return []
        except Exception:
            return []


# CLI test
if __name__ == "__main__":
    # This will fail without credentials - just testing import
    try:
        pub = GumroadPublisher()
        print("GumroadPublisher initialized OK")
        print(f"API Base: {pub.api_base}")
    except ValueError as e:
        print(f"Expected error (no creds): {e}")