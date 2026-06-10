import xml.etree.ElementTree as ET  # 국립수어원 API가 XML로 응답하므로 XML 문자열을 파싱할 때 사용합니다.

from urllib.parse import urlencode  # 외부 API 요청 주소에 붙일 query string을 안전하게 만들 때 사용합니다.
from urllib.request import urlopen  # 국립수어원 API 주소로 실제 HTTP 요청을 보낼 때 사용합니다.

from fastapi import APIRouter, HTTPException, Query  # 라우터, 에러 응답, query 파라미터 처리 도구입니다.
from pymongo import ASCENDING  # MongoDB 조회 결과를 단어명 기준 오름차순으로 정렬할 때 사용합니다.
from pymongo.errors import PyMongoError  # MongoDB 조회/저장 중 발생하는 오류를 잡기 위해 사용합니다.

from app.core.config import settings  # env 파일에 있는 국립수어원 API 키를 읽어온 설정 객체입니다.
from app.core.mongo_database import get_dictionary_collection  # 수어사전 데이터를 저장/조회할 MongoDB 컬렉션입니다.
from app.schemas.dictionary import DictionarySchema  # 프론트로 반환할 수어 사전 응답 JSON 구조입니다.


# 이 파일에 있는 모든 API 주소는 /api/v1/dictionary 로 시작합니다.
# 예: /categories endpoint는 최종적으로 /api/v1/dictionary/categories 가 됩니다.
router = APIRouter(prefix="/api/v1/dictionary", tags=["dictionary"])


# 국립수어원 수어 API 요청 기본 주소입니다.
# serviceKey, pageNo, numOfRows, keyword 같은 값은 아래 sync endpoint에서 query string으로 붙입니다.
SIGN_API_URL = "http://api.kcisa.kr/API_CNV_054/request"


def get_xml_text(item, tag_name):
    # XML item 안에서 title, categoryType, signDescription 같은 태그를 찾습니다.
    element = item.find(tag_name)

    # 태그가 없거나 태그 안의 값이 비어 있으면 빈 문자열을 반환해 이후 로직이 깨지지 않게 합니다.
    if element is None or element.text is None:
        return ""

    # 앞뒤 공백을 제거한 실제 텍스트만 반환합니다.
    return element.text.strip()


def get_next_dictionary_id(collection):
    # 국립수어원 응답에 localId가 없는 예외 상황을 대비해 다음 dictionary_id를 계산합니다.
    # MongoDB에는 MySQL AUTO_INCREMENT가 없으므로 가장 큰 dictionary_id에 1을 더해 사용합니다.
    last_dictionary = collection.find_one(sort=[("dictionary_id", -1)])

    # 아직 저장된 데이터가 없으면 1번부터 시작합니다.
    if last_dictionary is None:
        return 1

    # 기존 dictionary_id가 숫자로 저장되어 있으면 그대로 1을 더합니다.
    try:
        return int(last_dictionary.get("dictionary_id", 0)) + 1
    except (TypeError, ValueError):
        # 혹시 숫자로 바꿀 수 없는 값이 들어 있으면 안전하게 1번부터 시작합니다.
        return 1


def get_document_dictionary_id(document):
    # MongoDB에 이미 들어간 데이터가 어떤 필드명으로 ID를 가지고 있는지 확인합니다.
    # 현재 프론트는 dictionary_id를 기준으로 상세 조회를 하므로 응답에는 반드시 숫자 ID가 필요합니다.
    for key in ("dictionary_id", "local_id", "localId"):
        try:
            return int(document.get(key))
        except (TypeError, ValueError):
            continue

    # 사용할 수 있는 ID 필드가 없으면 0을 반환하고, 아래 ensure_dictionary_ids에서 새 번호를 붙입니다.
    return 0


