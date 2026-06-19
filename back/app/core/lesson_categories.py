DEFAULT_LESSON_CATEGORIES = [
    {"category_id": 1, "name": "사회생활", "description": "사회생활 표현을 학습합니다.", "sort_order": 1},
    {"category_id": 2, "name": "일상생활", "description": "일상생활 표현을 학습합니다.", "sort_order": 2},
    {"category_id": 3, "name": "삶/가족", "description": "삶과 가족 관련 표현을 학습합니다.", "sort_order": 3},
    {"category_id": 4, "name": "교육/정보", "description": "교육과 정보통신 표현을 학습합니다.", "sort_order": 4},
    {"category_id": 5, "name": "교통/지역", "description": "교통과 지역 표현을 학습합니다.", "sort_order": 5},
    {"category_id": 6, "name": "개념/자연", "description": "개념과 자연 표현을 학습합니다.", "sort_order": 6},
    {"category_id": 7, "name": "인간/감정", "description": "인간과 감정 표현을 학습합니다.", "sort_order": 7},
    {"category_id": 8, "name": "기타/문화", "description": "기타와 문화 표현을 학습합니다.", "sort_order": 8},
]


LESSON_CATEGORY_SOURCE_MAP = {
    1: ["사회생활"],
    2: ["경제생활", "식생활", "의생활", "주생활", "의학"],
    3: ["삶"],
    4: ["교육", "정보통신"],
    5: ["교통", "나라명 및 지명"],
    6: ["개념", "자연"],
    7: ["인간"],
    8: ["기타", "문화"],
}


def get_lesson_query(category_id: int | None) -> dict:
    source_categories = sorted({
        source_category
        for category_sources in LESSON_CATEGORY_SOURCE_MAP.values()
        for source_category in category_sources
    })
    mongo_query = {
        "video_url": {"$exists": True, "$nin": [None, ""]},
        "category_name": {"$in": source_categories},
    }
    if category_id is not None:
        mongo_query["category_name"] = {"$in": LESSON_CATEGORY_SOURCE_MAP.get(category_id, [])}
    return mongo_query