"""Test-creator (RJalol/Test-creator) nusxasiga bizning moslashtirishlarni qo'llaydi.

    python3 deploy/test-creator/apply_patch.py /var/www/test-creator

Nima qiladi (hammasi IDEMPOTENT — qayta ishga tushirsa takrorlamaydi):
  1. `backend/app/services/providers/gemini_provider.py` — Gemini provayderini nusxalaydi;
  2. `backend/app/services/ai_router.py` — "gemini" provayderini ro'yxatga oladi;
  3. `backend/requirements.txt` — `google-genai` qo'shadi;
  4. `backend/app/api/v1/auth.py` — ro'yxatdan o'tishni YOPADI: faqat `REGISTRATION_ALLOWED_EMAILS`
     (vergul bilan) ro'yxatidagi emaillar ro'yxatdan o'ta oladi (ro'yxat bo'sh bo'lsa — hech kim).
     Aks holda ochiq saytda har kim hisob ochib, Gemini kalitimizni sarflay olardi.
  6. OpenAI (GPT) provayderi: `openai_provider.py` nusxalanadi, "openai" ro'yxatga olinadi, `openai` paketi qo'shiladi
     (faollashtirish: `.env` da `TC_AI_PROVIDER=openai`, `OPENAI_API_KEY`, `OPENAI_MODEL`).
  5. `backend/app/services/question_generation_service.py` — savol tili standartga qarab tanlanadi:
     IELTS va SAT — inglizcha, qolganlari (UZBMB) — o'zbekcha (asl kodda doim o'zbekcha edi).
"""
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

ROUTER_ANCHOR = '_provider_instances: dict[str, AIProvider] = {}'
ROUTER_BLOCK = '''try:
    from app.services.providers.gemini_provider import GeminiProvider

    _PROVIDER_REGISTRY["gemini"] = GeminiProvider
except ImportError:  # pragma: no cover
    pass

'''
OPENAI_ROUTER_BLOCK = '''try:
    from app.services.providers.openai_provider import OpenAIProvider

    _PROVIDER_REGISTRY["openai"] = OpenAIProvider
except ImportError:  # pragma: no cover
    pass

'''
OPENAI_MODEL_LINE = '"openai": __import__("os").environ.get("OPENAI_MODEL", "gpt-4o-mini"),'
MODEL_ANCHOR = '"anthropic": settings.ANTHROPIC_MODEL,'
MODEL_LINE = '"gemini": __import__("os").environ.get("GEMINI_MODEL", "gemini-3.5-flash"),'

AUTH_ANCHOR = '    existing = db.query(User).filter(User.email == payload.email).one_or_none()\n    if existing:'
AUTH_BLOCK = '''    import os as _os

    _allowed = {e.strip().lower() for e in _os.environ.get("REGISTRATION_ALLOWED_EMAILS", "").split(",") if e.strip()}
    if str(payload.email).lower() not in _allowed:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Ro'yxatdan o'tish yopiq: bu email ruxsat etilmagan")

'''


GEN_FUNC_ANCHOR = 'def generate_and_validate('
GEN_HELPER = '''def _language_for(db, standard_version_id) -> str:
    """Xalqaro imtihonlar (IELTS, SAT) savollari inglizcha, milliy (UZBMB) — o'zbekcha."""
    from app.models.standard import Standard, StandardVersion

    version = db.get(StandardVersion, standard_version_id)
    standard = db.get(Standard, version.standard_id) if version else None
    return "en" if standard is not None and standard.code in ("IELTS_ACADEMIC", "DIGITAL_SAT") else "uz"


'''
GEN_SIGNATURE = re.compile(r'(\n[ ]*)language: str = "uz",(\n\) -> GenerationOutcome:\n)')


