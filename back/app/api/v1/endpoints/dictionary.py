import xml.etree.ElementTree as ET  # 국립수어원 API가 XML로 응답하므로 XML 문자열을 파싱할 때 사용합니다.

from urllib.parse import urlencode  # 외부 API 요청 주소에 붙일 query string을 안전하게 만들 때 사용합니다.
from urllib.request import urlopen  # 국립수어원 API 주소로 실제 HTTP 요청을 보낼 때 사용합니다.
from fastapi import APIRouter, Depends, HTTPException, Query  # 라우터, 의존성 주입, 에러 응답, query 파라미터 처리 도구입니다.
from sqlalchemy import or_  # 단어명 또는 설명 중 하나라도 검색어를 포함하면 조회되도록 OR 조건을 만들 때 사용합니다.
from sqlalchemy.exc import SQLAlchemyError  # DB 조회/저장 중 발생하는 SQLAlchemy 계열 오류를 잡기 위해 사용합니다.
from sqlalchemy.orm import Session  # FastAPI endpoint 함수에서 DB 세션 타입을 명시하기 위해 사용합니다.

from app.core.config import settings  # env 파일에 있는 DB 정보와 국립수어원 API 키를 읽어온 설정 객체입니다.
from app.core.mysql_database import engine, get_db  # engine은 테이블 생성에, get_db는 요청마다 DB 세션을 받는 데 사용합니다.
from app.models.dictionary import DictionaryModel  # DICTIONARY 테이블과 연결된 SQLAlchemy 모델입니다.
from app.schemas.dictionary import DictionarySchema  # 프론트로 반환할 수어 사전 응답 JSON 구조입니다.


# 이 파일에 있는 모든 API 주소는 /api/v1/dictionary 로 시작합니다.
# 예: /categories endpoint는 최종적으로 /api/v1/dictionary/categories 가 됩니다.
router = APIRouter(prefix="/api/v1/dictionary", tags=["dictionary"])


# 국립수어원 수어 API 요청 기본 주소입니다.
# serviceKey, pageNo, numOfRows, keyword 같은 값은 아래 sync endpoint에서 query string으로 붙입니다.
SIGN_API_URL = "http://api.kcisa.kr/API_CNV_054/request"


def ensure_dictionary_table():
    # DICTIONARY 테이블이 없을 때만 생성합니다.
    # checkfirst=True가 있으므로 이미 테이블이 있으면 다시 만들지 않습니다.
    DictionaryModel.__table__.create(bind=engine, checkfirst=True)


def get_xml_text(item, tag_name):
    # XML item 안에서 title, categoryType, signDescription 같은 태그를 찾습니다.
    element = item.find(tag_name)

    # 태그가 없거나 태그 안의 값이 비어 있으면 빈 문자열을 반환해 이후 로직이 깨지지 않게 합니다.
    if element is None or element.text is None:
        return ""

    # 앞뒤 공백을 제거한 실제 텍스트만 반환합니다.
    return element.text.strip()


@router.get("/categories", response_model=list[str])
def get_dictionary_categories(db: Session = Depends(get_db)):
    # 수어표현검색1 화면에서 카테고리 버튼 목록을 보여주기 위한 API입니다.
    # 최종 주소: GET /api/v1/dictionary/categories
    try:
        # 테이블이 없는 초기 실행 상황을 대비해 DICTIONARY 테이블 존재 여부를 먼저 확인합니다.
        ensure_dictionary_table()

        # DICTIONARY 테이블에서 category_name만 조회합니다.
        # distinct()는 같은 카테고리명이 여러 번 나와도 한 번만 보여주기 위해 사용합니다.
        categories = (
            db.query(DictionaryModel.category_name)
            .distinct()
            .order_by(DictionaryModel.category_name)
            .all()
        )
    except SQLAlchemyError as error:
        # DB 연결 또는 조회 과정에서 문제가 생기면 Swagger/프론트에서 500 에러로 확인할 수 있게 합니다.
        raise HTTPException(status_code=500, detail=f"Dictionary DB read failed: {error}")

    # SQLAlchemy 조회 결과는 객체 형태이므로 category_name 값만 꺼내 문자열 리스트로 반환합니다.
    return [category.category_name for category in categories]


