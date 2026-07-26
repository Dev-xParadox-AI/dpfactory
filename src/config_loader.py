"""
Digital Product Factory - Core Configuration Loader
"""
import os
import yaml
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Dict, Any


@dataclass
class NicheConfig:
    id: str
    name: str
    tags: List[str]
    target_audience: str
    product_types: List[str]
    price_range_pln: List[int]
    seo_keywords: List[str]


@dataclass
class GumroadConfig:
    api_base: str
    access_token: str
    application_id: str
    default_visibility: str
    default_license: str


@dataclass
class AIConfig:
    provider: str
    models: Dict[str, str]
    temperature: float
    max_tokens: int


@dataclass
class FactoryConfig:
    name: str
    timezone: str
    language: str
    currency: str
    default_price_pln: int
    products_per_run: int
    runs_per_day: int
    niches: List[NicheConfig]
    gumroad: GumroadConfig
    ai: AIConfig
    packaging: Dict[str, Any]
    schedule: Dict[str, Any]
    monitoring: Dict[str, Any]
    hosting: Dict[str, Any]


def load_config(config_path: Optional[str] = None) -> FactoryConfig:
    """Load configuration from YAML file."""
    if config_path is None:
        config_path = os.environ.get(
            "DPF_CONFIG_PATH",
            str(Path(__file__).parent.parent / "config" / "settings.yaml")
        )
    
    with open(config_path, 'r', encoding='utf-8') as f:
        raw = yaml.safe_load(f)
    
    # Resolve secrets from environment
    gumroad_token = os.environ.get("GUMROAD_ACCESS_TOKEN", "")
    gumroad_app_id = os.environ.get("GUMROAD_APPLICATION_ID", "")
    
    niches = [
        NicheConfig(
            id=n["id"],
            name=n["name"],
            tags=n["tags"],
            target_audience=n["target_audience"],
            product_types=n["product_types"],
            price_range_pln=n["price_range_pln"],
            seo_keywords=n["seo_keywords"]
        )
        for n in raw["niches"]
    ]
    
    return FactoryConfig(
        name=raw["factory"]["name"],
        timezone=raw["factory"]["timezone"],
        language=raw["factory"]["language"],
        currency=raw["factory"]["currency"],
        default_price_pln=raw["factory"]["default_price_pln"],
        products_per_run=raw["factory"]["products_per_run"],
        runs_per_day=raw["factory"]["runs_per_day"],
        niches=niches,
        gumroad=GumroadConfig(
            api_base=raw["gumroad"]["api_base"],
            access_token=gumroad_token,
            application_id=gumroad_app_id,
            default_visibility=raw["gumroad"]["default_visibility"],
            default_license=raw["gumroad"]["default_license"]
        ),
        ai=AIConfig(
            provider=raw["ai"]["provider"],
            models=raw["ai"]["models"],
            temperature=raw["ai"]["temperature"],
            max_tokens=raw["ai"]["max_tokens"]
        ),
        packaging=raw["packaging"],
        schedule=raw["schedule"],
        monitoring=raw["monitoring"],
        hosting=raw["hosting"]
    )


# Global config instance
config = load_config()