def patch_generation(text: str) -> str:
    if GEN_FUNC_ANCHOR not in text or not GEN_SIGNATURE.search(text):
        return text
    text = GEN_SIGNATURE.sub(
        r'\1language: str | None = None,\2'
        '    if language is None:\n'
        '        language = _language_for(db, standard_version_id)\n',
        text, count=1,
    )
    return text.replace(GEN_FUNC_ANCHOR, GEN_HELPER + GEN_FUNC_ANCHOR, 1)


def patch_text(path: Path, marker: str, edit) -> str:
    text = path.read_text(encoding='utf-8')
    if marker in text:
        return 'allaqachon qo\'llangan'
    new = edit(text)
    if new == text:
        raise SystemExit(f'XATO: {path} ichida kerakli joy topilmadi (repo versiyasi o\'zgargan bo\'lishi mumkin).')
    path.write_text(new, encoding='utf-8', newline='')
    return 'qo\'llandi'


def main(root: str) -> None:
    base = Path(root) / 'backend'
    if not (base / 'app' / 'main.py').exists():
        raise SystemExit(f'XATO: {base} Test-creator backend papkasiga o\'xshamaydi.')

    shutil.copyfile(HERE / 'gemini_provider.py', base / 'app/services/providers/gemini_provider.py')
    print('gemini_provider.py: nusxalandi')

    def router(text):
        if ROUTER_ANCHOR not in text or MODEL_ANCHOR not in text:
            raise SystemExit("XATO: ai_router.py ichida kerakli joylar topilmadi (repo versiyasi o'zgargan bo'lishi mumkin).")
        text = text.replace(ROUTER_ANCHOR, ROUTER_BLOCK + ROUTER_ANCHOR, 1)
        return text.replace(MODEL_ANCHOR, MODEL_ANCHOR + '\n        ' + MODEL_LINE, 1)

    print('ai_router.py:', patch_text(base / 'app/services/ai_router.py', 'gemini_provider', router))

    shutil.copyfile(HERE / 'openai_provider.py', base / 'app/services/providers/openai_provider.py')
    print('openai_provider.py: nusxalandi')

    def openai_router(text):
        if ROUTER_ANCHOR not in text or MODEL_ANCHOR not in text:
            raise SystemExit("XATO: ai_router.py ichida kerakli joylar topilmadi (repo versiyasi o'zgargan bo'lishi mumkin).")
        text = text.replace(ROUTER_ANCHOR, OPENAI_ROUTER_BLOCK + ROUTER_ANCHOR, 1)
        return text.replace(MODEL_ANCHOR, MODEL_ANCHOR + '\n        ' + OPENAI_MODEL_LINE, 1)

    print('ai_router.py (openai):', patch_text(base / 'app/services/ai_router.py', 'openai_provider', openai_router))

    requirements = base / 'requirements.txt'
    text = requirements.read_text(encoding='utf-8')
    if 'google-genai' in text:
        print('requirements.txt: allaqachon bor')
    else:
        requirements.write_text(text.rstrip('\n') + '\ngoogle-genai>=1.0\n', encoding='utf-8', newline='')
        print('requirements.txt: google-genai qo\'shildi')
    text = requirements.read_text(encoding='utf-8')
    if re.search(r'(?m)^openai[<>=~! ]', text):
        print('requirements.txt: openai allaqachon bor')
    else:
        requirements.write_text(text.rstrip('\n') + '\nopenai>=1.40\n', encoding='utf-8', newline='')
        print('requirements.txt: openai qo\'shildi')

    print('auth.py:', patch_text(
        base / 'app/api/v1/auth.py', 'REGISTRATION_ALLOWED_EMAILS',
        lambda text: text.replace(AUTH_ANCHOR, AUTH_BLOCK + AUTH_ANCHOR, 1),
    ))

    print('question_generation_service.py:', patch_text(
        base / 'app/services/question_generation_service.py', '_language_for', patch_generation,
    ))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Ishlatilishi: apply_patch.py <test-creator papkasi>')
    main(sys.argv[1])
