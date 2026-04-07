"""
Autonomous Wisdom Crawler — Main Runner

Runs as a persistent background worker:
1. Discovers wisdom from multiple sources (web search, Gutenberg, Wikipedia)
2. Evaluates candidates using LLM (quality, flourishing scores, divisiveness check)
3. Deduplicates against existing corpus
4. Ingests approved wisdom into the database
5. Logs everything for monitoring

Deploy as a separate Render Background Worker or run standalone.
"""

import asyncio
import logging
import signal
import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.models.wisdom import Base
from src.models.crawl_log import CrawlRun, CrawlCandidate
from src.crawler.config import CrawlerSettings
from src.crawler.sources.web_search import WebSearchSource
from src.crawler.sources.gutenberg import GutenbergSource
from src.crawler.sources.wikipedia import WikipediaSource
from src.crawler.pipeline.evaluator import WisdomEvaluator
from src.crawler.pipeline.ingestor import WisdomIngestor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("wisdom_crawler")


class WisdomCrawler:
    """The autonomous wisdom crawler orchestrator."""

    def __init__(self, settings: CrawlerSettings | None = None):
        self.settings = settings or CrawlerSettings()
        self.engine = create_async_engine(self.settings.database_url, pool_size=5)
        self.session_factory = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        self._shutdown = False

        # Sources
        self.sources = [
            WebSearchSource(),
            GutenbergSource(),
            WikipediaSource(),
        ]

        # Pipeline
        self.evaluator = WisdomEvaluator(self.settings)

    async def setup(self):
        """Initialize database tables."""
        from src.models.crawl_log import CrawlRun, CrawlCandidate
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables verified")

    async def run_once(self) -> dict:
        """Run a single crawl cycle. Returns stats dict."""
        run_id = uuid.uuid4()
        stats = {
            "run_id": str(run_id),
            "discovered": 0,
            "evaluated": 0,
            "approved": 0,
            "rejected": 0,
            "duplicates": 0,
            "ingested": 0,
            "sources": [],
            "errors": [],
        }

        async with self.session_factory() as session:
            # Log the crawl run
            crawl_run = CrawlRun(
                id=run_id,
                started_at=datetime.utcnow(),
                status="running",
                sources_used=[],
            )
            session.add(crawl_run)
            await session.flush()

            try:
                # Phase 1: Discovery
                logger.info("=" * 60)
                logger.info("PHASE 1: DISCOVERY")
                logger.info("=" * 60)

                all_candidates = []
                for source in self.sources:
                    if self._shutdown:
                        break
                    try:
                        logger.info(f"Crawling source: {source.name}")
                        candidates = await source.discover()
                        all_candidates.extend(candidates)
                        stats["sources"].append(source.name)
                        logger.info(f"  {source.name}: {len(candidates)} candidates")
                    except Exception as e:
                        logger.error(f"Source {source.name} failed: {e}")
                        stats["errors"].append(f"{source.name}: {str(e)}")

                stats["discovered"] = len(all_candidates)

                # Cap candidates per run
                if len(all_candidates) > self.settings.max_candidates_per_run:
                    import random
                    all_candidates = random.sample(all_candidates, self.settings.max_candidates_per_run)
                    logger.info(f"Capped to {self.settings.max_candidates_per_run} candidates")

                # Log candidates
                for candidate in all_candidates:
                    cc = CrawlCandidate(
                        id=uuid.uuid4(),
                        crawl_run_id=run_id,
                        source_text=candidate.source_text[:5000],
                        source_url=candidate.source_url,
                        crawl_source=candidate.crawl_source,
                        status="pending",
                    )
                    session.add(cc)
                await session.flush()

                if not all_candidates:
                    logger.info("No candidates discovered, ending cycle")
                    crawl_run.status = "completed"
                    crawl_run.finished_at = datetime.utcnow()
                    await session.commit()
                    return stats

                # Phase 2: Evaluation
                logger.info("=" * 60)
                logger.info(f"PHASE 2: EVALUATION ({len(all_candidates)} candidates)")
                logger.info("=" * 60)

                approved = await self.evaluator.evaluate_batch(all_candidates)
                stats["evaluated"] = len(all_candidates)
                stats["approved"] = len(approved)
                stats["rejected"] = len(all_candidates) - len(approved)

                logger.info(f"Evaluation: {len(approved)}/{len(all_candidates)} approved")

                if not approved:
                    logger.info("No candidates approved, ending cycle")
                    crawl_run.status = "completed"
                    crawl_run.finished_at = datetime.utcnow()
                    crawl_run.candidates_discovered = stats["discovered"]
                    crawl_run.candidates_evaluated = stats["evaluated"]
                    crawl_run.candidates_rejected = stats["rejected"]
                    await session.commit()
                    return stats

                # Phase 3: Ingestion
                logger.info("=" * 60)
                logger.info(f"PHASE 3: INGESTION ({len(approved)} approved)")
                logger.info("=" * 60)

                ingestor = WisdomIngestor(session, self.settings.dedup_similarity_threshold)
                entries = await ingestor.ingest_batch(approved)
                stats["ingested"] = len(entries)
                stats["duplicates"] = len(approved) - len(entries)

                logger.info(f"Ingested {len(entries)} new entries ({len(approved) - len(entries)} duplicates)")

                # Update crawl run
                crawl_run.status = "completed"
                crawl_run.finished_at = datetime.utcnow()
                crawl_run.candidates_discovered = stats["discovered"]
                crawl_run.candidates_evaluated = stats["evaluated"]
                crawl_run.candidates_approved = stats["approved"]
                crawl_run.candidates_rejected = stats["rejected"]
                crawl_run.candidates_duplicate = stats["duplicates"]
                crawl_run.entries_ingested = stats["ingested"]
                crawl_run.sources_used = stats["sources"]
                await session.commit()

            except Exception as e:
                logger.error(f"Crawl cycle failed: {e}")
                crawl_run.status = "failed"
                crawl_run.error_message = str(e)
                crawl_run.finished_at = datetime.utcnow()
                await session.commit()
                stats["errors"].append(str(e))

        return stats

    async def run_forever(self):
        """Run the crawler in a continuous loop."""
        await self.setup()

        logger.info("=" * 60)
        logger.info("WISDOM SPARK CRAWLER — STARTING")
        logger.info(f"Interval: {self.settings.crawl_interval_minutes} minutes")
        logger.info(f"Max candidates per run: {self.settings.max_candidates_per_run}")
        logger.info(f"Min flourishing score: {self.settings.min_flourishing_score}")
        logger.info(f"Sources: {[s.name for s in self.sources]}")
        logger.info("=" * 60)

        cycle = 0
        while not self._shutdown:
            cycle += 1
            logger.info(f"\n{'=' * 60}")
            logger.info(f"CRAWL CYCLE #{cycle}")
            logger.info(f"{'=' * 60}\n")

            try:
                stats = await self.run_once()
                logger.info(f"\nCycle #{cycle} complete: "
                            f"discovered={stats['discovered']}, "
                            f"evaluated={stats['evaluated']}, "
                            f"approved={stats['approved']}, "
                            f"ingested={stats['ingested']}, "
                            f"duplicates={stats['duplicates']}")
            except Exception as e:
                logger.error(f"Cycle #{cycle} failed: {e}")

            if self._shutdown:
                break

            logger.info(f"Sleeping {self.settings.crawl_interval_minutes} minutes until next cycle...")
            try:
                await asyncio.sleep(self.settings.crawl_interval_minutes * 60)
            except asyncio.CancelledError:
                break

        logger.info("Crawler shutting down gracefully")
        await self.cleanup()

    async def cleanup(self):
        """Clean up resources."""
        for source in self.sources:
            if hasattr(source, 'close'):
                await source.close()
        await self.evaluator.close()
        await self.engine.dispose()

    def shutdown(self):
        """Signal the crawler to stop after the current cycle."""
        logger.info("Shutdown signal received")
        self._shutdown = True


async def main():
    """Entry point for the crawler worker."""
    settings = CrawlerSettings()
    crawler = WisdomCrawler(settings)

    # Handle graceful shutdown
    loop = asyncio.get_event_loop()

    def signal_handler():
        crawler.shutdown()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    await crawler.run_forever()


if __name__ == "__main__":
    asyncio.run(main())
