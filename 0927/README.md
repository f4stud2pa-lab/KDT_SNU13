# 초개인화 금융상품 추천 챗봇

실습 문제 1 Part 1의 고객 프로파일과 금융상품 모범 매칭을 사용해,
OpenAI API로 초개인화 금융상품 추천 리포트를 생성하는 Python 프로그램입니다.

## 필요한 환경

- Python 3.10 이상
- OpenAI API Key
- 인터넷 연결

## 설치

프로젝트 폴더에서 실행합니다.

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -r 0927/requirements.txt
```

이미 `.venv`를 사용하고 있다면 설치 단계만 실행해도 됩니다.

## API Key 설정

API Key는 소스 코드나 GitHub에 저장하지 마세요. macOS/Linux 터미널에서
현재 터미널 세션에만 설정합니다.

```bash
export OPENAI_API_KEY="팀원 본인의 OpenAI API Key"
```

Windows PowerShell에서는 다음과 같이 설정합니다.

```powershell
$env:OPENAI_API_KEY="팀원 본인의 OpenAI API Key"
```

## 실행

프로젝트 루트에서 다음 명령을 실행합니다.

macOS/Linux:

```bash
./.venv/bin/python 0927/part1.py
```

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe 0927\part1.py
```

실행 후 다음 중 하나를 입력합니다.

- `C01` ~ `C10`: 실습 문서에 등록된 고객 선택
- `custom`: 고객 프로파일 직접 입력

## GitHub로 공유하는 방법

저장소를 만든 뒤 프로젝트 루트에서 다음을 실행합니다.

```bash
git init
git add 0927/part1.py 0927/part1 0927/README.md 0927/requirements.txt .gitignore
git commit -m "Add personalized finance chatbot"
git branch -M main
git remote add origin https://github.com/사용자명/저장소명.git
git push -u origin main
```

팀원은 저장소를 복제한 뒤 `설치 → API Key 설정 → 실행` 순서로 사용하면 됩니다.
팀원마다 자신의 API Key를 사용하는 것을 권장합니다.

## 보안 주의

- API Key를 `part1.py`, `README.md`, 채팅방, GitHub에 입력하지 않습니다.
- API Key가 외부에 노출되었다면 OpenAI 콘솔에서 폐기하고 새 키를 발급합니다.
- 이 프로그램의 추천 결과는 교육용이며 실제 금융상품 가입 전 상품설명서와
  전문가 상담을 확인해야 합니다.
