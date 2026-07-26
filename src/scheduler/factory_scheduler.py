"""
Digital Product Factory - Factory Scheduler
Orchestrates the full pipeline: generate -> package -> publish.
Runs via GitHub Actions cron or Cloudflare Workers scheduled trigger.
"""
import os
import sys
import json
import logging
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config_loader import config, load_config
from src.generators.product_generator import ProductGenerator, ProductSpec
from src.generators.ai_content_generator import AIContentGenerator, GenerationResult
from src.packagers.product_packager import ProductPackager, PackagedProduct
from src.publishers.gumroad_publisher import GumroadPublisher, PublishResult


# Configure logging
# Ensure log directories exist before creating FileHandler
Path("logs").mkdir(exist_ok=True)
Path("logs/runs").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/factory.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("factory_scheduler")


@dataclass
class RunReport:
    """Report for a single factory run."""
    run_id: str
    started_at: str
    finished_at: Optional[str] = None
    niches_processed: List[str] = None
    products_generated: int = 0
    products_packaged: int = 0
    products_published: int = 0
    products_failed: int = 0
    published_products: List[Dict[str, Any]] = None
    details: List[Dict[str, Any]] = None
    errors: List[str] = None
    
    def __post_init__(self):
        if self.niches_processed is None:
            self.niches_processed = []
        if self.published_products is None:
            self.published_products = []
        if self.details is None:
            self.details = []
        if self.errors is None:
            self.errors = []