def ensure_dictionary_ids(collection):
    # MySQL에서 MongoDB로 옮긴 데이터에 dictionary_id가 빠져 있을 수 있어 보정합니다.
    # dictionary_id가 없으면 목록에서는 보일 수 있지만 상세 조회 /dictionary/{id}가 불가능합니다.
    invalid_id_query = {
        "$or": [
            {"dictionary_id": {"$exists": False}},
            {"dictionary_id": None},
            {"dictionary_id": ""},
            {"dictionary_id": 0},
            {"dictionary_id": "0"},
        ]
    }

    # dictionary_id가 없거나 0으로 들어간 문서가 있는지만 먼저 가볍게 확인합니다.
    missing_id_count = collection.count_documents(invalid_id_query, limit=1)

    # 이미 모든 문서에 dictionary_id가 있으면 아무 작업도 하지 않습니다.
    if missing_id_count == 0:
        return

    # 기존 dictionary_id 중 가장 큰 값을 찾아 그 다음 번호부터 새로 붙입니다.
    next_dictionary_id = get_next_dictionary_id(collection)

    # dictionary_id가 없거나 잘못 들어간 문서들을 단어명 기준으로 순회하며 안정적인 번호를 부여합니다.
    for document in collection.find(invalid_id_query).sort("word_name", ASCENDING):
        document_id = get_document_dictionary_id(document)

        # localId 같은 기존 원본 ID가 있으면 그 값을 우선 사용합니다.
        if document_id:
            dictionary_id = document_id
        else:
            dictionary_id = next_dictionary_id
            next_dictionary_id += 1

        # MongoDB의 _id로 해당 문서를 찾아 dictionary_id 필드만 추가합니다.
        collection.update_one(
            {"_id": document["_id"]},
            {"$set": {"dictionary_id": dictionary_id}},
        )


def convert_dictionary_document(document):
    # MongoDB document를 프론트가 이미 사용 중인 DictionarySchema 형태로 맞춰주는 함수입니다.
    # MongoDB의 _id(ObjectId)는 JSON 응답 구조에 필요 없으므로 dictionary_id 중심으로 변환합니다.
    if document is None:
        return None

    # MongoDB에 숫자 또는 문자열로 들어온 dictionary_id를 프론트 응답에서는 int로 통일합니다.
    dictionary_id = get_document_dictionary_id(document)

    return {
        "dictionary_id": dictionary_id,
        "category_name": document.get("category_name", ""),
        "word_name": document.get("word_name", ""),
        "definition": document.get("definition", ""),
        "video_url": document.get("video_url"),
    }


@router.get("/categories", response_model=list[str])
def get_dictionary_categories():
    # 수어표현검색1 화면에서 카테고리 버튼 목록을 보여주기 위한 API입니다.
    # 최종 주소: GET /api/v1/dictionary/categories
    collection = get_dictionary_collection()

    try:
        # MongoDB dictionary 컬렉션에서 category_name 값만 중복 없이 가져옵니다.
        categories = collection.distinct("category_name")
    except PyMongoError as error:
        # MongoDB 연결 또는 조회 과정에서 문제가 생기면 Swagger/프론트에서 500 에러로 확인할 수 있게 합니다.
        raise HTTPException(status_code=500, detail=f"Dictionary MongoDB read failed: {error}")

    # 빈 카테고리명은 화면에 버튼으로 보여줄 필요가 없으므로 제외하고 가나다순으로 정렬합니다.
    return sorted(category for category in categories if category)


@router.get("", response_model=list[DictionarySchema])
def get_dictionary_list(
    keyword: str | None = Query(default=None),
    category: str | None = Query(default=None),
):
    # 수어표현검색2 화면에서 단어 목록을 보여주기 위한 API입니다.
    # 최종 주소: GET /api/v1/dictionary
    # 사용 예시:
    # - /api/v1/dictionary
    # - /api/v1/dictionary?category=기타
    # - /api/v1/dictionary?keyword=강원도
    # - /api/v1/dictionary?keyword=강원도&category=나라명 및 지명
    collection = get_dictionary_collection()
    mongo_query = {}

    try:
        # 기존 MongoDB 데이터에 dictionary_id가 없으면 상세 조회가 가능하도록 번호를 먼저 보정합니다.
        ensure_dictionary_ids(collection)
    except PyMongoError as error:
        # ID 보정도 MongoDB 작업이므로 실패하면 조회 실패와 같은 500 에러로 반환합니다.
        raise HTTPException(status_code=500, detail=f"Dictionary MongoDB id update failed: {error}")

    # category query가 있으면 해당 카테고리의 단어만 남깁니다.
    if category:
        mongo_query["category_name"] = category

    # keyword query가 있으면 단어명 또는 설명에 검색어가 포함된 데이터만 남깁니다.
    if keyword:
        mongo_query["$or"] = [
            {"word_name": {"$regex": keyword, "$options": "i"}},
            {"definition": {"$regex": keyword, "$options": "i"}},
        ]

    try:
        # 단어명 기준으로 정렬한 뒤 모든 결과를 리스트로 반환합니다.
        # convert_dictionary_document로 MongoDB document를 프론트 응답 구조에 맞춥니다.
        documents = collection.find(mongo_query).sort("word_name", ASCENDING)
        return [convert_dictionary_document(document) for document in documents]
    except PyMongoError as error:
        # DB 조회 실패 시 프론트가 원인을 확인할 수 있도록 500 에러를 반환합니다.
        raise HTTPException(status_code=500, detail=f"Dictionary MongoDB read failed: {error}")


