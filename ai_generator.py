import os
import json
from pypdf import PdfReader
from docx import Document

def extract_text_from_pdf(pdf_path: str, max_pages: int = 50) -> str:
    """PDF fayldan matnni ajratib oladi"""
    try:
        reader = PdfReader(pdf_path)
        text = ""
        total_pages = min(len(reader.pages), max_pages)
        for i in range(total_pages):
            page_text = reader.pages[i].extract_text()
            if page_text:
                text += f"\n--- {i+1}-sahifa ---\n" + page_text
        return text
    except Exception as e:
        print(f"PDF o'qishda xatolik: {e}")
        return ""

def extract_text_from_docx(docx_path: str) -> str:
    """Word (.docx) fayldan matnni ajratib oladi"""
    try:
        doc = Document(docx_path)
        full_text = []
        for para in doc.paragraphs:
            if para.text.strip():
                full_text.append(para.text)
        return "\n".join(full_text)
    except Exception as e:
        print(f"Word o'qishda xatolik: {e}")
        return ""

def generate_a_plus_prompt(text_content: str, test_type: str = "chapter", count: int = 30) -> str:
    """
    A+ darajadagi zanjirli testlar uchun qat'iy prompt tayyorlaydi.
    test_type: 'topic' (35 ta) yoki 'chapter' (30 ta)
    """
    prompt = f"""
Siz — Oliy toifali ekspert, DTM va Attestatsiya bo'yicha A+ darajadagi zanjirli testlar tuzuvchi mutaxassissiz.
Quyida berilgan darslik matniga asoslanib, jami {count} ta ENG QIYIN, A+ DARAJADAGI va ZANJIRLI test savollarini tuzing.

TEST TALABLARI:
1. Daraja: A+ (Yuzaki yodlash savollari bo'lmasin. Chuqur tahlil, sabab-oqibat, qiyoslash va mantiqiy xulosalash talab etilsin).
2. Zanjirli tuzilma (Chain questions): Har 2-3 ta savol bitta umumiy manba/kontekstga asoslansin yoki 1-savolning natijasi 2-savol uchun shart bo'lib xizmat qilsin.
3. Variantlar: A, B, C, D — barcha variantlar ilmiy asoslangan, chalg'ituvchi va jiddiy bo'lsin.
4. Javob va Tahlil: Har bir savol uchun to'g'ri javob harfi va batafsil tahliliy izoh (explanation) berilsin.

FORMAT: Faqat va faqat quyidagi toza JSON formatida javob qaytaring (hech qanday qo'shimcha so'z yoki markdown belgisisiz):
[
  {{
    "question_number": 1,
    "chain_group": "Zanjir-1",
    "question_text": "Savol matni...",
    "options": {{
      "A": "Variant A",
      "B": "Variant B",
      "C": "Variant C",
      "D": "Variant D"
    }},
    "correct_answer": "A",
    "explanation": "Ushbu savolning chuqur ilmiy tahlili..."
  }}
]

DARSLIK MATNI:
{text_content[:15000]}
"""
    return prompt
