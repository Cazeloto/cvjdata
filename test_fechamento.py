import os
import unittest
from unittest.mock import patch
import pandas as pd
from massa_teste import generate
from fechamento import select_official, summarize_closings, match_cure


class FechamentoTests(unittest.TestCase):
    def setUp(self):
        self.calendar, self.closing, self.cure = generate()
        self.selected = select_official(self.calendar, self.closing, '2026-10-01', '2026-12-31', '2026-11-23')

    def test_official_and_future(self):
        self.assertEqual(len(self.closing), 21)
        self.assertEqual(len(self.selected), 18)
        self.assertEqual(self.selected['data'].nunique(), 2)

    def test_counts(self):
        summary = summarize_closings(self.selected)
        self.assertEqual(summary[['normais','preferenciais','nao_apareceu','espera']].values.tolist(), [[5,2,1,2],[5,3,2,1]])
        self.assertTrue((summary['normais']+summary['preferenciais']+summary['nao_apareceu']==summary['registros']).all())

    def test_type_filter(self):
        rows = select_official(self.calendar,self.closing,'2026-10-01','2026-11-23','2026-11-23',['Preto Velho'])
        self.assertEqual(len(rows),10)

    def test_names_and_duplicate_procedures(self):
        people=match_cure(self.selected,self.cure,'2026-10-01','2026-11-23','2026-11-23')
        self.assertEqual(len(people),15)
        self.assertEqual(int(people['tambem_cura'].sum()),5)
        ana=people.set_index('chave').loc['teste ana']
        self.assertEqual((ana['giras'],ana['dias_cura']),(2,1))
        self.assertEqual(people.set_index('chave').loc['teste lia','cadastros_cura'],2)

    def test_full_history(self):
        people=match_cure(self.selected,self.cure,'2026-10-01','2026-11-23','2026-11-23',False)
        self.assertEqual(int(people['tambem_cura'].sum()),6)

    def test_empty(self):
        rows=select_official(self.calendar,self.closing,'2025-01-01','2025-12-31','2026-11-23')
        self.assertTrue(summarize_closings(rows).empty)
        self.assertTrue(match_cure(rows,self.cure,'2025-01-01','2025-12-31','2026-11-23').empty)

    def test_ui_demo_without_database(self):
        from streamlit.testing.v1 import AppTest
        with patch.dict(os.environ, {'CVJDATA_DEMO':'1'}), patch('db.connect', side_effect=AssertionError('Database access forbidden in demo')):
            app=AppTest.from_file('pages/2_Fechamento.py').run(timeout=30)
            self.assertFalse(app.exception)
            self.assertEqual(app.selectbox[0].value,pd.Timestamp('2026-11-07'))
            app.selectbox[0].select(pd.Timestamp('2026-10-17')).run()
            self.assertFalse(app.exception)
            metrics={m.label:m.value for m in app.metric}
            self.assertEqual(metrics['Normais (inclui espera)'],'5')
            self.assertEqual(metrics['Preferenciais'],'2')
            self.assertEqual(metrics['Não apareceu'],'1')


if __name__ == '__main__':
    unittest.main()
