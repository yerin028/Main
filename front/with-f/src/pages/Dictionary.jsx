import { useEffect, useMemo, useState } from 'react'; // React 상태, 화면 진입 처리, 계산값 저장 기능
import './Dictionary.css'; // 수어표현검색 화면 CSS
import { useLocation } from 'react-router-dom'; // 현재 route 정보와 navigate state 값을 읽기 위해 사용합니다.

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'; // 백엔드 API 주소
const categoryPageSize = 6; // 카테고리 한 페이지 표시 개수
const wordPageSize = 5; // 단어 한 페이지 표시 개수

// 수어 API가 http sldict 영상 주소를 내려주면 브라우저에서 안정적으로 불러올 수 있게 https 주소로 바꿉니다.
// 일부 영상은 krdicmedia 호스트에서는 400 오류가 나지만, https sldict 주소에서는 정상 재생됩니다.
// 그래서 호스트는 sldict 그대로 두고 http만 https로 보정합니다.
function normalizeVideoUrl(videoUrl) {
  return videoUrl.replace(
    'http://sldict.korean.go.kr',
    'https://sldict.korean.go.kr'
  );
}

// 영상 파일명 규칙을 이용해 목록 미리보기에 사용할 JPG 썸네일 주소를 만듭니다.
// 예: MOV000361377_700X466.mp4 -> MOV000361377_215X161.jpg
// 단어선택창에서는 영상을 바로 재생하지 않아도 poster 이미지가 먼저 보여서 빈 박스처럼 보이지 않습니다.
function getVideoPosterUrl(videoUrl) {
  return videoUrl.replace('_700X466.mp4', '_215X161.jpg');
}

// 백엔드/DB 연결 전에도 화면 흐름을 확인할 수 있게 사용하는 임시 수어 사전 데이터입니다.
// 실제 API가 정상 응답하면 이 데이터 대신 DICTIONARY 테이블 데이터가 표시됩니다.
// Array.from({ length: 24 })는 카테고리 24개를 만들기 위한 반복문 역할을 합니다.
const fallbackDictionaryItems = Array.from({ length: 24 }, (_, categoryIndex) =>
  // 각 카테고리 안에 들어갈 단어 9개를 만듭니다.
  Array.from({ length: 9 }, (_, wordIndex) => {
    // index는 0부터 시작하므로 화면에 보여줄 번호는 1을 더해서 만듭니다.
    const categoryNumber = categoryIndex + 1; // 화면 표시용 카테고리 번호
    const wordNumber = wordIndex + 1; // 화면 표시용 단어 번호

    // 실제 DB 응답과 같은 형태로 임시 단어 객체를 반환합니다.
    return {
      dictionaryId: categoryIndex * 9 + wordNumber, // 임시 고유 번호
      categoryName: `카테고리${categoryNumber}`, // 카테고리 선택창 표시 이름
      wordName: `카테고리${categoryNumber}-단어${wordNumber}`, // 단어명
      definition: `카테고리${categoryNumber}-단어${wordNumber}의 수어 동작 설명입니다.`, // 수어 설명
      videoUrl: '', // Azure 영상 URL 자리
    };
  })
// 카테고리별로 중첩된 단어 배열을 하나의 단어 목록 배열로 펼칩니다.
).flat();

// 백엔드 응답은 DB 컬럼명 기준 snake_case이고, React 내부에서는 camelCase로 사용합니다.
function convertDictionaryItem(item) {
  return {
    dictionaryId: item.dictionary_id, // 사전 ID
    categoryName: item.category_name, // 카테고리명
    wordName: item.word_name, // 단어명
    definition: item.definition, // 수어 동작 설명
    videoUrl: normalizeVideoUrl(item.video_url || ''), // 영상 URL
  };
}

// 카테고리 이름을 정렬할 때 카테고리10이 카테고리2보다 앞에 오지 않도록 숫자 기준도 함께 비교합니다.
function compareCategoryName(firstCategory, secondCategory) {
  return firstCategory.localeCompare(secondCategory, 'ko-KR', {
    numeric: true,
    sensitivity: 'base',
  });
}

// 단어명 정렬도 카테고리 정렬과 동일하게 자연 정렬을 사용합니다.
function compareDictionaryItem(firstItem, secondItem) {
  return firstItem.wordName.localeCompare(secondItem.wordName, 'ko-KR', {
    numeric: true,
    sensitivity: 'base',
  });
}

