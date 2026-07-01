"""任务实现模块

包含所有具体的定时任务实现：
- CrawlSiteTask: 站点爬取任务
- ComplaintPatrolTask: 客诉巡查任务
- ComplaintScoreSnapshotTask: 客诉绩效快照任务
- ComplaintKnowledgeGapTask: 知识缺口分析任务
"""

from app.scheduler.tasks.complaint_knowledge_gap import ComplaintKnowledgeGapTask
from app.scheduler.tasks.complaint_patrol import ComplaintPatrolTask
from app.scheduler.tasks.complaint_score_snapshot import ComplaintScoreSnapshotTask
from app.scheduler.tasks.crawl_site import CrawlSiteTask

__all__ = [
    "ComplaintKnowledgeGapTask",
    "ComplaintPatrolTask",
    "ComplaintScoreSnapshotTask",
    "CrawlSiteTask",
]
