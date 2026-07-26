#!/usr/bin/env python3
"""
Digital Product Factory - Local Test Runner
Runs a dry-run to verify the pipeline works end-to-end.
"""
import os
import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.scheduler.factory_scheduler import FactoryScheduler


def main():
    parser = argparse.ArgumentParser(description="Run Digital Product Factory locally")
    parser.add_argument("--niches", nargs="+", help="Niche IDs to process")
    parser.add_argument("--count", type=int, default=1, help="Products per niche")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Don't publish to Gumroad")
    parser.add_argument("--config", help="Config file path")
    
    args = parser.parse_args()
    
    if args.config:
        os.environ["DPF_CONFIG_PATH"] = args.config
    
    print("=" * 60)
    print("🏭 Digital Product Factory - Local Test Run")
    print("=" * 60)
    print(f"Dry run: {args.dry_run}")
    print(f"Products per niche: {args.count}")
    print(f"Niches: {args.niches or 'ALL'}")
    print("=" * 60)
    
    scheduler = FactoryScheduler(dry_run=args.dry_run)
    report = scheduler.run(niche_ids=args.niches, products_per_niche=args.count)
    
    print("\n" + "=" * 60)
    print("📊 FINAL REPORT")
    print("=" * 60)
    print(f"Run ID: {report.run_id}")
    print(f"Generated: {report.products_generated}")
    print(f"Packaged:  {report.products_packaged}")
    print(f"Published: {report.products_published}")
    print(f"Failed:    {report.products_failed}")
    
    if report.published_products:
        print("\nPublished products:")
        for p in report.published_products:
            print(f"  • {p['title']} ({p.get('url', 'dry-run')})")
    
    if report.errors:
        print(f"\nErrors ({len(report.errors)}):")
        for e in report.errors:
            print(f"  ❌ {e}")
    
    print("=" * 60)
    
    # Exit code for CI
    sys.exit(1 if report.products_failed > 0 and report.products_published == 0 else 0)


if __name__ == "__main__":
    main()