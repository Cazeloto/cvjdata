from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
import fitz
captured=[]
def download(*args,**kwargs):
    value=kwargs.get('data')
    if callable(value): captured.append(value)
    return False
with patch('streamlit.download_button',download):
    app=AppTest.from_file('C:/CVJDATA/pages/1_Cura.py',default_timeout=90).run()
assert not app.exception, str(app.exception)
assert captured, 'PDF callback missing'
Path('output/pdf').mkdir(parents=True,exist_ok=True)
result=captured[-1]()
Path('output/pdf/cura_painel.pdf').write_bytes(result)
doc=fitz.open(stream=result,filetype='pdf')
print('PDF pages:',len(doc))
for i,page in enumerate(doc):
    if i<4 or i==len(doc)-1:
        page.get_pixmap(matrix=fitz.Matrix(1.2,1.2)).save(f'tmp/pdfs/new_{i+1}.png')
    print(i+1, len(page.get_text()), page.get_text()[:70].replace('\n',' '))

