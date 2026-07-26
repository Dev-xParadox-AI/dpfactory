"""
Digital Product Factory - Cloudflare Workers Entry Point
Runs the factory pipeline on Cloudflare Workers scheduled triggers.
"""
import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config_loader import load_config
from src.scheduler.factory_scheduler import FactoryScheduler, RunReport

# Configure logging for Workers
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger("dpfactory.worker")


def handler(request, env, ctx):
    """
    Cloudflare Workers entry point.
    Called by cron triggers (0 4 * * * and 0 16 * * *).
    """
    # Load config (can be from KV or bundled)
    config = load_config()
    
    # Parse environment
    dry_run = env.FACTORY_DRY_RUN == "true" if hasattr(env, "FACTORY_DRY_RUN") else False
    log_level = getattr(env, "LOG_LEVEL", "INFO")
    logger.setLevel(log_level)
    
    logger.info(f"🏭 Factory worker triggered | Dry run: {dry_run}")
    
    # Run factory
    scheduler = FactoryScheduler(dry_run=dry_run)
    
    # Optionally filter niches from request (for manual triggers)
    niche_ids = None
    if request.method == "POST":
        try:
            body = request.json()
            niche_ids = body.get("niches")
        except Exception:
            pass
    
    report = scheduler.run(niche_ids=niche_ids)
    
    # Store report in KV if available
    if hasattr(env, "FACTORY_STATE"):
        report_key = f"run_{report.run_id}"
        env.FACTORY_STATE.put(report_key, json.dumps(report.__dict__))
        logger.info(f"Report stored in KV: {report_key}")
    
    # Store products in R2 if available
    if hasattr(env, "PRODUCTS_BUCKET"):
        products_dir = Path("products")
        if products_dir.exists():
            for product_file in products_dir.rglob("*.zip"):
                key = f"{report.run_id}/{product_file.name}"
                with open(product_file, "rb") as f:
                    env.PRODUCTS_BUCKET.put(key, f.read())
            logger.info(f"Products uploaded to R2 bucket")
    
    # Return response
    return {
        "status": "success" if report.products_failed == 0 else "partial_failure",
        "run_id": report.run_id,
        "products_generated": report.products_generated,
        "products_published": report.products_published,
        "products_failed": report.products_failed,
        "details": report.details
    }


# For local testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--niches", nargs="+")
    parser.add_argument("--count", type=int, default=3)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    
    # Mock env
    class MockEnv:
        FACTORY_DRY_RUN = str(args.dry_run).lower()
        LOG_LEVEL = "DEBUG"
    
    class MockRequest:
        method = "GET"
        def json(self): return {}
    
    result = handler(MockRequest(), MockEnv(), None)
    print(json.dumps(result, indent=2, ensure_ascii=False))