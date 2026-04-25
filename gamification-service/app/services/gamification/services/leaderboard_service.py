from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.gamification.models import Wallet
from app.services.gamification.schemas.leaderboard import LeaderboardItem


class LeaderboardService:
    """
    Leaderboard based ONLY on wallets.lifetime_earned (not ledger).

    Tie-break: higher lifetime_earned first; then user_id ASC for stable unique ordering.
    Rank is 1-indexed with that ordering.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _get_user_names(self, user_ids: list[UUID]) -> dict[str, str]:
        import httpx
        import os
        names = {}
        try:
            internal_token = os.getenv("INTERNAL_API_TOKEN", "")
            user_svc = os.getenv("USER_SERVICE_URL", "https://user-service-1095720168864-1095720168864.us-central1.run.app")
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{user_svc}/internal/users/names",
                    headers={"X-Internal-Token": internal_token},
                    timeout=2.0
                )
                if resp.status_code == 200:
                    names = resp.json()
        except Exception:
            pass
        return names

    async def get_top_users(self, *, limit: int = 50) -> list[LeaderboardItem]:
        limit = max(1, min(int(limit), 200))
        res = await self.session.execute(
            select(Wallet.user_id, Wallet.lifetime_earned)
            .order_by(Wallet.lifetime_earned.desc(), Wallet.user_id.asc())
            .limit(limit)
        )
        rows = res.all()
        user_ids = [r[0] for r in rows]
        names = await self._get_user_names(user_ids)
        
        return [
            LeaderboardItem(
                rank=i + 1, 
                user_id=uid, 
                user_name=names.get(str(uid), "Unknown User"),
                score=int(score)
            )
            for i, (uid, score) in enumerate(rows)
        ]

    async def get_user_rank(self, *, user_id: UUID) -> LeaderboardItem:
        me_res = await self.session.execute(
            select(Wallet.user_id, Wallet.lifetime_earned).where(Wallet.user_id == user_id)
        )
        me = me_res.first()
        if not me:
            my_score = 0
        else:
            my_score = int(me[1])

        higher_count_q = select(func.count()).select_from(Wallet).where(Wallet.lifetime_earned > my_score)
        higher = int((await self.session.execute(higher_count_q)).scalar_one())

        ties_before_q = select(func.count()).select_from(Wallet).where(
            and_(Wallet.lifetime_earned == my_score, Wallet.user_id < user_id)
        )
        ties_before = int((await self.session.execute(ties_before_q)).scalar_one())

        rank = higher + ties_before + 1
        names = await self._get_user_names([user_id])
        return LeaderboardItem(
            rank=rank, 
            user_id=user_id, 
            user_name=names.get(str(user_id), "Unknown User"),
            score=my_score
        )

    async def get_users_around(self, *, user_id: UUID, window: int = 5) -> list[LeaderboardItem]:
        window = max(1, min(int(window), 50))
        me = await self.get_user_rank(user_id=user_id)

        offset = max(0, me.rank - window - 1)
        limit = window * 2 + 1

        res = await self.session.execute(
            select(Wallet.user_id, Wallet.lifetime_earned)
            .order_by(Wallet.lifetime_earned.desc(), Wallet.user_id.asc())
            .offset(offset)
            .limit(limit)
        )
        rows = res.all()
        user_ids = [r[0] for r in rows]
        names = await self._get_user_names(user_ids)
        
        return [
            LeaderboardItem(
                rank=offset + i + 1, 
                user_id=uid, 
                user_name=names.get(str(uid), "Unknown User"),
                score=int(score)
            )
            for i, (uid, score) in enumerate(rows)
        ]