@router.get("/sync/sign-api")
def sync_dictionary_from_sign_api(
    page_no: int = Query(default=1),
    num_of_rows: int = Query(default=10),
    keyword: str = Query(default=""),
):
    # 국립수어원 API 데이터를 가져와 MongoDB dictionary 컬렉션에 저장하는 동기화 API입니다.
    # 최종 주소: GET /api/v1/dictionary/sync/sign-api
    # Swagger 테스트 예시:
    # - page_no: 31
    # - num_of_rows: 5
    # - keyword: 비워두기
    # saved_count는 새로 저장한 개수, skipped_count는 이미 있어서 건너뛴 개수입니다.
    if not settings.sign_api_service_key:
        # env 파일에 SIGN_API_SERVICE_KEY가 없으면 외부 API 호출을 할 수 없으므로 500 에러를 반환합니다.
        raise HTTPException(status_code=500, detail="SIGN_API_SERVICE_KEY is not set")

    # 국립수어원 API에 전달할 query string 값을 구성합니다.
    # serviceKey는 env에서 읽은 API 키이고, 나머지는 Swagger나 프론트에서 받은 query 값입니다.
    params = urlencode({
        "serviceKey": settings.sign_api_service_key,
        "numOfRows": num_of_rows,
        "pageNo": page_no,
        "keyword": keyword,
    })

    # 최종 외부 API 요청 주소입니다.
    # 예: http://api.kcisa.kr/API_CNV_054/request?serviceKey=...&numOfRows=5&pageNo=31&keyword=
    request_url = f"{SIGN_API_URL}?{params}"

    try:
        # 국립수어원 API에 HTTP 요청을 보내고 응답 XML 문자열을 읽습니다.
        with urlopen(request_url, timeout=10) as response:
            response_text = response.read().decode("utf-8")

        # 문자열 형태의 XML을 ElementTree 객체로 바꿔서 태그별 값을 꺼낼 수 있게 합니다.
        root = ET.fromstring(response_text)
    except Exception as error:
        # 외부 API 요청 실패, XML 파싱 실패 등은 백엔드 내부 DB 오류가 아니라 외부 API 오류로 보고 502를 반환합니다.
        raise HTTPException(status_code=502, detail=f"Sign API request failed: {error}")

    # 국립수어원 API의 header/resultCode 값을 확인합니다.
    # 0000이면 정상, 그 외 값이면 API 키나 요청 파라미터 문제가 있을 수 있습니다.
    result_code = get_xml_text(root.find("header"), "resultCode")

    if result_code != "0000":
        # 실패 메시지도 같이 꺼내서 Swagger에서 원인을 볼 수 있게 합니다.
        result_msg = get_xml_text(root.find("header"), "resultMsg")
        raise HTTPException(
            status_code=502,
            detail=f"Sign API error: {result_code} {result_msg}",
        )

    collection = get_dictionary_collection()
    saved_count = 0  # 새로 저장한 데이터 개수입니다.
    skipped_count = 0  # 필수값이 없거나 이미 DB에 있어서 저장하지 않은 데이터 개수입니다.

    try:
        # XML 응답 안의 모든 item 태그를 하나씩 순회합니다.
        for item in root.findall(".//item"):
            # localId는 국립수어원에서 내려주는 원본 데이터 ID입니다.
            # 값이 있으면 dictionary_id로 사용해서 상세 조회에도 그대로 활용합니다.
            local_id = get_xml_text(item, "localId")
            # title 태그는 수어 단어명으로 사용합니다.
            word_name = get_xml_text(item, "title")
            # categoryType이 있으면 카테고리로 쓰고, 비어 있으면 collectionDb를 카테고리로 사용합니다.
            category_name = get_xml_text(item, "categoryType") or get_xml_text(item, "collectionDb")
            # signDescription을 설명으로 쓰고, 없으면 description, 그것도 없으면 기본 문구를 사용합니다.
            definition = (
                get_xml_text(item, "signDescription")
                or get_xml_text(item, "description")
                or "수어 동작 설명이 없습니다."
            )
            # subDescription 태그에 수어 영상 mp4 주소가 들어 있습니다.
            video_url = get_xml_text(item, "subDescription")

            # 단어명이나 카테고리명이 없으면 화면에 보여주기 어렵기 때문에 저장하지 않습니다.
            if not word_name or not category_name:
                skipped_count += 1
                continue

            # localId가 숫자로 들어오면 dictionary_id로 사용하고, 없으면 MongoDB 기준 다음 번호를 만듭니다.
            try:
                dictionary_id = int(local_id)
            except (TypeError, ValueError):
                dictionary_id = get_next_dictionary_id(collection)

            # 같은 dictionary_id 또는 같은 단어명+영상 URL이 이미 있으면 중복 데이터로 판단합니다.
            exists = collection.find_one({
                "$or": [
                    {"dictionary_id": dictionary_id},
                    {"word_name": word_name, "video_url": video_url},
                ]
            })

            # 이미 저장된 데이터라면 다시 저장하지 않고 skipped_count만 증가시킵니다.
            if exists:
                skipped_count += 1
                continue

            # MongoDB에 저장할 수어사전 document입니다.
            # 프론트가 기대하는 필드명과 같게 저장해서 조회 API가 단순하게 응답할 수 있게 합니다.
            dictionary_document = {
                "dictionary_id": dictionary_id,
                "category_name": category_name,
                "word_name": word_name,
                "definition": definition,
                "video_url": video_url,
            }

            # 새 수어사전 데이터를 MongoDB dictionary 컬렉션에 저장합니다.
            collection.insert_one(dictionary_document)
            saved_count += 1
    except PyMongoError as error:
        # MongoDB 저장 중 오류가 생기면 Swagger/프론트에서 원인을 볼 수 있게 500 에러를 반환합니다.
        raise HTTPException(status_code=500, detail=f"Dictionary MongoDB save failed: {error}")

    # Swagger와 프론트에서 동기화 결과를 확인할 수 있도록 저장/건너뜀 개수를 반환합니다.
    return {
        "saved_count": saved_count,
        "skipped_count": skipped_count,
        "page_no": page_no,
        "num_of_rows": num_of_rows,
    }


@router.get("/{dictionary_id}", response_model=DictionarySchema)
def get_dictionary_detail(dictionary_id: int):
    # 수어표현검색3 화면에서 단어 하나의 상세 정보를 보여주기 위한 API입니다.
    # 최종 주소: GET /api/v1/dictionary/{dictionary_id}
    # 예: /api/v1/dictionary/10
    collection = get_dictionary_collection()

    try:
        # dictionary_id가 일치하는 단어 하나만 MongoDB에서 조회합니다.
        dictionary = collection.find_one({"dictionary_id": dictionary_id})
    except PyMongoError as error:
        # DB 조회 실패 시 500 에러를 반환합니다.
        raise HTTPException(status_code=500, detail=f"Dictionary MongoDB read failed: {error}")

    # 해당 ID의 단어가 없으면 존재하지 않는 자원이므로 404를 반환합니다.
    if dictionary is None:
        raise HTTPException(status_code=404, detail="Dictionary item not found")

    # MongoDB document를 프론트 응답 구조로 변환해서 반환합니다.
    return convert_dictionary_document(dictionary)
