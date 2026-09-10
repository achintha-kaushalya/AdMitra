import json
import logging
import os
from pathlib import Path
from typing import Dict, List

import chromadb
from chromadb.config import Settings


CHROMA_DIR = os.getenv("CHROMA_PERSIST_DIR", "./ir/chroma_db")
COLLECTION_NAME = "past_campaigns"

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _load_past_campaigns_json() -> List[Dict]:
    """Load historical campaign records from mock_data/past_campaigns.json."""

    base_dir = Path(__file__).resolve().parents[1]
    data_path = base_dir / "mock_data" / "past_campaigns.json"

    if not data_path.exists():
        logger.warning("past_campaigns.json not found at %s", data_path)
        return []

    try:
        return json.loads(data_path.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("Failed to read past_campaigns.json")
        return []


_CHROMA_CLIENT = None
_CHROMA_COLLECTION = None

def initialize_store():
    """
    Initialize and return the persistent ChromaDB collection.
    """
    global _CHROMA_CLIENT, _CHROMA_COLLECTION
    if _CHROMA_COLLECTION is not None:
        return _CHROMA_COLLECTION

    persist_dir = os.path.abspath(CHROMA_DIR)
    os.makedirs(persist_dir, exist_ok=True)

    settings = Settings(anonymized_telemetry=False)

    if _CHROMA_CLIENT is None:
        _CHROMA_CLIENT = chromadb.PersistentClient(
            path=persist_dir,
            settings=settings,
        )

    _CHROMA_COLLECTION = _CHROMA_CLIENT.get_or_create_collection(
        name=COLLECTION_NAME
    )

    return _CHROMA_COLLECTION


def seed_campaigns(collection) -> None:
    """
    Seed the ChromaDB collection with historical campaign data
    only when the collection is empty.
    """

    try:
        count = collection.count()
    except Exception:
        logger.exception("Unable to count records in ChromaDB collection")
        return

    if count > 0:
        logger.info(
            "Collection '%s' already contains %d records",
            COLLECTION_NAME,
            count,
        )
        return

    campaigns = _load_past_campaigns_json()

    if not campaigns:
        logger.warning("No historical campaigns available for seeding")
        return

    ids = []
    documents = []
    metadatas = []

    for campaign in campaigns:
        spend = float(campaign.get("spend", 0) or 0)
        roas = float(campaign.get("ROAS", 0) or 0)
        cpm = float(campaign.get("CPM", 0) or 0)
        ctr = float(campaign.get("CTR", 0) or 0)

        performance_tags = []

        if spend > 500:
            performance_tags.append("high spend")

        if roas < 1.0:
            performance_tags.append("low ROAS")

        if spend > 500 and roas < 1.0:
            performance_tags.append(
                "budget drain inefficient campaign"
            )

        if roas >= 3.0:
            performance_tags.append(
                "high ROAS successful campaign"
            )

        if spend <= 500 and roas >= 3.0:
            performance_tags.append(
                "small budget high ROAS winner"
            )

        if cpm >= 20:
            performance_tags.append("high CPM")

        if ctr < 0.5:
            performance_tags.append("low CTR")

        combined_text = (
            f"{campaign.get('outcome', '')} "
            f"{campaign.get('lesson', '')}"
        ).lower()

        if "fatigue" in combined_text:
            performance_tags.append("creative fatigue")

        document = (
            f"Campaign: {campaign.get('campaign_name', '')}. "
            f"Objective: {campaign.get('objective', '')}. "
            f"Audience: {campaign.get('audience', '')}. "
            f"Creative type: {campaign.get('creative_type', '')}. "
            f"CPM: {cpm}. "
            f"CTR: {ctr}. "
            f"ROAS: {roas}. "
            f"Spend: {spend}. "
            f"Performance tags: {', '.join(performance_tags)}. "
            f"Outcome: {campaign.get('outcome', '')}. "
            f"Lesson: {campaign.get('lesson', '')}"
        )

        metadata = {
            "id": campaign.get("id", ""),
            "campaign_name": campaign.get("campaign_name", ""),
            "objective": campaign.get("objective", ""),
            "audience": campaign.get("audience", ""),
            "creative_type": campaign.get("creative_type", ""),
            "CPM": cpm,
            "CTR": ctr,
            "ROAS": roas,
            "spend": spend,
            "outcome": campaign.get("outcome", ""),
            "lesson": campaign.get("lesson", ""),
        }

        ids.append(campaign["id"])
        documents.append(document)
        metadatas.append(metadata)

    try:
        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )

        logger.info(
            "Seeded %d campaigns into '%s'",
            len(campaigns),
            COLLECTION_NAME,
        )

    except Exception:
        logger.exception("Failed to seed ChromaDB collection")


def get_or_create_store():
    """
    Initialize the collection and seed historical campaigns if required.
    """

    collection = initialize_store()
    seed_campaigns(collection)

    return collection