@router.get("", response_model=list[DictionarySchema])
def get_dictionary_list(
    keyword: str | None = Query(default=None),
    category: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    # 수어표현검색2 화면에서 단어 목록을 보여주기 위한 API입니다.
    # 최종 주소: GET /api/v1/dictionary
    # 사용 예시:
    # - /api/v1/dictionary
    # - /api/v1/dictionary?category=기타
    # - /api/v1/dictionary?keyword=강원도
    # - /api/v1/dictionary?keyword=강원도&category=나라명 및 지명
    ensure_dictionary_table()

    # DICTIONARY 테이블 전체를 조회하는 기본 query를 만듭니다.
    query = db.query(DictionaryModel)

    # category query가 있으면 해당 카테고리의 단어만 남깁니다.
    if category:
        query = query.filter(DictionaryModel.category_name == category)

    # keyword query가 있으면 단어명 또는 설명에 검색어가 포함된 데이터만 남깁니다.
    if keyword:
        # LIKE 검색에 사용할 수 있도록 앞뒤에 %를 붙입니다.
        # 예: 강원도 -> %강원도%
        search_keyword = f"%{keyword}%"
        query = query.filter(
            or_(
                DictionaryModel.word_name.like(search_keyword),
                DictionaryModel.definition.like(search_keyword),
            )
        )

    try:
        # 단어명 기준으로 정렬한 뒤 모든 결과를 리스트로 반환합니다.
        # response_model=list[DictionarySchema] 때문에 Swagger에는 DictionarySchema 배열로 표시됩니다.
        return query.order_by(DictionaryModel.word_name).all()
    except SQLAlchemyError as error:
        # DB 조회 실패 시 프론트가 원인을 확인할 수 있도록 500 에러를 반환합니다.
        raise HTTPException(status_code=500, detail=f"Dictionary DB read failed: {error}")


@router.get("/sync/sign-api")
def sync_dictionary_from_sign_api(
    page_no: int = Query(default=1),
    num_of_rows: int = Query(default=10),
    keyword: str = Query(default=""),
    db: Session = Depends(get_db),
):
    # 국립수어원 API 데이터를 가져와 DICTIONARY 테이블에 저장하는 동기화 API입니다.
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

    # 새로 저장한 데이터 개수입니다.
    saved_count = 0
    # 필수값이 없거나 이미 DB에 있어서 저장하지 않은 데이터 개수입니다.
    skipped_count = 0

    try:
        # 저장 전에 DICTIONARY 테이블이 있는지 확인합니다.
        ensure_dictionary_table()

        # XML 응답 안의 모든 item 태그를 하나씩 순회합니다.
        for item in root.findall(".//item"):
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

            # 같은 단어명과 같은 영상 URL이 이미 DB에 있으면 중복 데이터로 판단합니다.
            exists = (
                db.query(DictionaryModel)
                .filter(
                    DictionaryModel.word_name == word_name,
                    DictionaryModel.video_url == video_url,
                )
                .first()
            )

            # 이미 저장된 데이터라면 다시 저장하지 않고 skipped_count만 증가시킵니다.
            if exists:
                skipped_count += 1
                continue

            # XML에서 꺼낸 값을 DICTIONARY 테이블 모델 객체로 만듭니다.
            dictionary = DictionaryModel(
                category_name=category_name,
                word_name=word_name,
                definition=definition,
                video_url=video_url,
            )

            # 새 데이터를 DB 세션에 추가합니다.
            db.add(dictionary)
            saved_count += 1

        # 반복문에서 추가한 데이터들을 실제 DB에 확정 저장합니다.
        db.commit()
    except SQLAlchemyError as error:
        # 저장 중 오류가 생기면 지금까지의 변경을 취소해서 DB가 어중간한 상태가 되지 않게 합니다.
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Dictionary DB save failed: {error}")

    # Swagger와 프론트에서 동기화 결과를 확인할 수 있도록 저장/건너뜀 개수를 반환합니다.
    return {
        "saved_count": saved_count,
        "skipped_count": skipped_count,
        "page_no": page_no,
        "num_of_rows": num_of_rows,
    }


@router.get("/{dictionary_id}", response_model=DictionarySchema)
def get_dictionary_detail(dictionary_id: int, db: Session = Depends(get_db)):
    # 수어표현검색3 화면에서 단어 하나의 상세 정보를 보여주기 위한 API입니다.
    # 최종 주소: GET /api/v1/dictionary/{dictionary_id}
    # 예: /api/v1/dictionary/10
    try:
        # 테이블이 없는 초기 실행 상황을 대비해 DICTIONARY 테이블 존재 여부를 먼저 확인합니다.
        ensure_dictionary_table()

        # dictionary_id가 일치하는 단어 하나만 조회합니다.
        dictionary = (
            db.query(DictionaryModel)
            .filter(DictionaryModel.dictionary_id == dictionary_id)
            .first()
        )
    except SQLAlchemyError as error:
        # DB 조회 실패 시 500 에러를 반환합니다.
        raise HTTPException(status_code=500, detail=f"Dictionary DB read failed: {error}")

    # 해당 ID의 단어가 없으면 존재하지 않는 자원이므로 404를 반환합니다.
    if dictionary is None:
        raise HTTPException(status_code=404, detail="Dictionary item not found")

    # 찾은 단어 객체를 반환합니다.
    # response_model=DictionarySchema가 적용되어 JSON 응답 형태가 정리됩니다.
    return dictionary
