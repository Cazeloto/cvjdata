"""Dados inteiramente fictícios; não abre conexão com o banco."""
from pathlib import Path
import pandas as pd


def generate():
    calendar = pd.DataFrame([
        ('2026-09-16', 'Cura', 'Cura fictícia anterior'),
        ('2026-10-17', 'Marinheiro e Malandro', 'Gira fictícia de outubro'),
        ('2026-11-07', 'Preto Velho', 'Gira fictícia de novembro'),
        ('2026-11-18', 'Cura', 'Cura fictícia'),
        ('2026-12-05', 'Preto Velho', 'Gira fictícia futura'),
        ('2026-12-16', 'Cura', 'Cura fictícia futura'),
    ], columns=['data', 'tipo', 'gira'])
    rows = []
    def add(day, prefix, names):
        for i, name in enumerate(names, 1):
            rows.append((len(rows)+1, day, f'{prefix}-{i:03}',
                         'P' if prefix == 'P' else 'N', name, i % 3, 'Médium fictício'))
    add('2026-10-17', 'N', ['Teste Ana', 'Teste José', 'Teste Bruno'])
    add('2026-10-17', 'E', ['Teste Carla', 'Teste Davi'])
    add('2026-10-17', 'P', ['Teste Eva', 'Teste Fabio'])
    add('2026-10-17', 'A', ['Teste Gabi'])
    add('2026-11-07', 'N', [' teste  ANA ', 'TESTE JOSE', 'Teste Hugo', None])
    add('2026-11-07', 'E', ['Teste Iris'])
    add('2026-11-07', 'P', ['Teste Julia', 'Teste Kai', 'Teste Lia'])
    add('2026-11-07', 'A', ['Teste Mauro', 'Teste Nina'])
    add('2026-11-22', 'N', ['Teste Fora Calendario', 'Teste Fora Calendario Dois'])
    add('2026-12-05', 'P', ['Teste Futuro'])
    closing = pd.DataFrame(rows, columns=['id','data','senha','fila','nome','acompanhantes','medium'])
    cure = pd.DataFrame([
        (1,'TESTE ANA','2026-11-18'), (1,'TESTE ANA','2026-11-18'),
        (2,'Teste Jose','2026-11-18'), (3,'Teste Carla','2026-09-16'),
        (4,'Teste Eva','2026-11-18'), (5,'Teste Iris','2026-11-18'),
        (6,'Teste Julia','2026-12-16'), (7,'Teste Hugo','2000-01-01'),
        (8,'Teste Lia','2026-11-18'), (9,'Teste Lia','2026-11-18'),
    ], columns=['codigo','nome','data'])
    from fechamento import normalize_name
    for df in (calendar, closing, cure):
        df['data'] = pd.to_datetime(df['data'])
    for df in (closing, cure):
        df['chave'] = df['nome'].map(normalize_name)
    return calendar, closing, cure


if __name__ == '__main__':
    destination = Path(__file__).parent / 'output' / 'massa_teste'
    destination.mkdir(parents=True, exist_ok=True)
    for name, df in zip(('calendario','fechamentos','cura'), generate()):
        df.to_csv(destination / f'{name}.csv', index=False, sep=';', encoding='utf-8-sig')
    print(f'Massa fictícia gerada em {destination}')
