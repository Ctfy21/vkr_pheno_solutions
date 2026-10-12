"""Loading of experiments together with their analysis runs, images and plants."""
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class StudyData:
    studies: List[dict] = field(default_factory=list)
    runs: List[dict] = field(default_factory=list)
    images: Dict[str, dict] = field(default_factory=dict)  # image id -> image doc
    plants: Dict[str, dict] = field(default_factory=dict)  # observation unit id -> plant doc


async def load_study_data(db, brapi_db, study_ids: List[str]) -> StudyData:
    data = StudyData()
    ids = [s for s in dict.fromkeys(study_ids) if s]
    if not ids:
        return data
    async for doc in brapi_db["studies"].find({"_id": {"$in": ids}}):
        data.studies.append(doc)
    order = {sid: i for i, sid in enumerate(ids)}
    data.studies.sort(key=lambda s: order.get(s["_id"], 0))

    async for run in db["analysis_runs"].find({"studyId": {"$in": ids}}).sort("createdAt", 1):
        data.runs.append(run)

    image_ids = list({res.get("imageId") for run in data.runs for res in run.get("results", []) if res.get("imageId")})
    if image_ids:
        async for img in db["images"].find({"_id": {"$in": image_ids}}):
            data.images[img["_id"]] = img

    async for ou in brapi_db["observation_units"].find({"studyId": {"$in": ids}}):
        data.plants[ou["_id"]] = ou
    return data