def query_similar_campaigns(
    query_text: str,
    n: int = 3,
) -> List[Dict]:
    """
    Retrieve semantically similar historical campaigns and
    rerank them using metric-aware signals when appropriate.
    """

    if not isinstance(query_text, str) or not query_text.strip():
        return []

    collection = get_or_create_store()
    collection_size = collection.count()

    if collection_size == 0:
        return []

    query = query_text.strip().lower()

    # Retrieve a wider semantic candidate pool first.
    candidate_count = min(
        max(n * 4, 10),
        collection_size,
    )

    try:
        response = collection.query(
            query_texts=[query_text.strip()],
            n_results=candidate_count,
            include=[
                "metadatas",
                "documents",
                "distances",
            ],
        )

    except Exception:
        logger.exception("ChromaDB similarity query failed")
        return []

    results = []

    ids = response.get("ids", [[]])[0]
    metadatas = response.get("metadatas", [[]])[0]
    documents = response.get("documents", [[]])[0]
    distances = response.get("distances", [[]])[0]

    for index, campaign_id in enumerate(ids):
        metadata = (
            metadatas[index]
            if index < len(metadatas)
            else {}
        )

        document = (
            documents[index]
            if index < len(documents)
            else ""
        )

        distance = (
            distances[index]
            if index < len(distances)
            else None
        )

        # Lower ChromaDB distance means better semantic similarity.
        score = -(distance if distance is not None else 999)

        spend = float(metadata.get("spend", 0) or 0)
        roas = float(metadata.get("ROAS", 0) or 0)
        cpm = float(metadata.get("CPM", 0) or 0)
        ctr = float(metadata.get("CTR", 0) or 0)

        # Metric-aware reranking.
        if "high spend" in query and spend > 500:
            score += 2.0

        if "low roas" in query and roas < 1.0:
            score += 2.0

        if (
            ("budget drain" in query or "inefficient" in query)
            and spend > 500
            and roas < 1.0
        ):
            score += 3.0

        if "high roas" in query and roas >= 3.0:
            score += 2.0

        if (
            ("small budget" in query or "low spend" in query)
            and spend <= 500
        ):
            score += 2.0

        if "high cpm" in query and cpm >= 20:
            score += 2.0

        if "low ctr" in query and ctr < 0.5:
            score += 2.0

        combined_text = (
            f"{metadata.get('outcome', '')} "
            f"{metadata.get('lesson', '')}"
        ).lower()

        if (
            "creative fatigue" in query
            and "fatigue" in combined_text
        ):
            score += 3.0

        results.append(
            {
                "id": campaign_id,
                "metadata": metadata,
                "document": document,
                "distance": distance,
                "_ranking_score": score,
            }
        )

    # Higher reranking score is better.
    results.sort(
        key=lambda item: item["_ranking_score"],
        reverse=True,
    )

    final_results = results[:n]

    # Keep internal score hidden from callers.
    for result in final_results:
        result.pop("_ranking_score", None)

    return final_results


def sync_live_meta_campaigns() -> tuple[int, str]:
    """
    Enterprise Sync: Ingests all historical campaigns and insights from the connected 
    Meta Ad Account into ChromaDB vector memory for AI performance intelligence.
    """
    try:
        from shared.meta_api import fetch_all_historical_campaigns
        historical_camps = fetch_all_historical_campaigns(max_campaigns=100)
    except Exception as exc:
        return 0, f"Failed to connect to Meta API: {exc}"

    if not historical_camps:
        return 0, "No historical campaigns retrieved from Meta API"

    collection = initialize_store()
    ids = []
    documents = []
    metadatas = []

    for camp in historical_camps:
        camp_id = str(camp.get("id"))
        name = camp.get("name", "Campaign")
        spend = float(camp.get("spend", 0.0) or 0.0)
        cpm = float(camp.get("cpm", 0.0) or 0.0)
        ctr = float(camp.get("ctr", 0.0) or 0.0)
        roas = float(camp.get("roas", 0.0) or 0.0)
        status = camp.get("status", "PAUSED")
        objective = camp.get("objective", "OUTCOME_SALES")

        # Synthesize strategic lesson from performance
        if roas >= 3.0:
            outcome = "High Return Winner"
            lesson = f"Exceptional conversion efficiency at {roas:.2f}x ROAS. Maintain proven copy angle and creative format."
        elif ctr >= 2.0 and roas < 1.5:
            outcome = "High Engagement Low Conversion"
            lesson = f"Strong CTR ({ctr:.2f}%) but lower ROAS ({roas:.2f}x). Optimize checkout funnel and product landing page."
        elif cpm > 2.0:
            outcome = "High CPM Fatigue"
            lesson = f"Elevated CPM (${cpm:.2f}). Expand audience targeting and refresh visual hooks to lower auction costs."
        else:
            outcome = "Standard Delivery"
            lesson = f"Baseline campaign performance (CPM: ${cpm:.2f}, CTR: {ctr:.2f}%, Spend: ${spend:.2f})."

        doc = (
            f"Campaign name: {name}. "
            f"Objective: {objective}. "
            f"Status: {status}. "
            f"CPM: {cpm}. "
            f"CTR: {ctr}. "
            f"ROAS: {roas}. "
            f"Spend: {spend}. "
            f"Outcome: {outcome}. "
            f"Lesson: {lesson}"
        )

        meta = {
            "id": f"meta_{camp_id}",
            "campaign_name": name,
            "objective": objective,
            "status": status,
            "CPM": cpm,
            "CTR": ctr,
            "ROAS": roas,
            "spend": spend,
            "outcome": outcome,
            "lesson": lesson,
            "source": "meta_graph_api"
        }

        ids.append(f"meta_{camp_id}")
        documents.append(doc)
        metadatas.append(meta)

    try:
        # Upsert into ChromaDB
        collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        logger.info(f"Successfully ingested {len(ids)} Meta historical campaigns into ChromaDB")
        return len(ids), f"Successfully indexed {len(ids)} historical Meta campaigns into ChromaDB RAG memory!"
    except Exception as exc:
        logger.exception("Error syncing Meta campaigns to ChromaDB")
        return 0, f"ChromaDB upsert error: {exc}"


__all__ = [
    "initialize_store",
    "seed_campaigns",
    "query_similar_campaigns",
    "get_or_create_store",
    "sync_live_meta_campaigns",
]