// 페이지가 많을 때 전체 번호를 모두 보여주지 않고 현재 페이지 주변만 보여줍니다.
function getPaginationItems(currentPage, totalPages) {
  // 페이지 수가 7개 이하라면 생략 없이 전부 보여줍니다.
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, index) => index + 1);
  }

  // 앞쪽 페이지에서는 처음 5개와 마지막 페이지만 보여줍니다.
  if (currentPage <= 4) {
    return [1, 2, 3, 4, 5, 'next-ellipsis', totalPages];
  }

  // 뒤쪽 페이지에서는 첫 페이지와 마지막 5개만 보여줍니다.
  if (currentPage >= totalPages - 3) {
    return [1, 'prev-ellipsis', totalPages - 4, totalPages - 3, totalPages - 2, totalPages - 1, totalPages];
  }

  // 중간 페이지에서는 첫 페이지, 현재 페이지 주변, 마지막 페이지만 보여줍니다.
  return [
    1,
    'prev-ellipsis',
    currentPage - 1,
    currentPage,
    currentPage + 1,
    'next-ellipsis',
    totalPages,
  ];
}

function Dictionary() {
  // Layout.jsx에서 상단 수어검색 메뉴를 다시 누르면 navigate state에 resetAt 값을 담아 보냅니다.
  // 이 페이지에서는 useLocation으로 그 값을 읽어서 내부 화면을 첫 화면으로 되돌릴지 판단합니다.
  const location = useLocation(); // 현재 route 정보와 state 값을 담고 있는 객체입니다.

  // viewMode는 피그마의 수어표현검색1/2/3 화면을 한 route 안에서 전환하기 위한 값입니다.
  // category: 카테고리 선택창, result: 단어 선택창, detail: 단어 설명창입니다.
  const [viewMode, setViewMode] = useState('category'); // 현재 화면 상태
  const [searchKeyword, setSearchKeyword] = useState(''); // 검색창 입력값
  const [selectedCategory, setSelectedCategory] = useState(''); // 선택한 카테고리
  const [categories, setCategories] = useState([]); // 카테고리 목록
  const [dictionaryItems, setDictionaryItems] = useState([]); // 단어 목록
  const [selectedDictionary, setSelectedDictionary] = useState(null); // 상세 화면 선택 단어
  const [categoryPage, setCategoryPage] = useState(1); // 현재 카테고리 페이지
  const [wordPage, setWordPage] = useState(1); // 현재 단어 페이지
  const [categorySortOrder, setCategorySortOrder] = useState('asc'); // 카테고리 정렬 방향
  const [wordSortOrder, setWordSortOrder] = useState('asc'); // 단어 정렬 방향
  const [isLoading, setIsLoading] = useState(false); // API 요청 진행 여부
  const [isFallbackMode, setIsFallbackMode] = useState(false); // 임시 데이터 사용 여부

  // 카테고리 정렬 버튼(정렬/역순)에 따라 표시 순서를 계산합니다.
  const sortedCategories = useMemo(() => {
    // 원본 categories 배열을 직접 바꾸지 않기 위해 복사한 뒤 정렬합니다.
    const orderedCategories = [...categories].sort(compareCategoryName);

    // 역순 버튼을 누른 상태라면 정렬된 배열을 뒤집어서 반환합니다.
    if (categorySortOrder === 'desc') {
      return orderedCategories.reverse();
    }

    // 정렬 상태라면 정순 배열을 그대로 반환합니다.
    return orderedCategories;
  }, [categories, categorySortOrder]);

  // 카테고리 선택창은 6개씩 보여주기 때문에 전체 페이지 수를 계산합니다.
  const totalCategoryPages = Math.max(
    // 카테고리가 없더라도 페이지 번호는 최소 1페이지가 보이게 합니다.
    1,
    // 전체 카테고리 수를 한 페이지 개수로 나누고 올림해서 페이지 수를 구합니다.
    Math.ceil(sortedCategories.length / categoryPageSize)
  );

  // 카테고리 페이지 번호를 화면에 너무 길게 늘어놓지 않도록 축약해서 계산합니다.
  const categoryPaginationItems = getPaginationItems(categoryPage, totalCategoryPages);

  // 현재 카테고리 페이지에 실제로 표시할 카테고리 6개를 계산합니다.
  const visibleCategories = useMemo(() => {
    // 현재 페이지가 시작되는 배열 index를 계산합니다.
    const startIndex = (categoryPage - 1) * categoryPageSize;
    // 시작 index부터 6개만 잘라서 화면에 보여줍니다.
    return sortedCategories.slice(startIndex, startIndex + categoryPageSize);
  }, [sortedCategories, categoryPage]);

  // 단어선택창은 5개씩 보여주기 때문에 전체 페이지 수를 계산합니다.
  const totalWordPages = Math.max(
    // 단어가 없더라도 페이지 계산값은 최소 1로 둡니다.
    1,
    // 전체 단어 수를 한 페이지 개수로 나누고 올림해서 페이지 수를 구합니다.
    Math.ceil(dictionaryItems.length / wordPageSize)
  );

  // 단어 페이지 번호도 현재 페이지 주변만 보여주도록 축약해서 계산합니다.
  const wordPaginationItems = getPaginationItems(wordPage, totalWordPages);

  // 단어선택창에 표시할 단어 목록을 정렬/역순 상태에 맞게 계산합니다.
  const sortedDictionaryItems = useMemo(() => {
    // 원본 dictionaryItems 배열을 직접 바꾸지 않기 위해 복사한 뒤 정렬합니다.
    const orderedItems = [...dictionaryItems].sort(compareDictionaryItem);

    // 단어 역순 버튼을 누른 상태라면 정렬된 배열을 뒤집어서 반환합니다.
    if (wordSortOrder === 'desc') {
      return orderedItems.reverse();
    }

    // 단어 정렬 상태라면 정순 배열을 그대로 반환합니다.
    return orderedItems;
  }, [dictionaryItems, wordSortOrder]);

  // 현재 단어 페이지에 보여줄 5개의 단어만 잘라냅니다.
  const visibleDictionaryItems = useMemo(() => {
    // 현재 단어 페이지가 시작되는 배열 index를 계산합니다.
    const startIndex = (wordPage - 1) * wordPageSize;
    // 시작 index부터 5개만 잘라서 단어 카드로 보여줍니다.
    return sortedDictionaryItems.slice(startIndex, startIndex + wordPageSize);
  }, [sortedDictionaryItems, wordPage]);

  // API 호출에 실패하거나 DB 데이터가 비어 있을 때 fallback 데이터에서 검색 결과를 만듭니다.
  const getFallbackDictionaryItems = (keyword = searchKeyword, category = selectedCategory) => {
    // 검색어 앞뒤 공백을 제거하고 소문자로 바꿔 비교하기 쉽게 만듭니다.
    const normalizedKeyword = keyword.trim().toLowerCase();

    // 임시 데이터 전체에서 선택 카테고리와 검색어 조건에 맞는 단어만 남깁니다.
    return fallbackDictionaryItems.filter((item) => {
      // 카테고리를 선택하지 않았으면 전체 허용, 선택했으면 같은 카테고리만 허용합니다.
      const matchesCategory = !category || item.categoryName === category;
      // 검색어가 없으면 전체 허용, 있으면 단어명이나 설명에 검색어가 포함된 항목만 허용합니다.
      const matchesKeyword =
        !normalizedKeyword ||
        item.wordName.toLowerCase().includes(normalizedKeyword) ||
        item.definition.toLowerCase().includes(normalizedKeyword);

      // 카테고리 조건과 검색어 조건을 모두 만족한 항목만 결과로 사용합니다.
      return matchesCategory && matchesKeyword;
    });
  };

  // 수어표현검색1 화면에 표시할 카테고리 목록을 가져옵니다.
  // 백엔드가 준비되지 않았거나 카테고리가 없으면 임시 카테고리1~24를 사용합니다.
  const loadCategories = async () => {
    try {
      // 백엔드 카테고리 목록 API를 호출합니다.
      const response = await fetch(`${apiBaseUrl}/api/v1/dictionary/categories`);

      // 응답이 200번대가 아니면 catch로 이동시켜 fallback을 사용합니다.
      if (!response.ok) {
        throw new Error('Failed to load categories');
      }

      // 응답 JSON을 카테고리 배열로 변환합니다.
      const data = await response.json();

      // DB에 카테고리가 하나도 없으면 화면 확인을 위해 fallback을 사용합니다.
      if (data.length === 0) {
        throw new Error('No categories found');
      }

      // API 데이터 사용 상태로 변경합니다.
      setIsFallbackMode(false);
      // 백엔드에서 받은 카테고리 목록을 화면 상태에 저장합니다.
      setCategories(data);
    } catch {
      // API 실패 시 fallback 데이터 사용 상태로 변경합니다.
      setIsFallbackMode(true);
      // 임시 단어 데이터에서 카테고리 이름만 중복 제거해서 저장합니다.
      setCategories([
        ...new Set(fallbackDictionaryItems.map((item) => item.categoryName)),
      ]);
    }
  };

  // 검색어와 카테고리 조건으로 단어 목록을 가져옵니다.
  // 요구사항 RQ-8000/RQ-8002의 검색창 및 실시간 검색 흐름에서 사용됩니다.
  const loadDictionaryItems = async (keyword = searchKeyword, category = selectedCategory) => {
    // fallback 모드라면 백엔드 호출 없이 임시 데이터에서 검색합니다.
    if (isFallbackMode) {
      // 검색어/카테고리 조건에 맞는 임시 단어 목록을 저장합니다.
      setDictionaryItems(getFallbackDictionaryItems(keyword, category));
      // 새 검색 결과가 나오면 단어 페이지를 1페이지로 되돌립니다.
      setWordPage(1);
      return;
    }

    // API에 붙일 query string을 안전하게 만들기 위한 객체입니다.
    const params = new URLSearchParams();

    // 검색어가 있으면 keyword 파라미터를 추가합니다.
    if (keyword.trim()) {
      params.append('keyword', keyword.trim());
    }

    // 카테고리가 선택되어 있으면 category 파라미터를 추가합니다.
    if (category) {
      params.append('category', category);
    }

    // API 요청 시작 상태로 바꿔 로딩 문구를 표시할 수 있게 합니다.
    setIsLoading(true);

    try {
      // URLSearchParams를 실제 URL 뒤에 붙일 문자열로 변환합니다.
      const queryString = params.toString();
      // query string이 있으면 ?keyword=... 형태로 붙이고, 없으면 기본 목록 API를 호출합니다.
      const requestUrl = `${apiBaseUrl}/api/v1/dictionary${queryString ? `?${queryString}` : ''}`;
      // 백엔드 단어 목록 API를 호출합니다.
      const response = await fetch(requestUrl);

      // 응답이 200번대가 아니면 catch로 이동해 fallback 검색을 사용합니다.
      if (!response.ok) {
        throw new Error('Failed to load dictionary items');
      }

      // 백엔드 응답 JSON을 배열로 변환합니다.
      const data = await response.json();
      // snake_case 응답을 camelCase로 바꿔 단어 목록 상태에 저장합니다.
      setDictionaryItems(data.map(convertDictionaryItem));
      // 새 검색 결과가 나오면 단어 페이지를 1페이지로 되돌립니다.
      setWordPage(1);
    } catch {
      // API 실패 시 임시 데이터에서 같은 조건으로 검색합니다.
      setDictionaryItems(getFallbackDictionaryItems(keyword, category));
      // fallback 검색 결과도 1페이지부터 보여줍니다.
      setWordPage(1);
    } finally {
      // 성공/실패와 관계없이 API 요청이 끝났으므로 로딩 상태를 해제합니다.
      setIsLoading(false);
    }
  };

  // 상단 메뉴에서 수어검색을 다시 누르면 내부 화면 상태를 첫 화면으로 초기화합니다.
  // 같은 /dictionary 주소로 다시 이동하면 React는 컴포넌트를 새로 만들지 않기 때문에,
  // viewMode, selectedCategory, selectedDictionary 같은 내부 상태가 그대로 남을 수 있습니다.
  // 그래서 Layout.jsx가 보내는 resetAt 값을 기준으로 "다시 눌렀다"는 신호를 감지합니다.
  useEffect(() => {
    // resetAt 값이 없으면 일반적인 첫 진입이므로 여기서 따로 초기화하지 않습니다.
    if (!location.state?.resetAt) {
      return;
    }

    // 카테고리 선택창으로 돌아갑니다.
    setViewMode('category');
    // 검색창 입력값을 비웁니다.
    setSearchKeyword('');
    // 선택된 카테고리를 초기화합니다.
    setSelectedCategory('');
    // 이전 카테고리/검색 결과 단어 목록을 비웁니다.
    setDictionaryItems([]);
    // 상세 화면에서 선택했던 단어 정보를 비웁니다.
    setSelectedDictionary(null);
    // 카테고리 페이지를 첫 페이지로 되돌립니다.
    setCategoryPage(1);
    // 단어 페이지도 첫 페이지로 되돌립니다.
    setWordPage(1);
  }, [location.state?.resetAt]);

  // 화면 진입 시 카테고리 목록을 먼저 불러옵니다.
  useEffect(() => {
    // 컴포넌트가 처음 화면에 나타나면 카테고리 목록을 불러옵니다.
    loadCategories();
  }, []);

  // 단어선택창에서 검색어가 바뀌면 잠깐 기다린 뒤 자동으로 결과를 갱신합니다.
  // dependency에는 searchKeyword와 selectedCategory만 둡니다.
  // viewMode까지 넣으면 상세화면에서 뒤로가기 할 때 detail -> result 변화만으로 목록을 다시 조회합니다.
  // 그 경우 loadDictionaryItems 내부에서 wordPage가 1로 초기화되어, 8페이지에서 상세를 보고 돌아와도 1페이지로 가게 됩니다.
  // 그래서 검색어 또는 카테고리가 실제로 바뀔 때만 재검색하여 기존 단어 페이지 위치를 유지합니다.
  useEffect(() => {
    // 카테고리 선택창이나 단어설명창에서는 실시간 검색을 실행하지 않습니다.
    if (viewMode !== 'result') {
      return undefined;
    }

    // 사용자가 입력을 멈춘 뒤 0.25초 후 검색해서 너무 많은 API 호출을 막습니다.
    const timerId = window.setTimeout(() => {
      loadDictionaryItems(searchKeyword, selectedCategory);
    }, 250);

    // 검색어가 다시 바뀌면 이전 예약 검색을 취소합니다.
    return () => window.clearTimeout(timerId);
  }, [searchKeyword, selectedCategory]);

  // 검색 버튼 클릭 시 검색 결과 화면(수어표현검색2)으로 이동합니다.
  const handleSearch = (event) => {
    // form 기본 동작인 페이지 새로고침을 막습니다.
    event.preventDefault();
    // 이전에 선택했던 상세 단어를 초기화합니다.
    setSelectedDictionary(null);
    // 검색 결과는 항상 단어 1페이지부터 보여줍니다.
    setWordPage(1);
    // 검색 결과 화면으로 전환합니다.
    setViewMode('result');
    // 현재 검색어와 카테고리 조건으로 단어 목록을 불러옵니다.
    loadDictionaryItems(searchKeyword, selectedCategory);
  };

  // 카테고리 클릭 시 해당 카테고리의 단어 목록 화면으로 이동합니다.
  const handleCategoryClick = (categoryName) => {
    // 사용자가 클릭한 카테고리를 선택 상태로 저장합니다.
    setSelectedCategory(categoryName);
    // 이전에 선택했던 상세 단어를 초기화합니다.
    setSelectedDictionary(null);
    // 카테고리를 새로 선택하면 단어 1페이지부터 보여줍니다.
    setWordPage(1);
    // 단어 선택창으로 이동합니다.
    setViewMode('result');
    // 선택한 카테고리의 단어 목록을 불러옵니다.
    loadDictionaryItems(searchKeyword, categoryName);
  };

  // 단어 클릭 시 상세 API를 조회하고, 실패하면 목록에 있던 데이터로 상세 화면을 표시합니다.
  const handleDictionaryClick = async (dictionaryItem) => {
    // 상세 API 요청 중임을 표시합니다.
    setIsLoading(true);

    try {
      // 선택한 단어의 ID로 상세 조회 API를 호출합니다.
      const response = await fetch(
        `${apiBaseUrl}/api/v1/dictionary/${dictionaryItem.dictionaryId}`
      );

      // 상세 API가 실패하면 catch에서 목록 데이터를 그대로 사용합니다.
      if (!response.ok) {
        throw new Error('Failed to load dictionary detail');
      }

      // 상세 응답 JSON을 객체로 변환합니다.
      const data = await response.json();
      // 상세 응답을 camelCase로 바꿔 선택 단어 상태에 저장합니다.
      setSelectedDictionary(convertDictionaryItem(data));
    } catch {
      // 상세 API가 실패해도 목록에 이미 있는 정보로 상세 화면을 보여줍니다.
      setSelectedDictionary(dictionaryItem);
    } finally {
      // 상세 조회가 끝났으므로 로딩 상태를 해제합니다.
      setIsLoading(false);
      // 단어 설명창으로 이동합니다.
      setViewMode('detail');
    }
  };

  // 단어설명창(수어표현검색3)에서 뒤로가기하면 단어선택창(수어표현검색2)으로 돌아갑니다.
  const handleBackClick = () => {
    // 상세 화면에서 선택 단어 상태를 비웁니다.
    setSelectedDictionary(null);
    // 단어 선택창으로 돌아갑니다.
    setViewMode('result');
  };

  // 단어선택창(수어표현검색2)에서 뒤로가기하면 카테고리 선택창(수어표현검색1)으로 돌아갑니다.
  const handleResultBackClick = () => {
    // 검색어를 초기화합니다.
    setSearchKeyword('');
    // 선택 카테고리를 초기화합니다.
    setSelectedCategory('');
    // 단어 목록을 비웁니다.
    setDictionaryItems([]);
    // 선택 단어를 초기화합니다.
    setSelectedDictionary(null);
    // 단어 페이지를 1페이지로 되돌립니다.
    setWordPage(1);
    // 카테고리 선택창으로 돌아갑니다.
    setViewMode('category');
  };

  return (
    // 수어표현검색 전체 페이지를 감싸는 영역입니다.
    <section className="dictionary-page">
      {/* 수어표현검색1, 2에서 공통으로 사용하는 검색 영역입니다. */}
      {/* 단어설명창에서는 검색창을 숨기기 위해 viewMode가 detail이 아닐 때만 보여줍니다. */}
      {viewMode !== 'detail' && (
        <div className="dictionary-search-section">
          {/* 검색 영역 제목입니다. */}
          <h1>수어표현 찾기</h1>
          {/* 검색 버튼을 눌렀을 때 handleSearch가 실행되는 form입니다. */}
          <form className="dictionary-search-form" onSubmit={handleSearch}>
            {/* 검색어를 입력하는 input입니다. */}
            <input
              // 브라우저가 검색 입력으로 인식하도록 type을 search로 둡니다.
              type="search"
              // input에 표시할 값은 searchKeyword 상태와 연결합니다.
              value={searchKeyword}
              // 사용자가 입력할 때마다 searchKeyword 상태를 갱신합니다.
              onChange={(event) => setSearchKeyword(event.target.value)}
              // 입력 전 안내 문구입니다.
              placeholder="찾고 싶은 수어표현을 검색하세요."
              // 스크린리더가 검색창의 의미를 알 수 있게 하는 접근성 라벨입니다.
              aria-label="수어표현 검색어"
            />
            {/* 검색 결과 화면으로 이동시키는 버튼입니다. */}
            <button type="submit">검색</button>
          </form>
        </div>
      )}

      {/* 수어표현검색1: 카테고리 선택창 */}
      {/* viewMode가 category일 때만 카테고리 선택 화면을 보여줍니다. */}
      {viewMode === 'category' && (
        <>
          {/* 카테고리 정렬 방향을 바꾸는 버튼 영역입니다. */}
          <div className="dictionary-category-toolbar">
            {/* 카테고리를 1, 2, 3 순서로 정렬합니다. */}
            <button
              type="button"
              // 현재 정렬 상태가 asc면 선택된 버튼 스타일을 적용합니다.
              className={categorySortOrder === 'asc' ? 'dictionary-active' : ''}
              onClick={() => {
                // 카테고리 정렬 상태를 정순으로 바꿉니다.
                setCategorySortOrder('asc');
                // 정렬이 바뀌면 첫 페이지부터 다시 보여줍니다.
                setCategoryPage(1);
              }}
            >
              정렬
            </button>
            {/* 카테고리를 24, 23, 22 순서로 역순 정렬합니다. */}
            <button
              type="button"
              // 현재 정렬 상태가 desc면 선택된 버튼 스타일을 적용합니다.
              className={categorySortOrder === 'desc' ? 'dictionary-active' : ''}
              onClick={() => {
                // 카테고리 정렬 상태를 역순으로 바꿉니다.
                setCategorySortOrder('desc');
                // 정렬이 바뀌면 첫 페이지부터 다시 보여줍니다.
                setCategoryPage(1);
              }}
            >
              역순
            </button>
          </div>

          {/* 현재 카테고리 페이지의 카테고리 버튼 6개를 표시하는 영역입니다. */}
          <div className="dictionary-category-grid">
            {/* visibleCategories 배열을 반복해서 카테고리 버튼을 만듭니다. */}
            {visibleCategories.map((categoryName) => (
              <button
                // React가 반복 목록을 구분할 수 있게 카테고리명을 key로 사용합니다.
                key={categoryName}
                type="button"
                className="dictionary-category-button"
                // 카테고리 클릭 시 해당 카테고리의 단어 목록으로 이동합니다.
                onClick={() => handleCategoryClick(categoryName)}
              >
                {/* 버튼 안에 카테고리 이름을 표시합니다. */}
                {categoryName}
              </button>
            ))}
          </div>

          {/* 카테고리 페이지 번호를 표시하는 영역입니다. */}
          <div className="dictionary-page-selector">
            {/* 이전 카테고리 페이지로 이동하는 버튼입니다. */}
            <button
              type="button"
              // 첫 페이지에서는 이전 버튼을 비활성화합니다.
              disabled={categoryPage === 1}
              // 현재 페이지 번호에서 1을 빼 이전 페이지로 이동합니다.
              onClick={() => setCategoryPage(categoryPage - 1)}
            >
              &lt;
            </button>
            {/* 페이지가 많으면 현재 페이지 주변 번호와 생략 표시만 보여줍니다. */}
            {categoryPaginationItems.map((pageItem) =>
              typeof pageItem === 'number' ? (
                <button
                  // 페이지 번호 자체를 key로 사용합니다.
                  key={pageItem}
                  type="button"
                  // 현재 페이지 번호와 같으면 선택된 버튼 스타일을 적용합니다.
                  className={categoryPage === pageItem ? 'dictionary-active' : ''}
                  // 클릭한 번호의 카테고리 페이지로 이동합니다.
                  onClick={() => setCategoryPage(pageItem)}
                >
                  {/* 화면에는 1부터 시작하는 페이지 번호를 보여줍니다. */}
                  {pageItem}
                </button>
              ) : (
                // 생략 구간은 클릭할 수 없는 점 표시로 보여줍니다.
                <span key={pageItem} className="dictionary-page-ellipsis">...</span>
              )
            )}
            {/* 다음 카테고리 페이지로 이동하는 버튼입니다. */}
            <button
              type="button"
              // 마지막 페이지에서는 다음 버튼을 비활성화합니다.
              disabled={categoryPage === totalCategoryPages}
              // 현재 페이지 번호에 1을 더해 다음 페이지로 이동합니다.
              onClick={() => setCategoryPage(categoryPage + 1)}
            >
              &gt;
            </button>
          </div>
        </>
      )}

      {/* 수어표현검색2: 검색 결과 및 단어 선택창 */}
      {/* viewMode가 result일 때만 단어 선택 화면을 보여줍니다. */}
      {viewMode === 'result' && (
        <div className="dictionary-result-section">
          {/* 선택 카테고리, 결과 개수, 뒤로가기 버튼을 보여주는 상단 영역입니다. */}
          <div className="dictionary-result-header">
            <div>
              {/* 선택된 카테고리가 있으면 카테고리명, 없으면 전체라고 표시합니다. */}
              <strong>{selectedCategory || '전체'}</strong>
              {/* 현재 조건으로 조회된 전체 단어 개수를 표시합니다. */}
              <span>{dictionaryItems.length}개 결과</span>
            </div>
            {/* 단어 선택창에서 카테고리 선택창으로 돌아가는 버튼입니다. */}
            <button type="button" onClick={handleResultBackClick}>
              뒤로가기
            </button>
          </div>

          {/* 단어 정렬 방향을 바꾸는 버튼 영역입니다. */}
          <div className="dictionary-category-toolbar">
            {/* 단어를 1, 2, 3 순서로 정렬합니다. */}
            <button
              type="button"
              // 현재 단어 정렬 상태가 asc면 선택된 버튼 스타일을 적용합니다.
              className={wordSortOrder === 'asc' ? 'dictionary-active' : ''}
              onClick={() => {
                // 단어 정렬 상태를 정순으로 바꿉니다.
                setWordSortOrder('asc');
                // 정렬이 바뀌면 단어 1페이지부터 다시 보여줍니다.
                setWordPage(1);
              }}
            >
              정렬
            </button>
            {/* 단어를 9, 8, 7 순서로 역순 정렬합니다. */}
            <button
              type="button"
              // 현재 단어 정렬 상태가 desc면 선택된 버튼 스타일을 적용합니다.
              className={wordSortOrder === 'desc' ? 'dictionary-active' : ''}
              onClick={() => {
                // 단어 정렬 상태를 역순으로 바꿉니다.
                setWordSortOrder('desc');
                // 정렬이 바뀌면 단어 1페이지부터 다시 보여줍니다.
                setWordPage(1);
              }}
            >
              역순
            </button>
          </div>

          {/* 단어 검색 결과 카드 목록을 표시하는 영역입니다. */}
          <div className="dictionary-result-list">
            {/* API 요청 중일 때 로딩 문구를 보여줍니다. */}
            {isLoading && <p className="dictionary-empty-text">검색 중입니다.</p>}
            {/* 로딩이 끝났고 결과가 없으면 빈 결과 문구를 보여줍니다. */}
            {!isLoading && dictionaryItems.length === 0 && (
              <p className="dictionary-empty-text">검색 결과가 없습니다.</p>
            )}
            {/* 로딩이 아니면 현재 단어 페이지에 해당하는 단어 카드들을 보여줍니다. */}
            {!isLoading &&
              visibleDictionaryItems.map((dictionaryItem) => (
                <button
                  // 각 단어 카드의 고유 key입니다.
                  key={dictionaryItem.dictionaryId}
                  type="button"
                  className="dictionary-result-item"
                  // 단어 카드를 클릭하면 단어 설명창으로 이동합니다.
                  onClick={() => handleDictionaryClick(dictionaryItem)}
                >
                  {/* 목록에서 영상 미리보기 또는 영상 자리 표시를 보여주는 영역입니다. */}
                  <span className="dictionary-video-box">
                    {/* videoUrl이 있으면 실제 영상을 표시합니다. */}
                    {dictionaryItem.videoUrl ? (
                      <video
                        // Azure 또는 DB에서 받은 영상 URL입니다.
                        src={dictionaryItem.videoUrl}
                        // 목록에서 빈 영상 박스처럼 보이지 않도록 같은 파일의 썸네일 이미지를 표시합니다.
                        poster={getVideoPosterUrl(dictionaryItem.videoUrl)}
                        // 목록 미리보기에서는 소리가 나지 않도록 muted를 사용합니다.
                        muted
                        // 모바일 브라우저가 목록 영상을 전체 화면으로 강제 전환하지 않도록 합니다.
                        playsInline
                        // 영상 전체가 아니라 메타데이터만 먼저 불러옵니다.
                        preload="metadata"
                      />
                    ) : (
                      // 영상 URL이 없으면 임시로 "영상" 텍스트를 보여줍니다.
                      <span>영상</span>
                    )}
                  </span>
                  {/* 단어명과 설명을 보여주는 텍스트 영역입니다. */}
                  <span className="dictionary-result-content">
                    {/* 단어명을 굵게 표시합니다. */}
                    <strong>{dictionaryItem.wordName}</strong>
                    {/* 단어의 수어 동작 설명을 표시합니다. */}
                    <span>{dictionaryItem.definition}</span>
                  </span>
                </button>
              ))}
          </div>

          {/* 단어가 한 페이지 분량보다 많을 때만 단어 페이지 번호를 보여줍니다. */}
          {!isLoading && dictionaryItems.length > wordPageSize && (
            <div className="dictionary-page-selector">
              {/* 이전 단어 페이지로 이동하는 버튼입니다. */}
              <button
                type="button"
                // 첫 페이지에서는 이전 버튼을 비활성화합니다.
                disabled={wordPage === 1}
                // 현재 단어 페이지 번호에서 1을 빼 이전 페이지로 이동합니다.
                onClick={() => setWordPage(wordPage - 1)}
              >
                &lt;
              </button>
              {/* 페이지가 많으면 현재 페이지 주변 번호와 생략 표시만 보여줍니다. */}
              {wordPaginationItems.map((pageItem) =>
                typeof pageItem === 'number' ? (
                  <button
                    // 페이지 번호 자체를 key로 사용합니다.
                    key={pageItem}
                    type="button"
                    // 현재 단어 페이지 번호와 같으면 선택된 버튼 스타일을 적용합니다.
                    className={wordPage === pageItem ? 'dictionary-active' : ''}
                    // 클릭한 번호의 단어 페이지로 이동합니다.
                    onClick={() => setWordPage(pageItem)}
                  >
                    {/* 화면에는 1부터 시작하는 페이지 번호를 보여줍니다. */}
                    {pageItem}
                  </button>
                ) : (
                  // 생략 구간은 클릭할 수 없는 점 표시로 보여줍니다.
                  <span key={pageItem} className="dictionary-page-ellipsis">...</span>
                )
              )}
              {/* 다음 단어 페이지로 이동하는 버튼입니다. */}
              <button
                type="button"
                // 마지막 페이지에서는 다음 버튼을 비활성화합니다.
                disabled={wordPage === totalWordPages}
                // 현재 단어 페이지 번호에 1을 더해 다음 페이지로 이동합니다.
                onClick={() => setWordPage(wordPage + 1)}
              >
                &gt;
              </button>
            </div>
          )}
        </div>
      )}

      {/* 수어표현검색3: 선택한 단어의 영상과 설명을 보여주는 상세창 */}
      {/* viewMode가 detail이고 선택 단어가 있을 때만 단어 설명창을 보여줍니다. */}
      {viewMode === 'detail' && selectedDictionary && (
        <div className="dictionary-detail-wrap">
          {/* 단어선택창과 상세창의 뒤로가기 버튼 위치를 맞추기 위한 숨김 검색창 자리입니다. */}
          <div className="dictionary-search-section dictionary-search-placeholder" aria-hidden="true">
            {/* 실제로 보이지 않지만 검색창 영역 높이를 맞추기 위해 같은 제목을 둡니다. */}
            <h1>수어표현 찾기</h1>
            {/* 실제로 보이지 않지만 검색창 영역 높이를 맞추기 위해 같은 form 구조를 둡니다. */}
            <form className="dictionary-search-form">
              <input
                type="search"
                placeholder="찾고 싶은 수어표현을 검색하세요."
                // 숨김 input이 키보드 포커스를 받지 않도록 합니다.
                tabIndex="-1"
              />
              {/* 숨김 버튼도 키보드 포커스를 받지 않도록 합니다. */}
              <button type="button" tabIndex="-1">
                검색
              </button>
            </form>
          </div>

          {/* 단어 설명창의 상단 정보와 뒤로가기 버튼 영역입니다. */}
          <div className="dictionary-result-header dictionary-detail-header">
            <div>
              {/* 상세 화면에서 선택한 단어명을 표시합니다. */}
              <strong>{selectedDictionary.wordName}</strong>
              {/* 상세 화면에서 선택한 단어의 카테고리를 표시합니다. */}
              <span>{selectedDictionary.categoryName}</span>
            </div>
            {/* 단어 설명창에서 단어 선택창으로 돌아가는 버튼입니다. */}
            <button type="button" onClick={handleBackClick}>
              뒤로가기
            </button>
          </div>

          {/* 영상과 설명을 나란히 보여주는 상세 내용 영역입니다. */}
          <div className="dictionary-detail-section">
            {/* 상세 영상 또는 카메라 아이콘을 보여주는 영역입니다. */}
            <div className="dictionary-detail-video">
              {/* videoUrl이 있으면 실제 영상을 controls와 함께 보여줍니다. */}
              {selectedDictionary.videoUrl ? (
                <video src={selectedDictionary.videoUrl} controls />
              ) : (
                // videoUrl이 없으면 영상 준비 전 상태를 카메라 아이콘으로 표시합니다.
                <span className="dictionary-camera-icon" aria-hidden="true" />
              )}
            </div>

            {/* 단어명과 수어 동작 설명을 보여주는 상세 텍스트 영역입니다. */}
            <article className="dictionary-detail-content">
              {/* 선택한 단어의 카테고리명입니다. */}
              <span>{selectedDictionary.categoryName}</span>
              {/* 선택한 단어의 이름입니다. */}
              <h1>{selectedDictionary.wordName}</h1>
              {/* 선택한 단어의 수어 동작 설명입니다. */}
              <p>{selectedDictionary.definition}</p>
            </article>
          </div>
        </div>
      )}
    </section>
  );
}

export default Dictionary;