class FactoryScheduler:
    """Main orchestrator for the Digital Product Factory."""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.generator = ProductGenerator()
        self.ai_generator = AIContentGenerator()
        self.packager = ProductPackager()
        self.publisher = None if dry_run else GumroadPublisher()
        self.report = None
    
    def run(
        self,
        niche_ids: Optional[List[str]] = None,
        products_per_niche: int = None
    ) -> RunReport:
        """Run the factory pipeline."""
        run_id = f"factory_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.report = RunReport(
            run_id=run_id,
            started_at=datetime.now().isoformat()
        )
        
        logger.info(f"🏭 Starting factory run: {run_id}")
        logger.info(f"   Dry run: {self.dry_run}")
        
        # Determine niches to process
        if niche_ids:
            niches_to_process = [n for n in config.niches if n.id in niche_ids]
        else:
            niches_to_process = config.niches
        
        products_per_niche = products_per_niche or config.products_per_run
        
        logger.info(f"   Niches: {[n.id for n in niches_to_process]}")
        logger.info(f"   Products per niche: {products_per_niche}")
        
        for niche in niches_to_process:
            try:
                self._process_niche(niche.id, products_per_niche)
                self.report.niches_processed.append(niche.id)
            except Exception as e:
                error_msg = f"Niche {niche.id} failed: {e}"
                logger.error(error_msg)
                self.report.errors.append(error_msg)
        
        self.report.finished_at = datetime.now().isoformat()
        self._save_report()
        self._log_summary()
        
        return self.report
    
    def _process_niche(self, niche_id: str, count: int):
        """Process a single niche: generate -> package -> publish."""
        logger.info(f"📦 Processing niche: {niche_id} ({count} products)")
        
        # 1. Generate product specs
        specs = self.generator.generate_product_specs(niche_id, count)
        logger.info(f"   Generated {len(specs)} product specs")
        
        for i, spec in enumerate(specs, 1):
            product_detail = {
                "niche": niche_id,
                "title": spec.title,
                "type": spec.product_type,
                "price_pln": spec.price_pln,
                "status": "pending"
            }
            
            try:
                logger.info(f"   [{i}/{len(specs)}] {spec.title}")
                
                # 2. Generate content with AI
                logger.debug(f"      Generating content with AI...")
                ai_result = self.ai_generator.generate_with_retry(spec.content_prompt)
                
                if not ai_result.success:
                    raise Exception(f"AI generation failed: {ai_result.error}")
                
                content_md = ai_result.content
                logger.debug(f"      Content generated: {len(content_md)} chars, {ai_result.tokens_used} tokens")
                
                product_detail["ai_model"] = ai_result.model_used
                product_detail["ai_tokens"] = ai_result.tokens_used
                product_detail["ai_latency_ms"] = ai_result.latency_ms
                
                # 3. Package product
                logger.debug(f"      Packaging...")
                packaged = self.packager.package(spec, content_md)
                logger.debug(f"      Packaged: {packaged.zip_path}")
                
                product_detail["zip_path"] = packaged.zip_path
                product_detail["pdf_path"] = packaged.pdf_path
                product_detail["status"] = "packaged"
                self.report.products_packaged += 1
                
                # 4. Publish to Gumroad (skip in dry run)
                if not self.dry_run and self.publisher:
                    logger.debug(f"      Publishing to Gumroad...")
                    publish_result = self.publisher.publish(packaged)
                    
                    if publish_result.success:
                        logger.info(f"      ✅ Published: {publish_result.product_url}")
                        product_detail["status"] = "published"
                        product_detail["product_id"] = publish_result.product_id
                        product_detail["product_url"] = publish_result.product_url
                        self.report.products_published += 1
                        self.report.published_products.append({
                            "niche": niche_id,
                            "title": spec.title,
                            "product_id": publish_result.product_id,
                            "url": publish_result.product_url,
                            "price_pln": spec.price_pln
                        })
                    else:
                        raise Exception(f"Publish failed: {publish_result.error}")
                else:
                    logger.info(f"      🔍 Dry run - would publish to Gumroad")
                    product_detail["status"] = "dry_run"
                    self.report.products_published += 1  # Count as success in dry run
                    self.report.published_products.append({
                        "niche": niche_id,
                        "title": spec.title,
                        "product_id": "dry-run",
                        "url": "dry-run",
                        "price_pln": spec.price_pln
                    })
                
                self.report.products_generated += 1
                product_detail["status"] = "success"
                
            except Exception as e:
                error_msg = f"Product '{spec.title}' failed: {e}"
                logger.error(f"      ❌ {error_msg}")
                product_detail["status"] = "failed"
                product_detail["error"] = str(e)
                self.report.products_failed += 1
                self.report.errors.append(error_msg)
            
            finally:
                self.report.details.append(product_detail)
    
    def _save_report(self):
        """Save run report to JSON."""
        report_dir = Path("logs/runs")
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / f"{self.report.run_id}.json"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(self.report), f, ensure_ascii=False, indent=2)
        
        logger.info(f"📊 Report saved: {report_path}")
    
    def _log_summary(self):
        """Log run summary."""
        duration = "N/A"
        if self.report.finished_at:
            start = datetime.fromisoformat(self.report.started_at)
            end = datetime.fromisoformat(self.report.finished_at)
            duration = str(end - start).split('.')[0]
        
        logger.info(f"""
🏭 FACTORY RUN COMPLETE: {self.report.run_id}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏱️  Duration: {duration}
📦 Niches processed: {len(self.report.niches_processed)}
✅ Products generated: {self.report.products_generated}
🚀 Products published: {self.report.products_published}
❌ Products failed: {self.report.products_failed}
📝 Niches: {', '.join(self.report.niches_processed) if self.report.niches_processed else 'none'}
        """)


def main():
    parser = argparse.ArgumentParser(description="Digital Product Factory Scheduler")
    parser.add_argument("--niches", nargs="+", help="Niche IDs to process (default: all)")
    parser.add_argument("--count", type=int, help="Products per niche (default: from config)")
    parser.add_argument("--dry-run", action="store_true", help="Run without publishing to Gumroad")
    parser.add_argument("--config", help="Path to config.yaml")
    
    args = parser.parse_args()
    
    # Load custom config if provided
    if args.config:
        load_config(args.config)
    
    # Ensure logs directory
    Path("logs").mkdir(exist_ok=True)
    Path("logs/runs").mkdir(exist_ok=True)
    
    # Run factory
    scheduler = FactoryScheduler(dry_run=args.dry_run)
    report = scheduler.run(
        niche_ids=args.niches,
        products_per_niche=args.count
    )
    
    # Exit code based on results
    if report.products_failed > 0 and report.products_published == 0:
        sys.exit(1)  # Total failure
    elif report.products_failed > 0:
        sys.exit(2)  # Partial failure
    else:
        sys.exit(0)  # Success


if __name__ == "__main__":
    main()