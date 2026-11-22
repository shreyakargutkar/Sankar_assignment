from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, asc
from app.models.influencer import Influencer, LeadStatus
from app.schemas.influencer import InfluencerCreate, InfluencerUpdate
from app.core.logging import logger

class InfluencerService:
    def create_influencer(self, db: Session, influencer_in: InfluencerCreate) -> Tuple[Optional[Influencer], bool]:
        """
        Creates an influencer while preventing duplicates by username or profile URL.
        Returns (Influencer, is_created).
        """
        clean_username = influencer_in.instagram_username.lstrip("@").strip().lower()
        clean_url = influencer_in.profile_url.strip().rstrip("/").lower() if influencer_in.profile_url else f"https://instagram.com/{clean_username}"

        # Duplicate check
        existing = db.query(Influencer).filter(
            or_(
                Influencer.instagram_username.ilike(clean_username),
                Influencer.profile_url.ilike(clean_url)
            )
        ).first()

        if existing:
            logger.info(f"Influencer @{clean_username} already exists (ID: {existing.id}). Skipping.")
            return existing, False

        # If email is present, set initial status to Email Available if default was New Lead
        status = influencer_in.status or LeadStatus.NEW_LEAD.value
        if influencer_in.email and status == LeadStatus.NEW_LEAD.value:
            status = LeadStatus.EMAIL_AVAILABLE.value

        db_obj = Influencer(
            name=influencer_in.name.strip(),
            instagram_username=clean_username,
            profile_url=clean_url,
            niche=influencer_in.niche.strip(),
            followers_count=influencer_in.followers_count,
            email=influencer_in.email.strip() if influencer_in.email else None,
            location=influencer_in.location.strip(),
            status=status
        )

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        logger.info(f"Created influencer @{clean_username} with ID {db_obj.id}")
        return db_obj, True

    def batch_create_influencers(self, db: Session, items: List[InfluencerCreate]) -> Dict[str, Any]:
        """
        Batch creates influencers with deduplication.
        Returns summary of created vs skipped items.
        """
        created = []
        skipped = []

        for item in items:
            obj, is_new = self.create_influencer(db, item)
            if is_new:
                created.append(obj)
            else:
                skipped.append(item.instagram_username)

        return {
            "total_processed": len(items),
            "created_count": len(created),
            "skipped_count": len(skipped),
            "created_influencers": created,
            "skipped_usernames": skipped
        }

    def get_influencer(self, db: Session, influencer_id: int) -> Optional[Influencer]:
        return db.query(Influencer).filter(Influencer.id == influencer_id).first()

    def get_influencers(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        niche: Optional[str] = None,
        status: Optional[str] = None,
        location: Optional[str] = None,
        min_followers: Optional[int] = None,
        max_followers: Optional[int] = None,
        min_score: Optional[int] = None,
        sort_by: Optional[str] = "created_at",
        sort_order: Optional[str] = "desc"
    ) -> Tuple[List[Influencer], int]:
        """
        Filter, search, sort, and paginate influencer leads.
        """
        query = db.query(Influencer)

        if search:
            search_term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Influencer.name.ilike(search_term),
                    Influencer.instagram_username.ilike(search_term),
                    Influencer.email.ilike(search_term),
                    Influencer.location.ilike(search_term),
                    Influencer.niche.ilike(search_term)
                )
            )

        if niche and niche.lower() != "all":
            query = query.filter(Influencer.niche.ilike(f"%{niche.strip()}%"))

        if status and status.lower() != "all":
            query = query.filter(Influencer.status == status)

        if location and location.lower() != "all":
            query = query.filter(Influencer.location.ilike(f"%{location.strip()}%"))

        if min_followers is not None:
            query = query.filter(Influencer.followers_count >= min_followers)

        if max_followers is not None:
            query = query.filter(Influencer.followers_count <= max_followers)

        if min_score is not None:
            query = query.filter(Influencer.suitability_score >= min_score)

        # Total count before pagination
        total = query.count()

        # Sorting
        sort_column = getattr(Influencer, sort_by, Influencer.created_at)
        if sort_order == "asc":
            query = query.order_by(asc(sort_column))
        else:
            query = query.order_by(desc(sort_column))

        items = query.offset(skip).limit(limit).all()
        return items, total

    def update_influencer(self, db: Session, influencer_id: int, update_data: InfluencerUpdate) -> Optional[Influencer]:
        obj = self.get_influencer(db, influencer_id)
        if not obj:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(obj, key, value)

        db.commit()
        db.refresh(obj)
        return obj

    def update_status(self, db: Session, influencer_id: int, new_status: str) -> Optional[Influencer]:
        obj = self.get_influencer(db, influencer_id)
        if not obj:
            return None
        obj.status = new_status
        db.commit()
        db.refresh(obj)
        return obj

    def delete_influencer(self, db: Session, influencer_id: int) -> bool:
        obj = self.get_influencer(db, influencer_id)
        if not obj:
            return False
        db.delete(obj)
        db.commit()
        return True

    def get_dashboard_stats(self, db: Session) -> Dict[str, Any]:
        """
        Calculates pipeline metrics for dashboard overview.
        """
        total = db.query(Influencer).count()
        analyzed = db.query(Influencer).filter(Influencer.suitability_score.isnot(None)).count()
        with_email = db.query(Influencer).filter(Influencer.email.isnot(None), Influencer.email != "").count()
        high_matches = db.query(Influencer).filter(Influencer.suitability_score >= 80).count()
        synced_sheets = db.query(Influencer).filter(Influencer.synced_to_sheets == True).count()

        # Breakdown by status
        statuses = [s.value for s in LeadStatus]
        status_counts = {}
        for s in statuses:
            status_counts[s] = db.query(Influencer).filter(Influencer.status == s).count()

        return {
            "total_leads": total,
            "ai_analyzed": analyzed,
            "emails_available": with_email,
            "high_suitability_matches": high_matches,
            "synced_to_sheets": synced_sheets,
            "status_breakdown": status_counts
        }

influencer_service = InfluencerService()

